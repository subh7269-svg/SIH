import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.alert import Alert
from backend.app.models.audit import AuditLog
from backend.app.services.replay_service import get_investigation_replay, get_investigation_replay_by_entity

def test_investigation_replay_end_to_end(client: TestClient, db: Session):
    # 1. Create a realistic Alert in DB simulating an anomalous wallet with contextual validation & dynamic baseline
    alert = Alert(
        id="alert-replay-test-001",
        dataset_id=None,
        entity_id="bc1q_test_replay_wallet_alpha",
        entity_type="WALLET",
        anomaly_score=0.92,
        raw_anomaly_score=0.88,
        validation_score=0.95,
        priority_score=94,
        severity="CRITICAL",
        confidence=0.87,
        status="NEW",
        reasons=["High transaction velocity deviation (3.5x)", "Rapid counterparty fan-out"],
        explanation_details={"velocity_zscore": 3.5, "fan_out_zscore": 2.8},
        behavioural_deviation={
            "what_changed": "Transaction burst rate surged 4.2x above historical baseline.",
            "deviations": [{"feature": "velocity", "observed": 12.5, "baseline": 3.0}]
        },
        supporting_evidence=[
            {
                "feature": "tx_velocity",
                "observed_value": 12.5,
                "baseline_value": 3.0,
                "deviation_type": "SURGE",
                "reason": "Sudden burst of 12.5 tx/hr"
            }
        ],
        counter_evidence=[],
        historical_context={
            "has_sufficient_history": True,
            "observation_count": 8,
            "avg_velocity_per_hour": 3.0,
            "avg_amount": 1.25,
            "counterparties_count": 4,
            "profile_reliability": "ESTABLISHED"
        },
        validation_explanation="Entity exhibited severe velocity surge compared to its 8 prior observed transactions.",
        evidence_summary={
            "related_transactions": ["tx_replay_01", "tx_replay_02"],
            "observed_ips": ["198.51.100.22"],
            "subscores": {"ml_score": 0.92, "velocity_score": 0.95}
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(alert)
    db.commit()

    # 2. Query replay via REST API by alert_id
    resp = client.get(f"/api/v1/alerts/{alert.id}/replay")
    assert resp.status_code == 200, resp.text
    replay = resp.json()

    assert replay["alert_id"] == "alert-replay-test-001"
    assert replay["entity_id"] == "bc1q_test_replay_wallet_alpha"
    assert replay["priority_score"] == 94
    assert replay["severity"] == "CRITICAL"

    # Verify all 6 chronological stages are present
    stages = replay["stages"]
    assert len(stages) == 6
    stage_ids = [s["stage_id"] for s in stages]
    assert stage_ids == [
        "anomaly_detected",
        "contextual_validation",
        "historical_baseline",
        "evidence_collected",
        "graph_investigation",
        "investigative_lead"
    ]

    # Stage 1: Anomaly Detected verification
    s1 = stages[0]
    assert s1["stage_name"] == "Anomaly Detected"
    assert s1["data"]["anomaly_score"] == 0.92
    assert s1["data"]["raw_anomaly_score"] == 0.88
    assert "High transaction velocity deviation" in s1["data"]["triggering_reasons"][0]

    # Stage 2: Contextual Validation verification
    s2 = stages[1]
    assert s2["stage_name"] == "Contextual Validation"
    assert s2["data"]["validation_score"] == 0.95
    assert s2["data"]["confidence"] == 0.87
    assert s2["data"]["confidence_percentage"] == 87
    assert "severe velocity surge" in s2["data"]["validation_explanation"]

    # Stage 3: Historical Baseline Comparison verification
    s3 = stages[2]
    assert s3["stage_name"] == "Historical Baseline Comparison"
    assert s3["data"]["has_sufficient_history"] is True
    assert s3["data"]["observation_count"] == 8
    assert "4.2x above historical baseline" in s3["data"]["what_changed"]

    # Stage 4: Evidence Collected verification
    s4 = stages[3]
    assert s4["stage_name"] == "Evidence Collected"
    assert len(s4["data"]["supporting_evidence"]) == 1
    assert s4["data"]["related_transactions"] == ["tx_replay_01", "tx_replay_02"]
    assert s4["data"]["observed_ips"] == ["198.51.100.22"]

    # Stage 5: Graph / Fund-Flow Investigation verification
    s5 = stages[4]
    assert s5["stage_name"] == "Graph / Fund-Flow Investigation"
    assert s5["data"]["focal_entity_id"] == "bc1q_test_replay_wallet_alpha"
    assert s5["data"]["k_hop_depth"] == 2

    # Stage 6: Investigative Lead verification
    s6 = stages[5]
    assert s6["stage_name"] == "Investigative Lead"
    assert s6["data"]["lead_id"] == "alert-replay-test-001"
    assert s6["data"]["priority_score"] == 94
    assert s6["data"]["severity"] == "CRITICAL"

    # 3. Query replay via REST API by entity_id
    resp_entity = client.get(f"/api/v1/alerts/entity/{alert.entity_id}/replay")
    assert resp_entity.status_code == 200
    assert resp_entity.json()["alert_id"] == "alert-replay-test-001"

    # 4. Check audit log was recorded
    audit = db.query(AuditLog).filter(
        AuditLog.action == "INVESTIGATION_REPLAY_VIEWED",
        AuditLog.target_id == alert.id
    ).first()
    assert audit is not None
    assert audit.target_type == "ALERT"

    # 5. Non-existent alert returns 404
    resp_404 = client.get("/api/v1/alerts/nonexistent-alert/replay")
    assert resp_404.status_code == 404
