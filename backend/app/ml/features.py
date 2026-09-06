import math
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.models.transaction import Transaction, TransactionInput, TransactionOutput, IPObservation
from backend.app.models.entity import Wallet
from backend.app.models.feature import EntityFeature

def compute_entropy(counts: List[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    probs = [c / total for c in counts if c > 0]
    return -sum(p * math.log2(p) for p in probs)

def extract_wallet_features_from_db(db: Session, dataset_id: str = None) -> Tuple[pd.DataFrame, List[str]]:
    """
    Extracts 20+ behavioral, graph, and network features for every observed wallet.
    Returns (DataFrame of features indexed by wallet address, list of feature names).
    """
    # 1. Fetch transactions, inputs, outputs, and IP observations
    tx_query = db.query(Transaction)
    if dataset_id:
        tx_query = tx_query.filter(Transaction.dataset_id == dataset_id)
    txs = tx_query.all()
    tx_map = {t.id: t for t in txs}
    tx_txid_map = {t.txid: t for t in txs}
    tx_ids = list(tx_map.keys())

    if not tx_ids:
        return pd.DataFrame(), []

    inputs = db.query(TransactionInput).filter(TransactionInput.transaction_id.in_(tx_ids)).all()
    outputs = db.query(TransactionOutput).filter(TransactionOutput.transaction_id.in_(tx_ids)).all()

    ip_obs_query = db.query(IPObservation)
    if dataset_id:
        ip_obs_query = ip_obs_query.filter(IPObservation.dataset_id == dataset_id)
    ip_obs = ip_obs_query.all()

    # Map txid to IP observations
    tx_ip_map: Dict[str, List[IPObservation]] = {}
    for ipo in ip_obs:
        if ipo.txid not in tx_ip_map:
            tx_ip_map[ipo.txid] = []
        tx_ip_map[ipo.txid].append(ipo)

    # Aggregate wallet data
    wallets_data: Dict[str, Dict[str, Any]] = {}

    def get_or_create(addr: str):
        if addr not in wallets_data:
            wallets_data[addr] = {
                "in_txs": [],
                "out_txs": [],
                "in_amounts": [],
                "out_amounts": [],
                "counterparties": set(),
                "observed_ips": set(),
                "observed_countries": [],
                "observed_asns": [],
                "timestamps": []
            }
        return wallets_data[addr]

    # Map inputs: Wallet -> sending to tx
    # Counterparties will be the outputs of the same tx
    tx_outputs_map: Dict[str, List[str]] = {}
    for out in outputs:
        if out.txid not in tx_outputs_map:
            tx_outputs_map[out.txid] = []
        tx_outputs_map[out.txid].append(out.wallet_address)

    tx_inputs_map: Dict[str, List[str]] = {}
    for inp in inputs:
        if inp.txid not in tx_inputs_map:
            tx_inputs_map[inp.txid] = []
        tx_inputs_map[inp.txid].append(inp.wallet_address)

    for inp in inputs:
        w = get_or_create(inp.wallet_address)
        w["out_txs"].append(inp.txid)
        w["out_amounts"].append(inp.amount)
        if inp.txid in tx_txid_map:
            ts = tx_txid_map[inp.txid].timestamp
            w["timestamps"].append(ts)
        # Counterparties are outputs of this transaction
        for peer in tx_outputs_map.get(inp.txid, []):
            if peer != inp.wallet_address:
                w["counterparties"].add(peer)
        # Network observations
        for ipo in tx_ip_map.get(inp.txid, []):
            w["observed_ips"].add(ipo.src_ip)
            if ipo.country and ipo.country != "UNKNOWN":
                w["observed_countries"].append(ipo.country)
            if ipo.asn and ipo.asn != "UNKNOWN":
                w["observed_asns"].append(ipo.asn)

    for out in outputs:
        w = get_or_create(out.wallet_address)
        w["in_txs"].append(out.txid)
        w["in_amounts"].append(out.amount)
        if out.txid in tx_txid_map:
            ts = tx_txid_map[out.txid].timestamp
            w["timestamps"].append(ts)
        # Counterparties are inputs of this transaction
        for peer in tx_inputs_map.get(out.txid, []):
            if peer != out.wallet_address:
                w["counterparties"].add(peer)
        # Network observations
        for ipo in tx_ip_map.get(out.txid, []):
            w["observed_ips"].add(ipo.src_ip)
            if ipo.country and ipo.country != "UNKNOWN":
                w["observed_countries"].append(ipo.country)
            if ipo.asn and ipo.asn != "UNKNOWN":
                w["observed_asns"].append(ipo.asn)

    # Compute Feature Vectors
    feature_rows = []
    wallet_addresses = []

    for addr, data in wallets_data.items():
        in_cnt = len(data["in_txs"])
        out_cnt = len(data["out_txs"])
        total_cnt = in_cnt + out_cnt
        in_tot = sum(data["in_amounts"])
        out_tot = sum(data["out_amounts"])
        all_amts = data["in_amounts"] + data["out_amounts"]

        avg_amt = float(np.mean(all_amts)) if all_amts else 0.0
        max_amt = float(np.max(all_amts)) if all_amts else 0.0
        std_amt = float(np.std(all_amts)) if len(all_amts) > 1 else 0.0
        net_flow = in_tot - out_tot

        # Temporal dynamics
        timestamps = sorted([
            (t.replace(tzinfo=timezone.utc) if (isinstance(t, datetime) and t.tzinfo is None) else t)
            for t in data["timestamps"]
            if t is not None
        ])
        if len(timestamps) > 1:
            time_diffs = [(timestamps[i] - timestamps[i - 1]).total_seconds() for i in range(1, len(timestamps))]
            avg_time_between_sec = float(np.mean(time_diffs))
            total_duration_hours = max(1.0, (timestamps[-1] - timestamps[0]).total_seconds() / 3600.0)
            velocity_per_hour = total_cnt / total_duration_hours
        else:
            avg_time_between_sec = 86400.0  # Default 1 day
            velocity_per_hour = float(total_cnt)

        # Graph signals
        num_counterparties = len(data["counterparties"])
        fan_in_ratio = in_cnt / max(1, total_cnt)
        fan_out_ratio = out_cnt / max(1, total_cnt)
        graph_degree = num_counterparties + len(set(data["in_txs"] + data["out_txs"]))
        in_degree = in_cnt
        out_degree = out_cnt

        # Network signals
        unique_ips = len(data["observed_ips"])
        unique_asns = len(set(data["observed_asns"]))
        unique_countries = len(set(data["observed_countries"]))
        country_counts = [data["observed_countries"].count(c) for c in set(data["observed_countries"])]
        geo_entropy = compute_entropy(country_counts)

        row = {
            "tx_count_total": total_cnt,
            "tx_incoming_count": in_cnt,
            "tx_outgoing_count": out_cnt,
            "total_incoming_btc": in_tot,
            "total_outgoing_btc": out_tot,
            "avg_tx_amount": avg_amt,
            "max_tx_amount": max_amt,
            "std_tx_amount": std_amt,
            "net_flow_btc": net_flow,
            "tx_velocity_per_hour": velocity_per_hour,
            "avg_time_between_txs_sec": avg_time_between_sec,
            "unique_counterparties": num_counterparties,
            "fan_in_ratio": fan_in_ratio,
            "fan_out_ratio": fan_out_ratio,
            "graph_degree": graph_degree,
            "graph_in_degree": in_degree,
            "graph_out_degree": out_degree,
            "unique_observed_ips": unique_ips,
            "unique_asns": unique_asns,
            "unique_countries": unique_countries,
            "foreign_geo_entropy": geo_entropy
        }
        feature_rows.append(row)
        wallet_addresses.append(addr)

    df = pd.DataFrame(feature_rows, index=wallet_addresses)
    feature_names = list(df.columns) if not df.empty else []

    # Store features into EntityFeature table for persistence & explainability
    for addr, row in zip(wallet_addresses, feature_rows):
        feat_obj = EntityFeature(
            entity_id=addr,
            entity_type="WALLET",
            dataset_id=dataset_id,
            features=row
        )
        db.merge(feat_obj)
    db.commit()

    return df, feature_names
