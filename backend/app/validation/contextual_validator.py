import numpy as np
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy.orm import Session

from backend.app.models.transaction import Transaction, TransactionInput, TransactionOutput, IPObservation
from backend.app.models.profile import EntityBehaviourProfile
from backend.app.validation.profiler import compute_behavioural_deviations
from backend.app.core.logging import logger

@dataclass
class ValidatorConfig:
    """
    Centralized, transparent configuration for the Contextual Validation Layer.
    All weights, thresholds, and tolerances are isolated here for auditability and easy tuning.
    """
    # Minimum observations required to establish a valid entity historical baseline
    min_historical_observations: int = 3

    # Feature deviation thresholds against entity's own baseline
    velocity_deviation_multiplier: float = 2.0       # e.g., current velocity >= 2.0x historical average
    amount_deviation_multiplier: float = 2.0         # e.g., current amount >= 2.0x historical median/average
    amount_z_threshold: float = 2.0                  # or >= 2 standard deviations above historical mean
    counterparty_deviation_multiplier: float = 2.0   # e.g., distinct counterparties >= 2.0x baseline
    interval_drop_multiplier: float = 0.25           # inter-tx interval dropped to < 25% of baseline (rapid burst)

    # Consistency tolerance (margin within which current behavior is deemed consistent with entity's history)
    consistency_tolerance: float = 0.25              # within 25% of historical average or within historical range

    # Component weights for Validation Score (must sum to 1.0)
    w_raw_anomaly: float = 0.35                      # base Isolation Forest anomaly signal
    w_historical_deviation: float = 0.45             # weight of entity's own historical deviation
    w_network_corroboration: float = 0.20            # weight of corroborated network/infrastructure signals

    # Counter-evidence attenuation factor (how strongly counter-evidence reduces validation score)
    counter_evidence_attenuation_factor: float = 0.60

    # Contextual confidence calibration
    confidence_insufficient_history: float = 0.35    # bounded low confidence when baseline cannot be built
    confidence_base_with_history: float = 0.65       # baseline confidence with sufficient history
    confidence_per_supporting_signal: float = 0.08   # boost per verified supporting signal (capped at 0.95)
    confidence_conflict_penalty: float = 0.15        # deduction when supporting and counter signals conflict
    confidence_consistent_reduction: float = 0.38    # reduced confidence when entity matches own history


class ContextualValidator:
    """
    Contextual Validation Layer sitting between the Isolation Forest anomaly detector
    and the investigative lead output stage.

    Evaluates:
      CURRENT ENTITY BEHAVIOUR vs ENTITY'S OWN LEARNED HISTORICAL BEHAVIOUR

    Answers:
      - What is normal behaviour for this entity?
      - What changed?
      - What evidence supports the deviation?
      - What evidence argues against it?
      - How much historical data supports the baseline?
      - How confident is the validation?
    """

    def __init__(self, config: Optional[ValidatorConfig] = None):
        self.config = config or ValidatorConfig()

    def compute_historical_baseline_from_db(
        self,
        db: Session,
        entity_id: str,
        dataset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates an entity-specific baseline using historical transaction data
        belonging to the entity strictly prior to the latest transaction in the database (avoiding data leakage).
        """
        if db is None:
            return {
                "has_sufficient_history": False,
                "observation_count": 0,
                "min_required": self.config.min_historical_observations,
                "profile_reliability": "INSUFFICIENT_HISTORY",
                "status": "INSUFFICIENT_HISTORY",
                "message": "Insufficient historical context: No database session available."
            }

        inputs = db.query(TransactionInput).filter(TransactionInput.wallet_address == entity_id).all()
        outputs = db.query(TransactionOutput).filter(TransactionOutput.wallet_address == entity_id).all()

        tx_in_map = {i.txid: i.amount for i in inputs}
        tx_out_map = {o.txid: o.amount for o in outputs}
        all_txids = list(set(list(tx_in_map.keys()) + list(tx_out_map.keys())))

        if len(all_txids) < self.config.min_historical_observations:
            return {
                "has_sufficient_history": False,
                "observation_count": len(all_txids),
                "min_required": self.config.min_historical_observations,
                "profile_reliability": "INSUFFICIENT_HISTORY",
                "status": "INSUFFICIENT_HISTORY",
                "message": f"Insufficient historical context: Entity has only {len(all_txids)} recorded transaction(s) (minimum {self.config.min_historical_observations} required)."
            }

        # Query transactions ordered chronologically
        tx_records = []
        BATCH_SIZE = 500
        for i in range(0, len(all_txids), BATCH_SIZE):
            sub_batch = all_txids[i : i + BATCH_SIZE]
            tx_records.extend(db.query(Transaction).filter(Transaction.txid.in_(sub_batch)).all())
        tx_records.sort(key=lambda t: t.timestamp if t.timestamp else datetime.min)
        if len(tx_records) < self.config.min_historical_observations:
            return {
                "has_sufficient_history": False,
                "observation_count": len(tx_records),
                "min_required": self.config.min_historical_observations,
                "profile_reliability": "INSUFFICIENT_HISTORY",
                "status": "INSUFFICIENT_HISTORY",
                "message": f"Insufficient historical context: Entity has only {len(tx_records)} recorded transaction(s)."
            }

        # Avoid Data Leakage: Use transactions prior to latest transaction for baseline
        baseline_records = tx_records[:-1] if len(tx_records) > self.config.min_historical_observations else tx_records

        amounts = []
        out_amounts = []
        in_amounts = []
        timestamps = []
        counterparties = set()
        in_count = 0
        out_count = 0

        for tx in baseline_records:
            if tx.timestamp is not None:
                t = tx.timestamp
                if isinstance(t, datetime) and t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                timestamps.append(t)

            if tx.txid in tx_in_map:
                amt = float(tx_in_map[tx.txid])
                out_amounts.append(amt)
                amounts.append(amt)
                out_count += 1
            if tx.txid in tx_out_map:
                amt = float(tx_out_map[tx.txid])
                in_amounts.append(amt)
                amounts.append(amt)
                in_count += 1

            peers_in = db.query(TransactionInput.wallet_address).filter(TransactionInput.txid == tx.txid).all()
            for p in peers_in:
                if p[0] != entity_id:
                    counterparties.add(p[0])
            peers_out = db.query(TransactionOutput.wallet_address).filter(TransactionOutput.txid == tx.txid).all()
            for p in peers_out:
                if p[0] != entity_id:
                    counterparties.add(p[0])

        timestamps = sorted(timestamps)
        avg_amt = float(np.mean(amounts)) if amounts else 0.0
        std_amt = float(np.std(amounts)) if len(amounts) > 1 else 0.0
        max_amt = float(np.max(amounts)) if amounts else 0.0
        min_amt = float(np.min(amounts)) if amounts else 0.0

        med_out = float(np.median(out_amounts)) if out_amounts else (float(np.median(amounts)) if amounts else 0.0)
        avg_out = float(np.mean(out_amounts)) if out_amounts else avg_amt

        if len(timestamps) > 1:
            time_diffs = [(timestamps[i] - timestamps[i-1]).total_seconds() for i in range(1, len(timestamps))]
            avg_interval = float(np.mean(time_diffs))
            total_hours = max(1.0, (timestamps[-1] - timestamps[0]).total_seconds() / 3600.0)
            avg_vel = float(len(timestamps) / total_hours)
            min_vel = float(min([1.0 / max(0.01, (td / 3600.0)) for td in time_diffs])) if time_diffs else avg_vel * 0.7
            max_vel = float(max([1.0 / max(0.01, (td / 3600.0)) for td in time_diffs])) if time_diffs else avg_vel * 1.3
        else:
            avg_interval = 86400.0
            avg_vel = 1.0
            min_vel = 0.5
            max_vel = 1.5

        total_tx = in_count + out_count
        fan_in = in_count / max(1, total_tx)
        fan_out = out_count / max(1, total_tx)
        reliability = "HIGH" if len(baseline_records) >= 6 else "MEDIUM"

        return {
            "has_sufficient_history": True,
            "observation_count": len(baseline_records),
            "profile_reliability": reliability,
            "total_recorded_transactions": len(tx_records),
            "status": "SUFFICIENT_HISTORY",
            "avg_amount": round(avg_amt, 4),
            "std_amount": round(std_amt, 4),
            "max_amount": round(max_amt, 4),
            "min_amount": round(min_amt, 4),
            "median_output_amount": round(med_out, 4),
            "avg_output_amount": round(avg_out, 4),
            "avg_velocity_per_hour": round(avg_vel, 2),
            "transaction_velocity": round(avg_vel, 2),
            "min_velocity_per_hour": round(min_vel, 2),
            "max_velocity_per_hour": round(max_vel, 2),
            "avg_time_between_txs_sec": round(avg_interval, 1),
            "counterparties_count": len(counterparties),
            "unique_counterparty_count": len(counterparties),
            "typical_fan_in": round(fan_in, 2),
            "typical_fan_out": round(fan_out, 2),
            "fan_in_ratio": round(fan_in, 2),
            "fan_out_ratio": round(fan_out, 2),
            "normal_behaviour": {
                "median_output_amount": round(med_out, 4),
                "avg_output_amount": round(avg_out, 4),
                "typical_velocity": round(avg_vel, 2),
                "velocity_range": [round(min_vel, 2), round(max_vel, 2)],
                "unique_counterparties": len(counterparties),
                "typical_fan_in": round(fan_in, 2),
                "typical_fan_out": round(fan_out, 2)
            }
        }

    def resolve_baseline(
        self,
        db: Optional[Session],
        entity_id: str,
        dataset_id: Optional[str] = None,
        historical_baseline: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Resolves the baseline from either an explicitly passed profile (for testing/overrides),
        the stored EntityBehaviourProfile table, or automatically queries the entity's history in the DB.
        """
        if historical_baseline is not None:
            has_suff = historical_baseline.get(
                "has_sufficient_history",
                historical_baseline.get("observation_count", 0) >= self.config.min_historical_observations
            )
            base_copy = dict(historical_baseline)
            base_copy["has_sufficient_history"] = has_suff
            if not has_suff and "message" not in base_copy:
                base_copy["message"] = f"Insufficient historical context: {base_copy.get('observation_count', 0)} observations."
                base_copy["status"] = "INSUFFICIENT_HISTORY"
                base_copy["profile_reliability"] = "INSUFFICIENT_HISTORY"
            elif has_suff:
                if "status" not in base_copy:
                    base_copy["status"] = "SUFFICIENT_HISTORY"
                if "profile_reliability" not in base_copy:
                    base_copy["profile_reliability"] = "HIGH" if base_copy.get("observation_count", 0) >= 6 else "MEDIUM"
                # Populate normal_behaviour if not present
                if "normal_behaviour" not in base_copy:
                    med_amt = base_copy.get("median_output_amount", base_copy.get("avg_amount", 0.0))
                    base_copy["normal_behaviour"] = {
                        "median_output_amount": med_amt,
                        "avg_output_amount": base_copy.get("avg_output_amount", med_amt),
                        "typical_velocity": base_copy.get("avg_velocity_per_hour", 1.0),
                        "velocity_range": [base_copy.get("min_velocity_per_hour", 0.5), base_copy.get("max_velocity_per_hour", 1.5)],
                        "unique_counterparties": base_copy.get("counterparties_count", 0),
                        "typical_fan_in": base_copy.get("fan_in_ratio", 0.5),
                        "typical_fan_out": base_copy.get("fan_out_ratio", 0.5)
                    }
            return base_copy

        if db is not None:
            # 1. First check if an EntityBehaviourProfile was already learned and stored
            try:
                prof_query = db.query(EntityBehaviourProfile).filter(EntityBehaviourProfile.entity_id == entity_id)
                if dataset_id:
                    prof_query = prof_query.filter(EntityBehaviourProfile.dataset_id == dataset_id)
                prof = prof_query.first()
                if prof:
                    med_amt = prof.median_output_amount or prof.avg_output_amount or prof.median_input_amount or prof.avg_input_amount
                    return {
                        "has_sufficient_history": bool(prof.has_sufficient_history),
                        "observation_count": prof.observation_count,
                        "profile_reliability": prof.profile_reliability,
                        "status": "SUFFICIENT_HISTORY" if prof.has_sufficient_history else "INSUFFICIENT_HISTORY",
                        "avg_input_amount": prof.avg_input_amount,
                        "median_input_amount": prof.median_input_amount,
                        "input_amount_dispersion": prof.input_amount_dispersion,
                        "avg_output_amount": prof.avg_output_amount,
                        "median_output_amount": prof.median_output_amount,
                        "output_amount_dispersion": prof.output_amount_dispersion,
                        "avg_amount": prof.avg_output_amount or prof.avg_input_amount,
                        "std_amount": prof.amount_dispersion,
                        "max_amount": med_amt * 1.5 if med_amt else 1.0,
                        "transaction_velocity": prof.transaction_velocity,
                        "avg_velocity_per_hour": prof.transaction_velocity,
                        "min_velocity_per_hour": prof.min_velocity,
                        "max_velocity_per_hour": prof.max_velocity,
                        "avg_time_between_txs_sec": prof.avg_inter_transaction_time,
                        "counterparties_count": prof.unique_counterparty_count,
                        "unique_counterparty_count": prof.unique_counterparty_count,
                        "typical_fan_in": prof.typical_fan_in,
                        "typical_fan_out": prof.typical_fan_out,
                        "fan_in_ratio": prof.typical_fan_in,
                        "fan_out_ratio": prof.typical_fan_out,
                        "network_statistics": prof.network_statistics,
                        "temporal_statistics": prof.temporal_statistics,
                        "normal_behaviour": {
                            "median_output_amount": prof.median_output_amount,
                            "avg_output_amount": prof.avg_output_amount,
                            "typical_velocity": prof.transaction_velocity,
                            "velocity_range": [prof.min_velocity, prof.max_velocity],
                            "unique_counterparties": prof.unique_counterparty_count,
                            "typical_fan_in": prof.typical_fan_in,
                            "typical_fan_out": prof.typical_fan_out
                        }
                    }
            except Exception:
                pass

            return self.compute_historical_baseline_from_db(db, entity_id, dataset_id)

        return {
            "has_sufficient_history": False,
            "observation_count": 0,
            "min_required": self.config.min_historical_observations,
            "profile_reliability": "INSUFFICIENT_HISTORY",
            "status": "INSUFFICIENT_HISTORY",
            "message": "Insufficient historical context: No prior historical observations recorded."
        }

    def identify_supporting_evidence(
        self,
        current_features: Dict[str, Any],
        baseline: Dict[str, Any],
        raw_anomaly_score: float
    ) -> List[Dict[str, Any]]:
        """
        Identifies signals supporting the anomaly using actual values from dataset.
        Answering: 'What evidence supports the deviation?'
        """
        evidence: List[Dict[str, Any]] = []
        if not baseline.get("has_sufficient_history", False):
            return evidence

        # 1. Transaction Amount / Output Amount
        obs_amt = float(current_features.get("output_amount", current_features.get("avg_tx_amount", 0.0)))
        base_med_amt = float(baseline.get("median_output_amount", baseline.get("avg_amount", 0.0)))
        base_avg_amt = float(baseline.get("avg_output_amount", baseline.get("avg_amount", base_med_amt)))
        base_std_amt = float(baseline.get("output_amount_dispersion", baseline.get("std_amount", 0.0)))
        base_max_amt = float(baseline.get("max_amount", base_med_amt * 1.3))
        ref_amt = base_med_amt if base_med_amt > 0.001 else base_avg_amt

        if ref_amt > 0 and obs_amt >= ref_amt * self.config.amount_deviation_multiplier and obs_amt > base_max_amt:
            ratio = obs_amt / max(0.001, ref_amt)
            evidence.append({
                "feature": "output_amount",
                "observed_value": round(obs_amt, 4),
                "baseline_value": round(ref_amt, 4),
                "deviation_type": "UNUSUAL_VOLUME_SURGE",
                "reason": f"Output amount = {obs_amt:.2f} BTC; entity historical median = {ref_amt:.2f} BTC ({ratio:.1f}x deviation)."
            })

        # 2. Transaction Velocity
        obs_vel = float(current_features.get("tx_velocity_per_hour", 0.0))
        base_avg_vel = float(baseline.get("avg_velocity_per_hour", baseline.get("transaction_velocity", 0.0)))
        base_max_vel = float(baseline.get("max_velocity_per_hour", baseline.get("max_velocity", base_avg_vel)))

        if base_avg_vel > 0 and obs_vel >= base_avg_vel * self.config.velocity_deviation_multiplier and obs_vel > base_max_vel:
            ratio = obs_vel / max(0.01, base_avg_vel)
            evidence.append({
                "feature": "tx_velocity_per_hour",
                "observed_value": round(obs_vel, 2),
                "baseline_value": round(base_avg_vel, 2),
                "deviation_type": "HISTORICAL_VELOCITY_SURGE",
                "reason": f"Transaction velocity ({obs_vel:.1f} tx/hr) is {ratio:.1f}x higher than entity's historical baseline ({base_avg_vel:.1f} tx/hr)."
            })

        # 3. Counterparties / Fan-out
        obs_peers = int(current_features.get("unique_counterparties", 0))
        base_peers = int(baseline.get("counterparties_count", baseline.get("unique_counterparty_count", 0)))
        if base_peers > 0 and obs_peers >= max(5, int(base_peers * self.config.counterparty_deviation_multiplier)):
            evidence.append({
                "feature": "unique_counterparties",
                "observed_value": obs_peers,
                "baseline_value": base_peers,
                "deviation_type": "COUNTERPARTY_NETWORK_EXPANSION",
                "reason": f"Transacted with {obs_peers} distinct counterparties, significantly exceeding the entity's historical interaction scope ({base_peers} peers)."
            })

        # 4. Temporal Inter-Transaction Intervals
        obs_interval = float(current_features.get("avg_time_between_txs_sec", 86400.0))
        base_interval = float(baseline.get("avg_time_between_txs_sec", baseline.get("avg_inter_transaction_time", 86400.0)))
        if base_interval > 120 and obs_interval <= base_interval * self.config.interval_drop_multiplier:
            evidence.append({
                "feature": "avg_time_between_txs_sec",
                "observed_value": round(obs_interval, 1),
                "baseline_value": round(base_interval, 1),
                "deviation_type": "RAPID_INTERVAL_COMPRESSION",
                "reason": f"Inter-transaction interval dropped to {obs_interval:.0f}s (historical normal: {base_interval:.0f}s), indicating rapid burst/peeling sequence."
            })

        # 5. Network / Multi-IP Dispersal Corroboration
        unique_ips = int(current_features.get("unique_observed_ips", 0))
        unique_asns = int(current_features.get("unique_asns", 0))
        unique_countries = int(current_features.get("unique_countries", 0))
        if unique_ips >= 3 or (unique_asns >= 2 and unique_countries >= 2):
            evidence.append({
                "feature": "unique_observed_ips",
                "observed_value": unique_ips,
                "baseline_value": 1,
                "deviation_type": "NETWORK_INFRASTRUCTURE_DISPERSAL",
                "reason": f"Transaction propagation observed across {unique_ips} distinct IPs ({unique_asns} ASNs, {unique_countries} jurisdictions)."
            })

        return evidence

    def identify_counter_evidence(
        self,
        current_features: Dict[str, Any],
        baseline: Dict[str, Any],
        raw_anomaly_score: float
    ) -> List[Dict[str, Any]]:
        """
        Identifies signals suggesting the behaviour may actually be normal for this entity.
        Answering: 'What evidence argues against it?'
        """
        counter_evidence: List[Dict[str, Any]] = []

        # 1. Check for Insufficient History
        if not baseline.get("has_sufficient_history", False):
            counter_evidence.append({
                "feature": "historical_context",
                "observed_value": f"{baseline.get('observation_count', 0)} observation(s)",
                "baseline_value": None,
                "counter_type": "INSUFFICIENT_HISTORICAL_CONTEXT",
                "reason": "Entity has insufficient historical observations to establish a baseline; anomaly cannot be verified against historical behaviour."
            })
            return counter_evidence

        # 2. Velocity Consistency
        obs_vel = float(current_features.get("tx_velocity_per_hour", 0.0))
        base_avg_vel = float(baseline.get("avg_velocity_per_hour", baseline.get("transaction_velocity", 0.0)))
        base_min_vel = float(baseline.get("min_velocity_per_hour", baseline.get("min_velocity", base_avg_vel * 0.75)))
        base_max_vel = float(baseline.get("max_velocity_per_hour", baseline.get("max_velocity", base_avg_vel * 1.25)))

        if base_avg_vel > 0:
            is_consistent_vel = False
            if base_min_vel <= obs_vel <= base_max_vel * 1.1:
                is_consistent_vel = True
            elif abs(obs_vel - base_avg_vel) / max(0.1, base_avg_vel) <= self.config.consistency_tolerance:
                is_consistent_vel = True

            if is_consistent_vel:
                counter_evidence.append({
                    "feature": "tx_velocity_per_hour",
                    "observed_value": round(obs_vel, 2),
                    "baseline_value": round(base_avg_vel, 2),
                    "counter_type": "CONSISTENT_WITH_HISTORICAL_VELOCITY",
                    "reason": f"Current transaction velocity ({obs_vel:.1f} tx/hr) is consistent with the entity's normal historical operational range ({base_min_vel:.1f}–{base_max_vel:.1f} tx/hr)."
                })

        # 3. Transaction Amount Consistency
        obs_amt = float(current_features.get("output_amount", current_features.get("avg_tx_amount", 0.0)))
        base_med_amt = float(baseline.get("median_output_amount", baseline.get("avg_amount", 0.0)))
        base_avg_amt = float(baseline.get("avg_output_amount", baseline.get("avg_amount", base_med_amt)))
        base_max_amt = float(baseline.get("max_amount", base_med_amt * 1.3))
        base_std_amt = float(baseline.get("output_amount_dispersion", baseline.get("std_amount", 0.0)))

        ref_amt = base_med_amt if base_med_amt > 0.001 else base_avg_amt
        if ref_amt > 0:
            is_consistent_amt = False
            if obs_amt <= base_max_amt and abs(obs_amt - ref_amt) / max(0.01, ref_amt) <= self.config.consistency_tolerance:
                is_consistent_amt = True
            elif base_std_amt > 0 and abs(obs_amt - base_avg_amt) <= 1.2 * base_std_amt:
                is_consistent_amt = True

            if is_consistent_amt:
                counter_evidence.append({
                    "feature": "avg_tx_amount",
                    "observed_value": round(obs_amt, 4),
                    "baseline_value": round(ref_amt, 4),
                    "counter_type": "CONSISTENT_TRANSACTION_VOLUME",
                    "reason": f"Transaction amount ({obs_amt:.2f} BTC) aligns with the entity's established historical volume ({ref_amt:.2f} BTC median/avg, peak {base_max_amt:.2f} BTC)."
                })

        # 4. Counterparty Network Scope Consistency
        obs_peers = int(current_features.get("unique_counterparties", 0))
        base_peers = int(baseline.get("counterparties_count", baseline.get("unique_counterparty_count", 0)))
        if base_peers > 0 and obs_peers <= base_peers + 1:
            counter_evidence.append({
                "feature": "unique_counterparties",
                "observed_value": obs_peers,
                "baseline_value": base_peers,
                "counter_type": "NORMAL_COUNTERPARTY_SCOPE",
                "reason": f"Counterparty interactions ({obs_peers} peers) are within the entity's typical historical interaction scope ({base_peers} peers)."
            })

        # 5. Weak or Ambiguous Network Attribution
        unique_ips = int(current_features.get("unique_observed_ips", 0))
        if unique_ips <= 1:
            counter_evidence.append({
                "feature": "unique_observed_ips",
                "observed_value": unique_ips,
                "baseline_value": 1,
                "counter_type": "WEAK_NETWORK_ATTRIBUTION",
                "reason": "Network attribution is single-hop or unverified; no corroborated multi-jurisdiction relaying."
            })

        return counter_evidence

    def compute_validation_score(
        self,
        raw_anomaly_score: float,
        supporting_evidence: List[Dict[str, Any]],
        counter_evidence: List[Dict[str, Any]],
        has_sufficient_history: bool
    ) -> float:
        """
        Computes the validation_score (0.0 to 1.0).
        Represents contextual support for further investigation relative to learned behaviour.
        Does NOT represent probability of crime or illicit activity.
        """
        s_raw = min(1.0, max(0.0, float(raw_anomaly_score)))

        if not has_sufficient_history:
            return round(s_raw * 0.70, 4)

        behavioral_supp = [e for e in supporting_evidence if e.get("feature") != "unique_observed_ips"]
        network_supp = [e for e in supporting_evidence if e.get("feature") == "unique_observed_ips"]

        n_supp = len(behavioral_supp)
        if n_supp > 0:
            d_hist = min(1.0, 0.40 * n_supp + (0.20 if any("SURGE" in e.get("deviation_type", "") for e in behavioral_supp) else 0.0))
        else:
            d_hist = 0.0

        c_net = 0.85 if len(network_supp) > 0 else 0.20

        s_composite = (
            self.config.w_raw_anomaly * s_raw +
            self.config.w_historical_deviation * d_hist +
            self.config.w_network_corroboration * c_net
        )

        behavioral_counter = [c for c in counter_evidence if "CONSISTENT" in c.get("counter_type", "")]
        n_counter = len(behavioral_counter)

        if n_counter > 0:
            attenuation = self.config.counter_evidence_attenuation_factor * (n_counter / (n_counter + 1.0))
            if n_supp == 0:
                attenuation = max(attenuation, 0.65)
            s_composite = s_composite * (1.0 - attenuation)

        return round(float(min(1.0, max(0.0, s_composite))), 4)

    def compute_confidence(
        self,
        supporting_evidence: List[Dict[str, Any]],
        counter_evidence: List[Dict[str, Any]],
        has_sufficient_history: bool,
        profile_reliability: str = "MEDIUM"
    ) -> float:
        """
        Computes confidence (0.0 to 1.0) reflecting:
        - How much historical data supports the baseline (sample size)
        - Evidence quality and consistency
        """
        if not has_sufficient_history:
            return round(self.config.confidence_insufficient_history, 2)

        n_supp = len(supporting_evidence)
        behavioral_counter = [c for c in counter_evidence if "CONSISTENT" in c.get("counter_type", "")]
        n_counter = len(behavioral_counter)

        # Base confidence boosted by profile reliability
        base_conf = self.config.confidence_base_with_history
        if profile_reliability == "HIGH":
            base_conf += 0.05

        if n_supp > 0 and n_counter == 0:
            conf = base_conf + (self.config.confidence_per_supporting_signal * n_supp)
            return round(min(0.95, conf), 2)

        if n_supp == 0 and n_counter > 0:
            return round(self.config.confidence_consistent_reduction, 2)

        if n_supp > 0 and n_counter > 0:
            conf = base_conf - self.config.confidence_conflict_penalty
            return round(max(0.45, min(0.65, conf)), 2)

        return round(base_conf, 2)

    def generate_validation_explanation(
        self,
        raw_anomaly_score: float,
        validation_score: float,
        confidence: float,
        supporting_evidence: List[Dict[str, Any]],
        counter_evidence: List[Dict[str, Any]],
        baseline: Dict[str, Any]
    ) -> str:
        """
        Generates a concise explanation from actual calculated values.
        Never generates generic text such as 'AI detected suspicious activity'.
        """
        if not baseline.get("has_sufficient_history", False):
            obs_cnt = baseline.get("observation_count", 0)
            return (
                f"Insufficient historical context ({obs_cnt} transaction observation{'s' if obs_cnt != 1 else ''}) "
                f"to establish a reliable baseline for this entity. Anomaly score ({raw_anomaly_score:.2f}) reflects "
                f"global population outlier divergence without historical entity corroboration. Contextual confidence is limited."
            )

        n_supp = len(supporting_evidence)
        behavioral_counter = [c for c in counter_evidence if "CONSISTENT" in c.get("counter_type", "")]
        n_counter = len(behavioral_counter)

        conf_desc = "High" if confidence >= 0.75 else "Medium" if confidence >= 0.50 else "Low"

        if n_supp == 0 and n_counter > 0:
            counter_reasons = "; ".join([c["reason"] for c in behavioral_counter[:2]])
            return (
                f"Although the entity was flagged by the anomaly detector (raw score: {raw_anomaly_score:.2f}), "
                f"{counter_reasons} Contextual validation score ({validation_score:.2f}) and confidence ({conf_desc}) were reduced."
            )

        if n_supp > 0 and n_counter == 0:
            supp_reasons = " ".join([s["reason"] for s in supporting_evidence[:2]])
            return (
                f"{supp_reasons} Current activity substantially deviates from the entity's historical baseline. "
                f"Contextual confidence: {conf_desc}."
            )

        if n_supp > 0 and n_counter > 0:
            supp_str = supporting_evidence[0]["reason"]
            counter_str = behavioral_counter[0]["reason"]
            return (
                f"{supp_str} However, {counter_str} Contextual confidence: {conf_desc} due to conflicting contextual indicators."
            )

        return (
            f"Contextual validation completed. Raw anomaly score: {raw_anomaly_score:.2f}, "
            f"Validation score: {validation_score:.2f}. Contextual confidence: {conf_desc}."
        )

    def validate_entity_anomaly(
        self,
        entity_id: str,
        current_features: Dict[str, Any],
        raw_anomaly_score: float,
        db: Optional[Session] = None,
        dataset_id: Optional[str] = None,
        historical_baseline: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main execution method for the Contextual Validation Layer.
        Sits directly between Isolation Forest output and Lead/Alert generation.

        Returns enriched result:
          - raw_anomaly_score
          - validation_score
          - confidence
          - behavioural_deviation
          - historical_context
          - supporting_evidence
          - counter_evidence
          - validation_explanation
        """
        # 1. Resolve learned historical baseline
        baseline = self.resolve_baseline(db, entity_id, dataset_id, historical_baseline)
        has_suff = baseline.get("has_sufficient_history", False)
        reliability = baseline.get("profile_reliability", "MEDIUM")

        # 2. Compute Interpretable Behavioural Deviations ("What changed?")
        behavioural_deviation = compute_behavioural_deviations(current_features, baseline)

        # 3. Identify Supporting Evidence ("What evidence supports the deviation?")
        supporting_evidence = self.identify_supporting_evidence(current_features, baseline, raw_anomaly_score)

        # 4. Identify Counter-Evidence ("What evidence argues against it?")
        counter_evidence = self.identify_counter_evidence(current_features, baseline, raw_anomaly_score)

        # 5. Compute Validation Score
        validation_score = self.compute_validation_score(
            raw_anomaly_score=raw_anomaly_score,
            supporting_evidence=supporting_evidence,
            counter_evidence=counter_evidence,
            has_sufficient_history=has_suff
        )

        # 6. Compute Confidence ("How much historical data supports the baseline?")
        confidence = self.compute_confidence(
            supporting_evidence=supporting_evidence,
            counter_evidence=counter_evidence,
            has_sufficient_history=has_suff,
            profile_reliability=reliability
        )

        # 7. Generate Human-Readable Explanation
        explanation = self.generate_validation_explanation(
            raw_anomaly_score=raw_anomaly_score,
            validation_score=validation_score,
            confidence=confidence,
            supporting_evidence=supporting_evidence,
            counter_evidence=counter_evidence,
            baseline=baseline
        )

        return {
            "raw_anomaly_score": round(float(raw_anomaly_score), 4),
            "validation_score": validation_score,
            "confidence": confidence,
            "behavioural_deviation": behavioural_deviation,
            "supporting_evidence": supporting_evidence,
            "counter_evidence": counter_evidence,
            "historical_context": baseline,
            "validation_explanation": explanation
        }


# Singleton instance ready for injection into pipeline
contextual_validator = ContextualValidator()
