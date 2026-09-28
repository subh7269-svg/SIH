"""
Feature Builder for Machine Learning Anomaly Detection.
Transforms behavioral correlation records into clean numerical numpy arrays / pandas DataFrames
for Isolation Forest training and inference.
"""
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np

ML_FEATURE_NAMES = [
    "fan_in",
    "fan_out",
    "transaction_amount",
    "fee",
    "wallet_count",
    "network_confidence",
    "time_difference_seconds",
    "degree",
    "unique_counterparties"
]

def build_feature_vector(record: Dict[str, Any]) -> List[float]:
    """Extracts a single numerical feature vector matching ML_FEATURE_NAMES."""
    time_diff = record.get("time_difference_seconds")
    if time_diff is None or np.isnan(float(time_diff)):
        time_diff = 999.0

    fan_in = float(record.get("fan_in", 1))
    fan_out = float(record.get("fan_out", 1))
    degree = float(record.get("degree", fan_in + fan_out))
    amount = float(record.get("transaction_amount", record.get("total_input_amount", 0.0)))
    fee = float(record.get("fee", 0.0))
    wallet_count = float(record.get("wallet_count", 0))
    net_conf = float(record.get("network_confidence", 0.0))
    counterparties = float(record.get("unique_counterparties", wallet_count))

    return [
        fan_in,
        fan_out,
        amount,
        fee,
        wallet_count,
        net_conf,
        float(time_diff),
        degree,
        counterparties
    ]

def build_feature_matrix(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Builds a pandas DataFrame from a list of transaction/correlation records."""
    rows = [build_feature_vector(r) for r in records]
    df = pd.DataFrame(rows, columns=ML_FEATURE_NAMES)
    return df.fillna(0.0)
