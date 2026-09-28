"""
Inference Module for ML Anomaly Detection.
Applies trained Isolation Forest to calculate ml_anomaly_score and ml_anomaly_label.
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from backend.app.ml.feature_builder import build_feature_matrix
from backend.app.ml.model_loader import load_models

def predict_anomalies(
    feature_records: List[Dict[str, Any]],
    models_dir: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Predicts ml_anomaly_score and ml_anomaly_label for a batch of feature records.
    If no trained model is found on disk, computes statistical heuristic fallback.
    """
    if not feature_records:
        return []

    model, scaler = load_models(models_dir)
    df = build_feature_matrix(feature_records)
    X = df.values

    if model is not None and scaler is not None:
        X_scaled = scaler.transform(X)
        # Decision function: lower means more anomalous
        raw_scores = model.decision_function(X_scaled)
        labels = model.predict(X_scaled)  # -1 for anomaly, 1 for normal

        # Normalize score into [0.0, 1.0] where 1.0 is most anomalous
        min_s, max_s = raw_scores.min(), raw_scores.max()
        denom = (max_s - min_s) if (max_s - min_s) > 1e-6 else 1.0
        normalized_scores = 1.0 - ((raw_scores - min_s) / denom)

        results = []
        for i in range(len(feature_records)):
            results.append({
                "ml_anomaly_score": round(float(normalized_scores[i]), 4),
                "ml_anomaly_label": int(labels[i]),  # -1 or 1
                "is_ml_anomaly": bool(labels[i] == -1)
            })
        return results

    # Fallback heuristic if model not yet trained
    results = []
    for r in feature_records:
        fan_in = float(r.get("fan_in", 1))
        fan_out = float(r.get("fan_out", 1))
        amount = float(r.get("transaction_amount", 0.0))
        net_conf = float(r.get("network_confidence", 0.0))
        
        # Simple statistical heuristic proxy
        h_score = min(1.0, (fan_in * 0.05) + (fan_out * 0.05) + (amount * 0.01) + (net_conf * 0.4))
        label = -1 if h_score > 0.6 else 1
        results.append({
            "ml_anomaly_score": round(h_score, 4),
            "ml_anomaly_label": label,
            "is_ml_anomaly": bool(label == -1)
        })
    return results
