import math
import gc
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
    # 1. Fetch lightweight column tuples instead of full ORM objects (~10-50x less memory)
    tx_ts_query = db.query(Transaction.txid, Transaction.timestamp)
    if dataset_id:
        tx_ts_query = tx_ts_query.filter(Transaction.dataset_id == dataset_id)
    tx_timestamp_map: Dict[str, Any] = {txid: ts for txid, ts in tx_ts_query.all()}

    if not tx_timestamp_map:
        return pd.DataFrame(), []

    # Load inputs/outputs as (txid, wallet_address, amount) tuples
    inp_query = db.query(TransactionInput.txid, TransactionInput.wallet_address, TransactionInput.amount)
    out_query = db.query(TransactionOutput.txid, TransactionOutput.wallet_address, TransactionOutput.amount)
    if dataset_id:
        inp_query = inp_query.join(Transaction, TransactionInput.transaction_id == Transaction.id).filter(Transaction.dataset_id == dataset_id)
        out_query = out_query.join(Transaction, TransactionOutput.transaction_id == Transaction.id).filter(Transaction.dataset_id == dataset_id)
    inputs_tuples = inp_query.all()
    outputs_tuples = out_query.all()

    # Load IP observations as (txid, src_ip, country, asn) tuples
    ip_obs_query = db.query(IPObservation.txid, IPObservation.src_ip, IPObservation.country, IPObservation.asn)
    if dataset_id:
        ip_obs_query = ip_obs_query.filter(IPObservation.dataset_id == dataset_id)
    ip_obs_tuples = ip_obs_query.all()

    # Map txid to IP observation tuples
    tx_ip_map: Dict[str, List[tuple]] = {}
    for row in ip_obs_tuples:
        tx_ip_map.setdefault(row[0], []).append(row)
    del ip_obs_tuples

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
    for txid, wallet_address, _amt in outputs_tuples:
        tx_outputs_map.setdefault(txid, []).append(wallet_address)

    tx_inputs_map: Dict[str, List[str]] = {}
    for txid, wallet_address, _amt in inputs_tuples:
        tx_inputs_map.setdefault(txid, []).append(wallet_address)

    for txid, wallet_address, amount in inputs_tuples:
        w = get_or_create(wallet_address)
        w["out_txs"].append(txid)
        w["out_amounts"].append(amount)
        ts = tx_timestamp_map.get(txid)
        if ts:
            w["timestamps"].append(ts)
        # Counterparties are outputs of this transaction
        for peer in tx_outputs_map.get(txid, []):
            if peer != wallet_address:
                w["counterparties"].add(peer)
        # Network observations  (tuple: txid, src_ip, country, asn)
        for ipo in tx_ip_map.get(txid, []):
            w["observed_ips"].add(ipo[1])
            if ipo[2] and ipo[2] != "UNKNOWN":
                w["observed_countries"].append(ipo[2])
            if ipo[3] and ipo[3] != "UNKNOWN":
                w["observed_asns"].append(ipo[3])
    del inputs_tuples

    for txid, wallet_address, amount in outputs_tuples:
        w = get_or_create(wallet_address)
        w["in_txs"].append(txid)
        w["in_amounts"].append(amount)
        ts = tx_timestamp_map.get(txid)
        if ts:
            w["timestamps"].append(ts)
        # Counterparties are inputs of this transaction
        for peer in tx_inputs_map.get(txid, []):
            if peer != wallet_address:
                w["counterparties"].add(peer)
        # Network observations  (tuple: txid, src_ip, country, asn)
        for ipo in tx_ip_map.get(txid, []):
            w["observed_ips"].add(ipo[1])
            if ipo[2] and ipo[2] != "UNKNOWN":
                w["observed_countries"].append(ipo[2])
            if ipo[3] and ipo[3] != "UNKNOWN":
                w["observed_asns"].append(ipo[3])
    del outputs_tuples, tx_ip_map, tx_outputs_map, tx_inputs_map, tx_timestamp_map
    gc.collect()

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

    # Store features into EntityFeature table for persistence & explainability in safe batches
    feat_objs = [
        EntityFeature(
            entity_id=addr,
            entity_type="WALLET",
            dataset_id=dataset_id,
            features=row
        ) for addr, row in zip(wallet_addresses, feature_rows)
    ]
    for i in range(0, len(feat_objs), 500):
        for obj in feat_objs[i:i + 500]:
            db.merge(obj)
        db.commit()

    return df, feature_names
