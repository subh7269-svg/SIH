import pytest
import numpy as np
import pandas as pd
from backend.app.ml.detector import AnomalyDetector
from backend.app.ml.clustering import EntityClusterer
from backend.app.ml.evaluation import evaluate_detector
from backend.app.risk.scorer import compute_deterministic_risk_score
from backend.app.explainability.explainer import ExplainabilityEngine

def test_isolation_forest_and_lof():
    # Synthetic normal data + 2 outliers
    np.random.seed(42)
    normal = np.random.normal(loc=1.0, scale=0.2, size=(30, 5))
    outliers = np.random.normal(loc=8.0, scale=0.5, size=(3, 5))
    data = np.vstack([normal, outliers])

    cols = ["f1", "f2", "f3", "f4", "f5"]
    df = pd.DataFrame(data, columns=cols, index=[f"W_{i}" for i in range(33)])

    # Isolation forest
    if_detector = AnomalyDetector(model_type="ISOLATION_FOREST", contamination=0.1)
    if_detector.fit(df)
    scores, preds = if_detector.predict_anomaly_scores(df)

    assert len(scores) == 33
    assert len(preds) == 33
    assert all(0.0 <= s <= 1.0 for s in scores)
    # Outliers should have higher anomaly scores
    assert scores[30] > scores[0]

    # LOF baseline
    lof_detector = AnomalyDetector(model_type="LOCAL_OUTLIER_FACTOR", contamination=0.1)
    lof_detector.fit(df)
    lof_scores, lof_preds = lof_detector.predict_anomaly_scores(df)
    assert len(lof_scores) == 33

def test_dbscan_clustering():
    df = pd.DataFrame({
        "tx_velocity_per_hour": [1.0, 1.2, 1.1, 15.0, 14.8, 15.2],
        "unique_counterparties": [2, 2, 3, 20, 22, 21],
        "unique_observed_ips": [1, 1, 1, 6, 7, 6]
    }, index=[f"W_{i}" for i in range(6)])

    clusterer = EntityClusterer(eps=0.5, min_samples=2)
    clusters = clusterer.fit_predict(df)
    assert len(clusters) >= 2

def test_deterministic_risk_scoring():
    features = {
        "tx_velocity_per_hour": 12.0,
        "unique_counterparties": 25,
        "unique_observed_ips": 4,
        "unique_asns": 3,
        "unique_countries": 3,
        "graph_degree": 30
    }
    score, severity, subscores = compute_deterministic_risk_score(anomaly_score=0.9, features=features)
    assert score >= 70
    assert severity in ("HIGH", "CRITICAL")
    assert "ml_score" in subscores
    assert "velocity_score" in subscores

def test_explainability_engine():
    engine = ExplainabilityEngine()
    df = pd.DataFrame({
        "tx_velocity_per_hour": [1.0, 1.2, 1.1, 1.0, 12.5],
        "unique_counterparties": [2, 2, 3, 2, 25],
        "unique_observed_ips": [1, 1, 1, 1, 8]
    }, index=["W1", "W2", "W3", "W4", "W_ANOMALOUS"])

    engine.compute_population_baselines(df)
    reasons, details = engine.explain_entity(
        "W_ANOMALOUS",
        df.loc["W_ANOMALOUS"].to_dict(),
        anomaly_score=0.95,
        priority_score=88
    )

    assert len(reasons) > 0
    assert any("velocity" in r.lower() or "counterparties" in r.lower() for r in reasons)
    assert "tx_velocity_per_hour" in details
