import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import RobustScaler, StandardScaler
from backend.app.core.config import settings

class AnomalyDetector:
    def __init__(self, model_type: str = "ISOLATION_FOREST", contamination: float = 0.05, random_state: int = 42):
        self.model_type = model_type.upper()
        self.contamination = contamination
        self.random_state = random_state
        self.scaler = RobustScaler()
        self.feature_names = []
        self.model = None
        self.is_fitted = False

    def fit(self, X: pd.DataFrame) -> "AnomalyDetector":
        self.feature_names = list(X.columns)
        # Handle NaN/Inf
        X_clean = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        X_scaled = self.scaler.fit_transform(X_clean)

        if self.model_type == "LOCAL_OUTLIER_FACTOR":
            n_neighbors = min(20, max(2, len(X_clean) - 1))
            self.model = LocalOutlierFactor(
                n_neighbors=n_neighbors,
                contamination=self.contamination,
                novelty=True
            )
            self.model.fit(X_scaled)
        else:
            self.model = IsolationForest(
                n_estimators=100,
                contamination=self.contamination,
                random_state=self.random_state,
                n_jobs=-1
            )
            self.model.fit(X_scaled)

        self.is_fitted = True
        return self

    def predict_anomaly_scores(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes anomaly scores normalized to [0.0, 1.0] where 1.0 is most anomalous.
        Returns (anomaly_scores, binary_predictions: 1 for anomaly, 0 for normal).
        """
        if not self.is_fitted:
            raise ValueError("Detector is not fitted yet.")

        X_clean = X[self.feature_names].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        X_scaled = self.scaler.transform(X_clean)

        if self.model_type == "LOCAL_OUTLIER_FACTOR":
            # score_samples returns opposite of LOF (higher is more normal)
            raw_scores = -self.model.score_samples(X_scaled)
            preds_raw = self.model.predict(X_scaled)  # -1 for anomaly, 1 for normal
        else:
            # Isolation forest: score_samples returns negative anomaly score (lower is more anomalous)
            raw_scores = -self.model.score_samples(X_scaled)
            preds_raw = self.model.predict(X_scaled)

        # Normalize scores to 0.0 - 1.0 range
        min_s = float(np.min(raw_scores))
        max_s = float(np.max(raw_scores))
        if max_s > min_s:
            norm_scores = (raw_scores - min_s) / (max_s - min_s)
        else:
            norm_scores = np.zeros_like(raw_scores)

        binary_preds = np.where(preds_raw == -1, 1, 0)
        return norm_scores, binary_preds

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            "model_type": self.model_type,
            "contamination": self.contamination,
            "random_state": self.random_state,
            "feature_names": self.feature_names,
            "scaler": self.scaler,
            "model": self.model,
            "is_fitted": self.is_fitted
        }, filepath)

    @classmethod
    def load(cls, filepath: str) -> "AnomalyDetector":
        data = joblib.load(filepath)
        instance = cls(
            model_type=data["model_type"],
            contamination=data["contamination"],
            random_state=data["random_state"]
        )
        instance.feature_names = data["feature_names"]
        instance.scaler = data["scaler"]
        instance.model = data["model"]
        instance.is_fitted = data["is_fitted"]
        return instance
