"""
Model Training Module for Isolation Forest Anomaly Detection.
Supports sampled / chunked training without loading 600+ MB into memory.
Saves models to models/isolation_forest.joblib and models/scaler.joblib.
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from backend.app.ml.feature_builder import build_feature_matrix, ML_FEATURE_NAMES
from backend.app.ml.model_loader import save_models

logger = logging.getLogger("tracex.ml.train")

def train_isolation_forest(
    feature_records: List[Dict[str, Any]],
    contamination: float = 0.05,
    n_estimators: int = 100,
    random_state: int = 42,
    models_dir: Optional[Path] = None,
    max_samples: Optional[int] = 50000
) -> Dict[str, Any]:
    """
    Trains an Isolation Forest anomaly detector on extracted feature records.
    Uses RobustScaler to handle heavy-tailed cryptocurrency amounts and degrees.
    """
    if not feature_records:
        raise ValueError("Cannot train Isolation Forest: No feature records provided.")

    logger.info(f"Preparing feature matrix for {len(feature_records)} records...")
    df = build_feature_matrix(feature_records)

    # Subsample if large to protect RAM
    if max_samples and len(df) > max_samples:
        logger.info(f"Subsampling {max_samples} instances for model training...")
        df_train = df.sample(n=max_samples, random_state=random_state)
    else:
        df_train = df

    X = df_train.values

    # Fit RobustScaler
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    # Fit Isolation Forest
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1
    )
    model.fit(X_scaled)

    # Save models
    model_path, scaler_path = save_models(model, scaler, models_dir)

    train_scores = model.decision_function(X_scaled)
    preds = model.predict(X_scaled)
    anomalies_detected = int((preds == -1).sum())

    report = {
        "status": "TRAINED",
        "training_samples": len(df_train),
        "features": ML_FEATURE_NAMES,
        "anomalies_in_training": anomalies_detected,
        "contamination": contamination,
        "model_file": str(model_path),
        "scaler_file": str(scaler_path)
    }
    logger.info(f"Training completed: {report}")
    return report
