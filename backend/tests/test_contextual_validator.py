import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from backend.app.validation.contextual_validator import ContextualValidator, ValidatorConfig, contextual_validator
from backend.app.ml.detector import AnomalyDetector
from backend.app.services.ml_service import train_and_evaluate_pipeline
from backend.app.models.alert import Alert
from backend.app.models.transaction import Transaction, TransactionInput, TransactionOutput
from backend.app.models.entity import Wallet
from backend.app.models.dataset import Dataset
from backend.app.models.profile import EntityBehaviourProfile
from backend.app.validation.profiler import (
    derive_entity_behaviour_profile,
    compute_behavioural_deviations,
    build_and_store_profiles_for_dataset
)
from backend.app.services.demo_service import run_one_click_demo

# ==============================================================================
# Case 1: High Anomaly + Strong Historical Deviation -> High Contextual Validation
# ==============================================================================
def test_case_1_high_anomaly_strong_deviation():
    """
    Case 1:
    Entity exhibits strong deviation from its own historical baseline
    (e.g., velocity 24x above baseline, volume 15x above baseline, expanded counterparties).
    Validation layer should produce:
      - High validation_score (>= 0.75)
      - High confidence (>= 0.80)
      - Supporting evidence identifying specific deviations with observed vs baseline values
      - Empty counter-evidence
    """
    validator = ContextualValidator()

    raw_anomaly_score = 0.88
    baseline = {
        "has_sufficient_history": True,
        "observation_count": 12,
        "avg_velocity_per_hour": 0.5,
        "min_velocity_per_hour": 0.2,
        "max_velocity_per_hour": 1.0,
        "avg_amount": 0.40,
        "std_amount": 0.15,
        "max_amount": 0.80,
        "min_amount": 0.10,
        "counterparties_count": 3,
        "avg_time_between_txs_sec": 7200.0,
        "fan_in_ratio": 0.5,
        "fan_out_ratio": 0.5
    }

    current_features = {
        "tx_velocity_per_hour": 14.5,            # 29x baseline average
        "avg_tx_amount": 12.0,                   # 30x baseline average
        "unique_counterparties": 18,             # 6x baseline counterparties
        "avg_time_between_txs_sec": 65.0,        # compression to < 1% of normal
        "unique_observed_ips": 4,
        "unique_asns": 3,
        "unique_countries": 3
    }

    result = validator.validate_entity_anomaly(
        entity_id="bc1q_test_deviating_wallet",
        current_features=current_features,
        raw_anomaly_score=raw_anomaly_score,
        historical_baseline=baseline
    )

    # Assertions
    assert result["raw_anomaly_score"] == 0.88
    assert result["validation_score"] >= 0.75, f"Expected validation_score >= 0.75, got {result['validation_score']}"
    assert result["confidence"] >= 0.80, f"Expected confidence >= 0.80, got {result['confidence']}"
    assert len(result["supporting_evidence"]) >= 3
    assert len(result["counter_evidence"]) == 0

    # Verify supporting evidence format
    velocity_ev = next(e for e in result["supporting_evidence"] if e["feature"] == "tx_velocity_per_hour")
    assert velocity_ev["observed_value"] == 14.5
    assert velocity_ev["baseline_value"] == 0.5
    assert "higher than entity's historical baseline" in velocity_ev["reason"]

    # Verify explanation is based on actual calculated values
    assert "substantially deviates from the entity's historical baseline" in result["validation_explanation"]
    assert "High" in result["validation_explanation"]


# ==============================================================================
# Case 2: High Anomaly + Behaviour Consistent with Own History -> Reduced Confidence
# ==============================================================================
def test_case_2_high_anomaly_consistent_with_history():
    """
    Case 2 (The prompt's critical edge case):
    Historical velocity: 70–90 transactions/hour
    Current velocity: 82 transactions/hour
    Isolation Forest flags it as globally unusual (raw score = 0.85),
    BUT the entity normally operates at this velocity.
    Validation layer MUST:
      - Recognize behaviour is consistent with entity's own history
      - Produce counter-evidence
      - Reduce validation_score (<= 0.35)
      - Reduce confidence (<= 0.45)
      - Clearly explain the reduction
    """
    validator = ContextualValidator()

    raw_anomaly_score = 0.85
    baseline = {
        "has_sufficient_history": True,
        "observation_count": 25,
        "avg_velocity_per_hour": 80.0,
        "min_velocity_per_hour": 70.0,
        "max_velocity_per_hour": 90.0,
        "avg_amount": 50.0,
        "std_amount": 8.0,
        "max_amount": 75.0,
        "min_amount": 35.0,
        "counterparties_count": 10,
        "avg_time_between_txs_sec": 45.0
    }

    current_features = {
        "tx_velocity_per_hour": 82.0,            # 82 tx/hr is within 70-90 baseline range!
        "avg_tx_amount": 51.5,                   # within normal range of 50.0
        "unique_counterparties": 10,
        "avg_time_between_txs_sec": 44.0,
        "unique_observed_ips": 1
    }

    result = validator.validate_entity_anomaly(
        entity_id="bc1q_high_throughput_exchange_wallet",
        current_features=current_features,
        raw_anomaly_score=raw_anomaly_score,
        historical_baseline=baseline
    )

    # Assertions
    assert result["raw_anomaly_score"] == 0.85
    # Validation score must be reduced because behaviour matches entity's own history
    assert result["validation_score"] <= 0.35, f"Expected validation_score <= 0.35, got {result['validation_score']}"
    # Contextual confidence must be reduced
    assert result["confidence"] <= 0.45, f"Expected confidence <= 0.45, got {result['confidence']}"
    # Must have counter-evidence and no behavioral deviation
    assert len(result["supporting_evidence"]) == 0
    assert len(result["counter_evidence"]) >= 1

    # Verify counter-evidence reason details
    vel_counter = next(c for c in result["counter_evidence"] if c["feature"] == "tx_velocity_per_hour")
    assert vel_counter["counter_type"] == "CONSISTENT_WITH_HISTORICAL_VELOCITY"
    assert "consistent with the entity's normal historical operational range" in vel_counter["reason"]

    # Verify human-readable explanation states consistency and reduction
    assert "consistent with the entity's normal historical operational range" in result["validation_explanation"]
    assert "Contextual validation score" in result["validation_explanation"]
    assert "were reduced" in result["validation_explanation"]


# ==============================================================================
# Case 3: High Anomaly + Supporting and Counter-Evidence -> Balanced Validation
# ==============================================================================
def test_case_3_mixed_supporting_and_counter_evidence():
    """
    Case 3:
    Entity has a sudden velocity burst (supporting evidence),
    but transaction amounts and counterparty scope are consistent with history (counter-evidence).
    Validation layer should produce:
      - Balanced validation_score (0.35 - 0.65)
      - Medium confidence (0.45 - 0.65) reflecting conflicting evidence
      - Both supporting_evidence and counter_evidence lists populated
    """
    validator = ContextualValidator()

    raw_anomaly_score = 0.82
    baseline = {
        "has_sufficient_history": True,
        "observation_count": 10,
        "avg_velocity_per_hour": 1.0,
        "min_velocity_per_hour": 0.5,
        "max_velocity_per_hour": 1.8,
        "avg_amount": 10.0,
        "std_amount": 2.0,
        "max_amount": 15.0,
        "counterparties_count": 4,
        "avg_time_between_txs_sec": 3600.0
    }

    current_features = {
        "tx_velocity_per_hour": 12.0,            # 12x baseline -> supporting deviation
        "avg_tx_amount": 10.2,                   # consistent with 10.0 -> counter-evidence
        "unique_counterparties": 4,              # within normal scope -> counter-evidence
        "avg_time_between_txs_sec": 300.0,
        "unique_observed_ips": 1
    }

    result = validator.validate_entity_anomaly(
        entity_id="bc1q_mixed_signals_wallet",
        current_features=current_features,
        raw_anomaly_score=raw_anomaly_score,
        historical_baseline=baseline
    )

    # Assertions
    assert result["raw_anomaly_score"] == 0.82
    assert 0.35 <= result["validation_score"] <= 0.65, f"Expected 0.35 <= val <= 0.65, got {result['validation_score']}"
    assert 0.45 <= result["confidence"] <= 0.65, f"Expected 0.45 <= conf <= 0.65, got {result['confidence']}"
    assert len(result["supporting_evidence"]) >= 1
    assert len(result["counter_evidence"]) >= 1
    assert "conflicting contextual indicators" in result["validation_explanation"]


# ==============================================================================
# Case 4: New Entity / Insufficient History -> Low/Limited Confidence
# ==============================================================================
def test_case_4_insufficient_history():
    """
    Case 4:
    New entity with 0 or 1 historical observation.
    Validation layer MUST:
      - NOT fabricate a baseline
      - NOT treat missing history as suspicious
      - Set an appropriate low/limited confidence (0.35)
      - Clearly state 'Insufficient historical context'
    """
    validator = ContextualValidator()

    raw_anomaly_score = 0.78
    baseline = {
        "has_sufficient_history": False,
        "observation_count": 1,
        "min_required": 3,
        "status": "INSUFFICIENT_HISTORY",
        "message": "Insufficient historical context: Entity has only 1 recorded transaction."
    }

    current_features = {
        "tx_velocity_per_hour": 8.0,
        "avg_tx_amount": 5.0,
        "unique_counterparties": 2,
        "unique_observed_ips": 1
    }

    result = validator.validate_entity_anomaly(
        entity_id="bc1q_brand_new_wallet",
        current_features=current_features,
        raw_anomaly_score=raw_anomaly_score,
        historical_baseline=baseline
    )

    # Assertions
    assert result["raw_anomaly_score"] == 0.78
    assert result["historical_context"]["has_sufficient_history"] is False
    assert result["confidence"] == 0.35
    assert len(result["supporting_evidence"]) == 0
    assert len(result["counter_evidence"]) == 1
    assert result["counter_evidence"][0]["counter_type"] == "INSUFFICIENT_HISTORICAL_CONTEXT"
    assert "Insufficient historical context" in result["validation_explanation"]
    assert "Contextual confidence is limited" in result["validation_explanation"]


# ==============================================================================
# Case 5: Existing Anomaly Detector Output Remains Unchanged
# ==============================================================================
def test_case_5_detector_output_preservation():
    """
    Case 5:
    raw_anomaly_score must be IDENTICAL before and after adding validation.
    Isolation Forest model behaviour, scores, and predictions remain completely untouched.
    """
    np.random.seed(42)
    normal = np.random.normal(loc=1.0, scale=0.2, size=(20, 4))
    outlier = np.array([[10.0, 10.0, 10.0, 10.0]])
    data = np.vstack([normal, outlier])
    cols = ["tx_velocity_per_hour", "avg_tx_amount", "unique_counterparties", "unique_observed_ips"]
    df = pd.DataFrame(data, columns=cols, index=[f"W_{i}" for i in range(21)])

    detector = AnomalyDetector(model_type="ISOLATION_FOREST", contamination=0.05, random_state=42)
    detector.fit(df)
    scores, preds = detector.predict_anomaly_scores(df)

    # Target outlier index 20
    raw_score_before = float(scores[20])
    features_20 = df.loc["W_20"].to_dict()

    # Pass through contextual validator
    res = contextual_validator.validate_entity_anomaly(
        entity_id="W_20",
        current_features=features_20,
        raw_anomaly_score=raw_score_before
    )

    # Strict equality
    assert res["raw_anomaly_score"] == round(raw_score_before, 4)
    # Both raw and validation scores exist separately
    assert "raw_anomaly_score" in res
    assert "validation_score" in res
    assert "confidence" in res
    assert "supporting_evidence" in res
    assert "counter_evidence" in res
    assert "historical_context" in res
    assert "validation_explanation" in res


# ==============================================================================
# End-to-End Pipeline Integration Test
# ==============================================================================
def test_e2e_pipeline_generates_contextual_validation_alerts(db: Session):
    """
    Tests full pipeline execution:
    Executes one-click demo pipeline and verifies that generated Alert records
    contain raw_anomaly_score, validation_score, confidence, supporting_evidence,
    counter_evidence, historical_context, and validation_explanation.
    """
    result = run_one_click_demo(db, seed=42)
    assert result["status"] == "SUCCESS"

    alerts = db.query(Alert).all()
    assert len(alerts) > 0

    for a in alerts:
        # 1. raw_anomaly_score must be present and equal to anomaly_score
        assert a.raw_anomaly_score is not None
        assert abs(a.raw_anomaly_score - a.anomaly_score) < 1e-4

        # 2. validation_score must be present
        assert a.validation_score is not None
        assert 0.0 <= a.validation_score <= 1.0

        # 3. confidence must be present
        assert a.confidence is not None
        assert 0.0 <= a.confidence <= 1.0

        # 4. Contextual evidence collections must be present
        assert isinstance(a.supporting_evidence, list)
        assert isinstance(a.counter_evidence, list)
        assert isinstance(a.historical_context, dict)

        # 5. Validation explanation must be present and non-empty
        assert a.validation_explanation is not None
        assert len(a.validation_explanation) > 10
        assert "AI detected suspicious activity" not in a.validation_explanation


# ==============================================================================
# Derived Profiling from Raw SIH Synthetic Dataset Records
# ==============================================================================
def test_derive_entity_behaviour_profile_from_raw_sih_dataset_records():
    """
    Verifies that entity behavioural baselines are derived directly from the
    historical observations contained in the SIH synthetic dataset itself.
    The baseline is NOT manually supplied.
    """
    t0 = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    raw_records = [
        {
            "timestamp": t0 + timedelta(hours=1),
            "txid": "tx_01",
            "input_addresses": ["bc1q_alice_historical"],
            "output_addresses": ["bc1q_bob_peer"],
            "input_amounts": [1.0],
            "output_amounts": [0.8],
            "fee": 0.0001,
            "script_type": "P2WPKH",
            "src_ip": "192.168.1.10",
            "dst_ip": "192.168.1.20",
            "src_port": 8333,
            "dst_port": 8333,
            "geo_country": "US",
            "asn": "AS15169"
        },
        {
            "timestamp": t0 + timedelta(hours=2),
            "txid": "tx_02",
            "input_addresses": ["bc1q_alice_historical"],
            "output_addresses": ["bc1q_charlie_peer"],
            "input_amounts": [1.2],
            "output_amounts": [1.1],
            "fee": 0.0001,
            "script_type": "P2WPKH",
            "src_ip": "192.168.1.10",
            "dst_ip": "192.168.1.21",
            "src_port": 8333,
            "dst_port": 8333,
            "geo_country": "US",
            "asn": "AS15169"
        },
        {
            "timestamp": t0 + timedelta(hours=3),
            "txid": "tx_03",
            "input_addresses": ["bc1q_alice_historical"],
            "output_addresses": ["bc1q_bob_peer"],
            "input_amounts": [1.0],
            "output_amounts": [0.9],
            "fee": 0.0001,
            "script_type": "P2WPKH",
            "src_ip": "192.168.1.10",
            "dst_ip": "192.168.1.22",
            "src_port": 8333,
            "dst_port": 8333,
            "geo_country": "US",
            "asn": "AS15169"
        },
        {
            "timestamp": t0 + timedelta(hours=4),
            "txid": "tx_04",
            "input_addresses": ["bc1q_alice_historical"],
            "output_addresses": ["bc1q_dave_peer"],
            "input_amounts": [1.5],
            "output_amounts": [1.2],
            "fee": 0.0001,
            "script_type": "P2WPKH",
            "src_ip": "192.168.1.10",
            "dst_ip": "192.168.1.23",
            "src_port": 8333,
            "dst_port": 8333,
            "geo_country": "US",
            "asn": "AS15169"
        },
        {
            "timestamp": t0 + timedelta(hours=5),
            "txid": "tx_05",
            "input_addresses": ["bc1q_alice_historical"],
            "output_addresses": ["bc1q_bob_peer"],
            "input_amounts": [0.9],
            "output_amounts": [0.7],
            "fee": 0.0001,
            "script_type": "P2WPKH",
            "src_ip": "192.168.1.10",
            "dst_ip": "192.168.1.24",
            "src_port": 8333,
            "dst_port": 8333,
            "geo_country": "US",
            "asn": "AS15169"
        }
    ]

    profile = derive_entity_behaviour_profile(
        entity_id="bc1q_alice_historical",
        raw_observations=raw_records,
        min_observations=3
    )

    # Assert derived profile fields
    assert profile["entity_id"] == "bc1q_alice_historical"
    assert profile["observation_count"] == 5
    assert profile["has_sufficient_history"] is True
    assert profile["profile_reliability"] == "HIGH"

    # Transaction Amount Behaviour (Historical output amounts: 0.8, 1.1, 0.9, 1.2, 0.7 BTC)
    assert profile["median_output_amount"] == 0.9
    assert abs(profile["avg_output_amount"] - 0.94) < 1e-4
    assert profile["output_amount_dispersion"] > 0.0

    # Flow & Counterparties
    assert profile["unique_counterparty_count"] == 3  # bob, charlie, dave
    assert profile["typical_fan_in"] == 1.0
    assert profile["typical_fan_out"] == 1.0

    # Network Behaviour
    assert "192.168.1.10" in profile["observed_ips"]
    assert "US" in profile["observed_countries"]
    assert "AS15169" in profile["observed_asns"]
    assert profile["network_observation_count"] == 5


# ==============================================================================
# Avoid Data Leakage: Temporal Ordering at Time T
# ==============================================================================
def test_avoid_data_leakage_temporal_ordering():
    """
    Verifies that for an observation at time T:
      Historical baseline = observations belonging to the entity BEFORE T
      Current observation = observation at T
    A large anomalous transaction at T must NOT contaminate its own reference baseline.
    """
    t0 = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    historical_records = [
        {"timestamp": t0 + timedelta(hours=1), "txid": "tx_1", "output_amounts": [0.8], "input_amounts": [1.0], "output_addresses": ["peer_1"]},
        {"timestamp": t0 + timedelta(hours=2), "txid": "tx_2", "output_amounts": [1.1], "input_amounts": [1.2], "output_addresses": ["peer_2"]},
        {"timestamp": t0 + timedelta(hours=3), "txid": "tx_3", "output_amounts": [0.9], "input_amounts": [1.0], "output_addresses": ["peer_1"]},
        {"timestamp": t0 + timedelta(hours=4), "txid": "tx_4", "output_amounts": [1.2], "input_amounts": [1.3], "output_addresses": ["peer_3"]},
        {"timestamp": t0 + timedelta(hours=5), "txid": "tx_5", "output_amounts": [0.7], "input_amounts": [0.8], "output_addresses": ["peer_1"]},
    ]
    # Current anomalous transaction at T (25 BTC)
    t_eval = t0 + timedelta(hours=6)
    anomalous_record = {
        "timestamp": t_eval,
        "txid": "tx_anomalous_at_T",
        "output_amounts": [25.0],
        "input_amounts": [26.0],
        "output_addresses": ["peer_4"]
    }
    all_records = historical_records + [anomalous_record]

    # Derive baseline strictly before time T
    profile_before_T = derive_entity_behaviour_profile(
        entity_id="bc1q_leakage_test_wallet",
        raw_observations=all_records,
        min_observations=3,
        target_timestamp=t_eval
    )

    # Crucial assertion: the median output amount remains 0.9 BTC!
    assert profile_before_T["median_output_amount"] == 0.9
    assert profile_before_T["observation_count"] == 5

    # If leakage had occurred, the 25.0 BTC would have skewed the baseline
    # Now compute deviation of the observation at T
    current_obs = {
        "output_amount": 25.0,
        "avg_tx_amount": 25.0,
        "tx_velocity_per_hour": 1.0,
        "unique_counterparties": 1
    }
    deviations = compute_behavioural_deviations(current_obs, profile_before_T)

    assert deviations["has_deviation"] is True
    out_dev = deviations["deviations"]["output_amount"]
    assert out_dev["current"] == 25.0
    assert out_dev["historical_median"] == 0.9
    # Ratio ≈ 27.78x
    assert abs(out_dev["ratio"] - 27.78) < 0.1
    assert "Output amount increased" in deviations["what_changed"]


# ==============================================================================
# Scenario A: Strong Contextual Deviation (Learned Baseline)
# ==============================================================================
def test_scenario_a_strong_contextual_deviation_learned():
    """
    SCENARIO A — Strong contextual deviation:
    Entity A historically:
      avg/median output amount ≈ 1.0 BTC
      typical velocity ≈ 5 tx/hour
    Current:
      output amount = 20 BTC
      velocity = 30 tx/hour
    Expected:
      Isolation Forest -> anomaly
      Validation -> strong contextual support (high validation score, high confidence)
    """
    t0 = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    historical_records = [
        {"timestamp": t0 + timedelta(minutes=12 * i), "txid": f"tx_a_{i}", "output_amounts": [1.0 + (i % 3) * 0.1], "input_amounts": [1.2], "output_addresses": [f"peer_{i % 3}"]}
        for i in range(10)
    ]
    # Derive profile from raw history
    profile_a = derive_entity_behaviour_profile(
        entity_id="bc1q_entity_a",
        raw_observations=historical_records,
        min_observations=3
    )

    current_features = {
        "avg_tx_amount": 20.0,
        "output_amount": 20.0,
        "tx_velocity_per_hour": 30.0,
        "unique_counterparties": 12,
        "avg_time_between_txs_sec": 120.0,
        "unique_observed_ips": 3
    }
    raw_anomaly_score = 0.89

    res = contextual_validator.validate_entity_anomaly(
        entity_id="bc1q_entity_a",
        current_features=current_features,
        raw_anomaly_score=raw_anomaly_score,
        historical_baseline=profile_a
    )

    assert res["raw_anomaly_score"] == 0.89
    assert res["validation_score"] >= 0.75, f"Expected validation_score >= 0.75, got {res['validation_score']}"
    assert res["confidence"] >= 0.80, f"Expected confidence >= 0.80, got {res['confidence']}"
    assert len(res["supporting_evidence"]) >= 2
    assert len(res["counter_evidence"]) == 0
    assert "Output amount increased" in res["behavioural_deviation"]["what_changed"]


# ==============================================================================
# Scenario B: Anomaly but Normal for Entity (Learned Baseline)
# ==============================================================================
def test_scenario_b_anomaly_but_normal_for_entity_learned():
    """
    SCENARIO B — Anomaly but normal for entity:
    Entity B historically:
      output amounts = 20–30 BTC
      velocity = 20–35 tx/hour
    Current:
      output amount = 25 BTC
      velocity = 28 tx/hour
    Expected:
      Isolation Forest may still flag the observation depending on global feature distribution.
      BUT Contextual validation should recognize that behaviour is consistent with
      Entity B's own history and reduce contextual support.
    """
    t0 = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    historical_records = [
        {"timestamp": t0 + timedelta(minutes=2 * i), "txid": f"tx_b_{i}", "output_amounts": [20.0 + (i % 11)], "input_amounts": [25.0], "output_addresses": [f"peer_{i % 5}"]}
        for i in range(25)
    ]
    profile_b = derive_entity_behaviour_profile(
        entity_id="bc1q_entity_b_exchange",
        raw_observations=historical_records,
        min_observations=3
    )

    current_features = {
        "avg_tx_amount": 25.0,
        "output_amount": 25.0,
        "tx_velocity_per_hour": 28.0,
        "unique_counterparties": 5,
        "avg_time_between_txs_sec": 120.0,
        "unique_observed_ips": 1
    }
    raw_anomaly_score = 0.86  # flagged as global outlier by ML

    res = contextual_validator.validate_entity_anomaly(
        entity_id="bc1q_entity_b_exchange",
        current_features=current_features,
        raw_anomaly_score=raw_anomaly_score,
        historical_baseline=profile_b
    )

    assert res["raw_anomaly_score"] == 0.86
    # Contextual validation MUST recognize consistency with own history and reduce score
    assert res["validation_score"] <= 0.35, f"Expected validation_score <= 0.35, got {res['validation_score']}"
    assert res["confidence"] <= 0.45, f"Expected confidence <= 0.45, got {res['confidence']}"
    assert len(res["counter_evidence"]) >= 1
    assert "consistent with the entity's normal historical operational range" in res["validation_explanation"]
    assert "were reduced" in res["validation_explanation"]


# ==============================================================================
# Scenario C: New Entity / Insufficient History (Learned Baseline)
# ==============================================================================
def test_scenario_c_new_entity_learned():
    """
    SCENARIO C — New entity:
    Entity C: only 1–2 historical observations.
    Expected:
      Do not fabricate a baseline.
      Return "Insufficient historical context."
      Keep original anomaly score but assign limited contextual confidence.
    """
    t0 = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    historical_records = [
        {"timestamp": t0, "txid": "tx_c_1", "output_amounts": [1.5], "input_amounts": [1.6], "output_addresses": ["peer_c"]}
    ]
    profile_c = derive_entity_behaviour_profile(
        entity_id="bc1q_entity_c_new",
        raw_observations=historical_records,
        min_observations=3
    )

    assert profile_c["has_sufficient_history"] is False
    assert profile_c["profile_reliability"] == "INSUFFICIENT_HISTORY"

    current_features = {
        "avg_tx_amount": 10.0,
        "tx_velocity_per_hour": 15.0,
        "unique_counterparties": 3,
        "unique_observed_ips": 1
    }
    raw_anomaly_score = 0.82

    res = contextual_validator.validate_entity_anomaly(
        entity_id="bc1q_entity_c_new",
        current_features=current_features,
        raw_anomaly_score=raw_anomaly_score,
        historical_baseline=profile_c
    )

    assert res["raw_anomaly_score"] == 0.82
    assert res["confidence"] == 0.35
    assert "Insufficient historical context" in res["validation_explanation"]
    assert "Contextual confidence is limited" in res["validation_explanation"]


# ==============================================================================
# Final Acceptance Test: Answering the 6 Core Questions
# ==============================================================================
def test_section_16_six_acceptance_questions():
    """
    Demonstrates that the system directly answers all 6 questions required by Section 16:
      1. What is normal behaviour for this entity?
      2. What changed?
      3. What evidence supports the deviation?
      4. What evidence argues against it?
      5. How much historical data supports the baseline?
      6. How confident is the validation?
    """
    t0 = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    historical_amounts = [0.8, 1.1, 0.9, 1.2, 0.7, 0.9, 0.8, 0.9]
    raw_records = [
        {"timestamp": t0 + timedelta(hours=i), "txid": f"tx_{i}", "output_amounts": [historical_amounts[i]], "input_amounts": [1.2], "output_addresses": [f"p_{i % 3}"]}
        for i in range(8)
    ]
    profile = derive_entity_behaviour_profile("bc1q_investigative_target", raw_records, min_observations=3)

    current_features = {
        "output_amount": 25.0,
        "avg_tx_amount": 25.0,
        "tx_velocity_per_hour": 21.0,
        "unique_counterparties": 15,
        "avg_time_between_txs_sec": 150.0,
        "unique_observed_ips": 3
    }
    raw_anomaly_score = 0.91

    enriched_lead = contextual_validator.validate_entity_anomaly(
        entity_id="bc1q_investigative_target",
        current_features=current_features,
        raw_anomaly_score=raw_anomaly_score,
        historical_baseline=profile
    )

    # 1. "What is normal behaviour for this entity?"
    assert "historical_context" in enriched_lead
    normal_behaviour = enriched_lead["historical_context"]
    assert normal_behaviour["median_output_amount"] == 0.9
    assert normal_behaviour["observation_count"] == 8

    # 2. "What changed?"
    assert "behavioural_deviation" in enriched_lead
    what_changed = enriched_lead["behavioural_deviation"]["what_changed"]
    assert len(what_changed) > 0
    assert "Output amount increased" in what_changed

    # 3. "What evidence supports the deviation?"
    assert "supporting_evidence" in enriched_lead
    supporting = enriched_lead["supporting_evidence"]
    assert len(supporting) >= 2
    assert all("reason" in s and "observed_value" in s and "baseline_value" in s for s in supporting)

    # 4. "What evidence argues against it?"
    assert "counter_evidence" in enriched_lead
    counter = enriched_lead["counter_evidence"]
    assert isinstance(counter, list)

    # 5. "How much historical data supports the baseline?"
    sample_size = normal_behaviour["observation_count"]
    reliability = normal_behaviour["profile_reliability"]
    assert sample_size == 8
    assert reliability == "HIGH"

    # 6. "How confident is the validation?"
    assert "confidence" in enriched_lead
    confidence = enriched_lead["confidence"]
    assert 0.0 <= confidence <= 1.0
    assert confidence >= 0.80  # high confidence due to sample size + corroborated evidence


# ==============================================================================
# Database Persistence & Cascade Test for Entity Behaviour Profiles
# ==============================================================================
def test_entity_profile_db_storage_and_cascade(db: Session):
    """
    Verifies that build_and_store_profiles_for_dataset writes EntityBehaviourProfile
    records into the SQLite database and that cascade deletion works when the dataset is removed.
    """
    import uuid
    dataset_id = str(uuid.uuid4())
    dataset = Dataset(
        id=dataset_id,
        filename="test_profile_dataset.csv",
        format="csv",
        total_records=5,
        status="COMPLETED"
    )
    db.add(dataset)
    db.commit()

    # Add transactions for wallet
    addr = "bc1q_db_profile_test_wallet"
    w = Wallet(id=str(uuid.uuid4()), address=addr)
    db.add(w)

    t0 = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(5):
        txid = f"tx_db_prof_{i}"
        tx_id = str(uuid.uuid4())
        tx = Transaction(
            id=tx_id,
            dataset_id=dataset_id,
            txid=txid,
            timestamp=t0 + timedelta(hours=i),
            input_total=1.0,
            output_total=0.9
        )
        tin = TransactionInput(id=str(uuid.uuid4()), transaction_id=tx_id, txid=txid, wallet_address=addr, amount=1.0)
        tout = TransactionOutput(id=str(uuid.uuid4()), transaction_id=tx_id, txid=txid, wallet_address=f"peer_db_{i}", amount=0.9)
        db.add_all([tx, tin, tout])
    db.commit()

    # Build and persist profiles
    res = build_and_store_profiles_for_dataset(db, dataset_id=dataset_id, min_observations=3)
    assert len(res) >= 1

    # Verify query from database
    stored_profile = db.query(EntityBehaviourProfile).filter(
        EntityBehaviourProfile.dataset_id == dataset_id,
        EntityBehaviourProfile.entity_id == addr
    ).first()

    assert stored_profile is not None
    assert stored_profile.observation_count == 4  # Strictly prior to latest transaction (no data leakage)
    assert stored_profile.has_sufficient_history == 1
    assert stored_profile.median_input_amount == 1.0

    # Verify cascade deletion
    db.delete(dataset)
    db.commit()

    deleted_profile = db.query(EntityBehaviourProfile).filter(
        EntityBehaviourProfile.dataset_id == dataset_id
    ).first()
    assert deleted_profile is None

