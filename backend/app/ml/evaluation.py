import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix

def evaluate_detector(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    anomaly_scores: np.ndarray,
    training_duration_ms: int = 0
) -> Dict[str, Any]:
    """
    Computes rigorous ML evaluation metrics against benchmark ground truth labels.
    """
    if len(y_true) == 0:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "roc_auc": 0.0,
            "pr_auc": 0.0,
            "false_positive_rate": 0.0,
            "detection_rate": 0.0,
            "training_duration_ms": training_duration_ms,
            "benchmark_disclaimer": "Metrics calculated using synthetic benchmark scenario ground truth."
        }

    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    try:
        roc_auc = float(roc_auc_score(y_true, anomaly_scores))
    except Exception:
        roc_auc = 0.5

    try:
        pr_auc = float(average_precision_score(y_true, anomaly_scores))
    except Exception:
        pr_auc = 0.5

    # False positive rate: FP / (FP + TN)
    try:
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        fpr = float(fp / max(1, fp + tn))
    except Exception:
        fpr = 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "false_positive_rate": round(fpr, 4),
        "detection_rate": round(recall, 4),
        "training_duration_ms": training_duration_ms,
        "sample_count": len(y_true),
        "benchmark_disclaimer": "Metrics calculated using synthetic benchmark scenario ground truth."
    }
