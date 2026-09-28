import uuid
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy.orm import Session

from backend.app.models.transaction import Transaction, TransactionInput, TransactionOutput, IPObservation
from backend.app.models.profile import EntityBehaviourProfile
from backend.app.core.logging import logger

def derive_entity_behaviour_profile(
    prior_tx_records: Any = None,
    entity_id: Any = None,
    min_observations: int = 3,
    target_timestamp: Optional[datetime] = None,
    raw_observations: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Derives an entity behavioural baseline profile strictly from historical observations
    belonging to the entity BEFORE the current observation time T (avoiding data leakage).

    Uses ONLY features derivable from SIH dataset fields:
    - input/output amounts, fees
    - transaction counts, timestamps, velocities, intervals
    - fan-in, fan-out, counterparty addresses
    - network observations (IPs, ports, ASNs, countries)
    """
    # 0. Handle flexible parameter ordering
    if raw_observations is not None:
        records_list = raw_observations
        actual_entity_id = str(entity_id or prior_tx_records or "")
    elif isinstance(prior_tx_records, list):
        records_list = prior_tx_records
        actual_entity_id = str(entity_id or "")
    elif isinstance(entity_id, list):
        records_list = entity_id
        actual_entity_id = str(prior_tx_records or "")
    else:
        records_list = []
        actual_entity_id = str(entity_id or prior_tx_records or "")

    # 1. Filter by target_timestamp if specified (avoid data leakage)
    valid_records = []
    for rec in records_list:
        ts = rec.get("timestamp")
        rec_dt = None
        if ts is not None:
            if isinstance(ts, str):
                try:
                    rec_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    pass
            elif isinstance(ts, datetime):
                rec_dt = ts
        if rec_dt is not None and rec_dt.tzinfo is None:
            rec_dt = rec_dt.replace(tzinfo=timezone.utc)

        if target_timestamp is not None and rec_dt is not None:
            tgt_dt = target_timestamp
            if tgt_dt.tzinfo is None:
                tgt_dt = tgt_dt.replace(tzinfo=timezone.utc)
            if rec_dt >= tgt_dt:
                continue
        valid_records.append(rec)

    count = len(valid_records)
    if count < min_observations:
        return {
            "entity_id": actual_entity_id,
            "has_sufficient_history": False,
            "observation_count": count,
            "min_required": min_observations,
            "profile_reliability": "INSUFFICIENT_HISTORY",
            "message": f"Insufficient historical context: Entity has {count} observation(s) prior to evaluation (minimum {min_observations} required)."
        }

    input_amounts: List[float] = []
    output_amounts: List[float] = []
    all_amounts: List[float] = []
    timestamps: List[datetime] = []
    counterparties: Set[str] = set()
    observed_ips: Set[str] = set()
    observed_ports: Set[int] = set()
    observed_asns: Set[str] = set()
    observed_countries: Set[str] = set()
    fan_ins: List[int] = []
    fan_outs: List[int] = []
    net_obs_count = 0

    for rec in valid_records:
        ts = rec.get("timestamp")
        if ts is not None:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    pass
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                timestamps.append(ts)

        # Inflow amounts (support both input_amounts and in_amounts)
        rec_in_amts = rec.get("input_amounts") or rec.get("in_amounts") or []
        if isinstance(rec_in_amts, (int, float)):
            rec_in_amts = [rec_in_amts]
        for amt in rec_in_amts:
            amt_f = float(amt)
            input_amounts.append(amt_f)
            all_amounts.append(amt_f)

        # Outflow amounts (support both output_amounts and out_amounts)
        rec_out_amts = rec.get("output_amounts") or rec.get("out_amounts") or []
        if isinstance(rec_out_amts, (int, float)):
            rec_out_amts = [rec_out_amts]
        for amt in rec_out_amts:
            amt_f = float(amt)
            output_amounts.append(amt_f)
            all_amounts.append(amt_f)

        # Addresses / Counterparties
        in_addrs = rec.get("input_addresses") or []
        out_addrs = rec.get("output_addresses") or []
        fan_ins.append(len(in_addrs) if in_addrs else 1)
        fan_outs.append(len(out_addrs) if out_addrs else 1)

        for addr in in_addrs + out_addrs + rec.get("counterparties", []):
            if addr and addr != actual_entity_id:
                counterparties.add(addr)

        # Network observations
        rec_ips = list(rec.get("ips", []))
        if rec.get("src_ip"):
            rec_ips.append(rec.get("src_ip"))
        if rec.get("dst_ip"):
            rec_ips.append(rec.get("dst_ip"))
        has_net = False
        for ip in rec_ips:
            if ip and ip != "UNKNOWN":
                observed_ips.add(ip)
                has_net = True

        rec_ports = list(rec.get("ports", []))
        if rec.get("src_port"):
            rec_ports.append(rec.get("src_port"))
        if rec.get("dst_port"):
            rec_ports.append(rec.get("dst_port"))
        for port in rec_ports:
            if port:
                try:
                    observed_ports.add(int(port))
                    has_net = True
                except Exception:
                    pass

        rec_asns = list(rec.get("asns", []))
        if rec.get("asn"):
            rec_asns.append(rec.get("asn"))
        for asn in rec_asns:
            if asn and asn != "UNKNOWN":
                observed_asns.add(asn)
                has_net = True

        rec_countries = list(rec.get("countries", []))
        if rec.get("geo_country"):
            rec_countries.append(rec.get("geo_country"))
        for country in rec_countries:
            if country and country != "UNKNOWN":
                observed_countries.add(country)
                has_net = True

        if has_net or rec_ips:
            net_obs_count += 1

    # 1. Amount Behaviour
    avg_in = float(np.mean(input_amounts)) if input_amounts else 0.0
    med_in = float(np.median(input_amounts)) if input_amounts else 0.0
    disp_in = float(np.std(input_amounts)) if len(input_amounts) > 1 else 0.0
    tot_in = float(sum(input_amounts))

    avg_out = float(np.mean(output_amounts)) if output_amounts else 0.0
    med_out = float(np.median(output_amounts)) if output_amounts else 0.0
    disp_out = float(np.std(output_amounts)) if len(output_amounts) > 1 else 0.0
    tot_out = float(sum(output_amounts))

    amount_dispersion = float(np.std(all_amounts)) if len(all_amounts) > 1 else 0.0

    # 2. Activity & Temporal Behaviour
    timestamps = sorted(timestamps)
    if len(timestamps) > 1:
        time_diffs = [(timestamps[i] - timestamps[i-1]).total_seconds() for i in range(1, len(timestamps))]
        avg_inter_sec = float(np.mean(time_diffs))
        dur_hours = max(0.5, (timestamps[-1] - timestamps[0]).total_seconds() / 3600.0)
        dur_days = max(1.0 / 24.0, (timestamps[-1] - timestamps[0]).total_seconds() / 86400.0)
        tx_velocity = float(len(timestamps) / dur_hours)
        tx_freq = float(len(timestamps) / dur_days)
        min_vel = float(min([1.0 / max(0.01, td / 3600.0) for td in time_diffs])) if time_diffs else tx_velocity * 0.7
        max_vel = float(max([1.0 / max(0.01, td / 3600.0) for td in time_diffs])) if time_diffs else tx_velocity * 1.3
    else:
        avg_inter_sec = 86400.0
        dur_hours = 1.0
        tx_velocity = 1.0
        tx_freq = 1.0
        min_vel = 0.5
        max_vel = 1.5

    # 3. Flow Behaviour
    fan_in = float(np.mean(fan_ins)) if fan_ins else 1.0
    fan_out = float(np.mean(fan_outs)) if fan_outs else 1.0

    reliability = "HIGH" if count >= 5 else "MEDIUM"

    temporal_stats = {
        "first_seen": timestamps[0].isoformat() if timestamps else None,
        "last_seen": timestamps[-1].isoformat() if timestamps else None,
        "active_duration_hours": round(dur_hours, 2),
        "peak_velocity_per_hour": round(max_vel, 2)
    }

    network_stats = {
        "unique_observed_ips": len(observed_ips),
        "observed_ips": list(observed_ips)[:10],
        "unique_ports": len(observed_ports),
        "unique_asns": len(observed_asns),
        "unique_countries": len(observed_countries),
        "asns": list(observed_asns)[:5],
        "countries": list(observed_countries)[:5]
    }

    return {
        "entity_id": actual_entity_id,
        "has_sufficient_history": True,
        "observation_count": count,
        "profile_reliability": reliability,
        "avg_input_amount": round(avg_in, 4),
        "median_input_amount": round(med_in, 4),
        "input_amount_dispersion": round(disp_in, 4),
        "avg_output_amount": round(avg_out, 4),
        "median_output_amount": round(med_out, 4),
        "output_amount_dispersion": round(disp_out, 4),
        "total_input_value": round(tot_in, 4),
        "total_output_value": round(tot_out, 4),
        "amount_dispersion": round(amount_dispersion, 4),
        "transaction_frequency": round(tx_freq, 2),
        "transaction_velocity": round(tx_velocity, 2),
        "min_velocity": round(min_vel, 2),
        "max_velocity": round(max_vel, 2),
        "avg_inter_transaction_time": round(avg_inter_sec, 1),
        "typical_fan_in": round(fan_in, 2),
        "typical_fan_out": round(fan_out, 2),
        "unique_counterparty_count": len(counterparties),
        "observed_ips": list(observed_ips),
        "observed_ports": list(observed_ports),
        "observed_asns": list(observed_asns),
        "observed_countries": list(observed_countries),
        "network_observation_count": net_obs_count,
        "temporal_statistics": temporal_stats,
        "network_statistics": network_stats
    }


def compute_behavioural_deviations(
    current_observation: Dict[str, Any],
    profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compares the current observation against the entity's learned historical profile.
    Calculates interpretable deviations answering 'What changed?'.
    """
    if not profile.get("has_sufficient_history", False):
        return {
            "has_deviation": False,
            "status": "INSUFFICIENT_HISTORY",
            "message": "Insufficient historical context to compute behavioral deviation.",
            "what_changed": "Cannot evaluate behavioral change: Entity has insufficient historical observations in dataset.",
            "deviations": {}
        }

    deviations: Dict[str, Any] = {}
    change_summaries: List[str] = []

    # 1. Output Amount Deviation
    current_out = float(current_observation.get("output_amount", current_observation.get("avg_tx_amount", 0.0)))
    base_med_out = float(profile.get("median_output_amount", 0.0))
    base_avg_out = float(profile.get("avg_output_amount", base_med_out))
    base_disp_out = float(profile.get("output_amount_dispersion", 0.0))
    ref_amt = base_med_out if base_med_out > 0.001 else base_avg_out

    if current_out > 0 and ref_amt > 0:
        ratio = current_out / ref_amt
        z_score = (current_out - base_avg_out) / max(0.01, base_disp_out) if base_disp_out > 0 else 0.0
        is_sig = ratio >= 2.0 or z_score >= 2.0
        deviations["output_amount"] = {
            "current": round(current_out, 4),
            "historical_median": round(ref_amt, 4),
            "ratio": round(ratio, 2),
            "z_score": round(z_score, 2),
            "is_significant": is_sig
        }
        if is_sig:
            change_summaries.append(f"Output amount increased {ratio:.1f}x above historical median ({current_out:.2f} BTC vs {ref_amt:.2f} BTC)")

    # 2. Transaction Velocity Deviation
    current_vel = float(current_observation.get("tx_velocity_per_hour", 0.0))
    base_vel = float(profile.get("transaction_velocity", 0.0))
    base_max_vel = float(profile.get("max_velocity", base_vel * 1.25))

    if current_vel > 0 and base_vel > 0:
        v_ratio = current_vel / base_vel
        is_sig = current_vel >= base_vel * 2.0 and current_vel > base_max_vel
        deviations["transaction_velocity"] = {
            "current": round(current_vel, 2),
            "historical_typical": round(base_vel, 2),
            "ratio": round(v_ratio, 2),
            "is_significant": is_sig
        }
        if is_sig:
            change_summaries.append(f"Transaction velocity increased {v_ratio:.1f}x ({current_vel:.1f} tx/hr vs {base_vel:.1f} tx/hr)")

    # 3. Counterparty Scope Deviation
    current_peers = int(current_observation.get("unique_counterparties", 0))
    base_peers = int(profile.get("unique_counterparty_count", 0))

    if current_peers > 0 and base_peers > 0:
        p_ratio = current_peers / base_peers
        is_sig = current_peers >= max(5, int(base_peers * 2.0))
        deviations["counterparties"] = {
            "current": current_peers,
            "historical_count": base_peers,
            "ratio": round(p_ratio, 2),
            "is_significant": is_sig
        }
        if is_sig:
            change_summaries.append(f"Counterparties expanded from typical {base_peers} to {current_peers}")

    # 4. Inter-Transaction Interval Compression
    current_interval = float(current_observation.get("avg_time_between_txs_sec", 86400.0))
    base_interval = float(profile.get("avg_inter_transaction_time", 86400.0))

    if base_interval > 120 and current_interval <= base_interval * 0.25:
        deviations["inter_tx_interval"] = {
            "current": round(current_interval, 1),
            "historical_average": round(base_interval, 1),
            "is_significant": True
        }
        change_summaries.append(f"Inter-transaction interval compressed to {current_interval:.0f}s (historical normal: {base_interval:.0f}s)")

    has_sig_deviation = any(d.get("is_significant", False) for d in deviations.values())

    what_changed_str = "; ".join(change_summaries) if change_summaries else "Current observation aligns with the entity's learned historical parameters."

    return {
        "has_deviation": has_sig_deviation,
        "status": "DEVIATION_ANALYSIS_COMPLETE",
        "what_changed": what_changed_str,
        "deviations": deviations
    }


def build_and_store_profiles_for_dataset(
    db: Session,
    dataset_id: Optional[str] = None,
    min_observations: int = 3
) -> Dict[str, EntityBehaviourProfile]:
    """
    Learns and persists an EntityBehaviourProfile for each observed wallet in the dataset.
    Uses temporal sequencing to avoid data leakage (prior observations vs latest observation).
    Stores profiles in the existing SQLite database.
    """
    # Fetch transactions and map inputs, outputs, and IPs
    tx_q = db.query(Transaction)
    if dataset_id:
        tx_q = tx_q.filter(Transaction.dataset_id == dataset_id)
    tx_records = tx_q.order_by(Transaction.timestamp.asc()).all()

    if not tx_records:
        return {}

    tx_map = {t.id: t for t in tx_records}
    tx_txid_map = {t.txid: t for t in tx_records}
    tx_ids = list(tx_map.keys())

    if dataset_id:
        inputs = db.query(TransactionInput).join(Transaction, TransactionInput.transaction_id == Transaction.id).filter(Transaction.dataset_id == dataset_id).all()
        outputs = db.query(TransactionOutput).join(Transaction, TransactionOutput.transaction_id == Transaction.id).filter(Transaction.dataset_id == dataset_id).all()
    else:
        inputs = db.query(TransactionInput).all()
        outputs = db.query(TransactionOutput).all()

    ip_q = db.query(IPObservation)
    if dataset_id:
        ip_q = ip_q.filter(IPObservation.dataset_id == dataset_id)
    ip_obs = ip_q.all()

    tx_ips_map: Dict[str, List[IPObservation]] = {}
    for ipo in ip_obs:
        if ipo.txid not in tx_ips_map:
            tx_ips_map[ipo.txid] = []
        tx_ips_map[ipo.txid].append(ipo)

    # Group records per wallet chronologically
    wallet_events: Dict[str, List[Dict[str, Any]]] = {}

    for inp in inputs:
        addr = inp.wallet_address
        if addr not in wallet_events:
            wallet_events[addr] = []
        tx_obj = tx_txid_map.get(inp.txid)
        if tx_obj:
            wallet_events[addr].append({
                "txid": inp.txid,
                "timestamp": tx_obj.timestamp,
                "in_amounts": [inp.amount],
                "out_amounts": [],
                "counterparties": [o.wallet_address for o in outputs if o.txid == inp.txid and o.wallet_address != addr],
                "ips": [ipo.src_ip for ipo in tx_ips_map.get(inp.txid, [])],
                "ports": [ipo.src_port for ipo in tx_ips_map.get(inp.txid, []) if ipo.src_port],
                "asns": [ipo.asn for ipo in tx_ips_map.get(inp.txid, []) if ipo.asn and ipo.asn != "UNKNOWN"],
                "countries": [ipo.country for ipo in tx_ips_map.get(inp.txid, []) if ipo.country and ipo.country != "UNKNOWN"]
            })

    for out in outputs:
        addr = out.wallet_address
        if addr not in wallet_events:
            wallet_events[addr] = []
        tx_obj = tx_txid_map.get(out.txid)
        if tx_obj:
            wallet_events[addr].append({
                "txid": out.txid,
                "timestamp": tx_obj.timestamp,
                "in_amounts": [],
                "out_amounts": [out.amount],
                "counterparties": [i.wallet_address for i in inputs if i.txid == out.txid and i.wallet_address != addr],
                "ips": [ipo.src_ip for ipo in tx_ips_map.get(out.txid, [])],
                "ports": [ipo.src_port for ipo in tx_ips_map.get(out.txid, []) if ipo.src_port],
                "asns": [ipo.asn for ipo in tx_ips_map.get(out.txid, []) if ipo.asn and ipo.asn != "UNKNOWN"],
                "countries": [ipo.country for ipo in tx_ips_map.get(out.txid, []) if ipo.country and ipo.country != "UNKNOWN"]
            })

    # Clean old profiles for dataset
    if dataset_id:
        db.query(EntityBehaviourProfile).filter(EntityBehaviourProfile.dataset_id == dataset_id).delete()
        db.commit()

    stored_profiles: Dict[str, EntityBehaviourProfile] = {}

    for addr, events in wallet_events.items():
        # Sort chronologically
        events.sort(key=lambda e: e["timestamp"])

        # Temporal split to prevent data leakage:
        # If an entity has multiple transactions, historical baseline = events[:-1]
        # strictly prior to the latest transaction
        prior_events = events[:-1] if len(events) > min_observations else events

        profile_data = derive_entity_behaviour_profile(prior_events, addr, min_observations=min_observations)

        prof_obj = EntityBehaviourProfile(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            entity_id=addr,
            entity_type="WALLET",
            observation_count=profile_data["observation_count"],
            has_sufficient_history=profile_data["has_sufficient_history"],
            profile_reliability=profile_data["profile_reliability"],
            avg_input_amount=profile_data.get("avg_input_amount", 0.0),
            median_input_amount=profile_data.get("median_input_amount", 0.0),
            input_amount_dispersion=profile_data.get("input_amount_dispersion", 0.0),
            avg_output_amount=profile_data.get("avg_output_amount", 0.0),
            median_output_amount=profile_data.get("median_output_amount", 0.0),
            output_amount_dispersion=profile_data.get("output_amount_dispersion", 0.0),
            total_input_value=profile_data.get("total_input_value", 0.0),
            total_output_value=profile_data.get("total_output_value", 0.0),
            amount_dispersion=profile_data.get("amount_dispersion", 0.0),
            transaction_frequency=profile_data.get("transaction_frequency", 0.0),
            transaction_velocity=profile_data.get("transaction_velocity", 0.0),
            min_velocity=profile_data.get("min_velocity", 0.0),
            max_velocity=profile_data.get("max_velocity", 0.0),
            avg_inter_transaction_time=profile_data.get("avg_inter_transaction_time", 0.0),
            typical_fan_in=profile_data.get("typical_fan_in", 0.0),
            typical_fan_out=profile_data.get("typical_fan_out", 0.0),
            unique_counterparty_count=profile_data.get("unique_counterparty_count", 0),
            temporal_statistics=profile_data.get("temporal_statistics", {}),
            network_statistics=profile_data.get("network_statistics", {})
        )
        db.add(prof_obj)
        stored_profiles[addr] = prof_obj

    db.commit()
    logger.info(f"Learned behavioural profiles for {len(stored_profiles)} entities in dataset.")
    return stored_profiles
