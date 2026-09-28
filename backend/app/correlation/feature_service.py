"""
Behavioral and topological graph feature extraction module.
Calculates fan_in, fan_out, degree, ratios, amounts, counterparty diversity,
and network correlation features for downstream analysis and ML anomaly detection.
"""
from typing import Dict, Any, List, Optional
import numpy as np

def extract_features(
    record: Dict[str, Any],
    wallet_info: Dict[str, Any],
    network_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes unified behavioral and topological feature vector for a transaction.
    """
    fan_in = int(record.get("fan_in", 1))
    fan_out = int(record.get("fan_out", 1))
    degree = fan_in + fan_out
    fan_ratio = float(fan_in / max(1, fan_out))

    total_amount = float(record.get("total_input_amount", 0.0))
    fee = float(record.get("fee", 0.0))
    amount_per_output = float(record.get("amount_per_output", 0.0))

    wallet_count = int(wallet_info.get("wallet_count", 0))
    unique_counterparties = len(wallet_info.get("related_wallets", []))

    network_confidence = float(network_info.get("network_confidence", 0.0))
    time_diff = network_info.get("time_difference_seconds")
    temporal_distance = float(time_diff) if time_diff is not None else 999.0

    return {
        "fan_in": fan_in,
        "fan_out": fan_out,
        "degree": degree,
        "fan_ratio": round(fan_ratio, 4),
        "transaction_amount": round(total_amount, 6),
        "fee": round(fee, 8),
        "amount_per_output": round(amount_per_output, 6),
        "wallet_count": wallet_count,
        "number_of_connected_wallets": wallet_count,
        "unique_counterparties": unique_counterparties,
        "network_correlation_strength": round(network_confidence, 4),
        "network_confidence": round(network_confidence, 4),
        "temporal_distance": round(temporal_distance, 2),
        "time_difference_seconds": temporal_distance
    }
