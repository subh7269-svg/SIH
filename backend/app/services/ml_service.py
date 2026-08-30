import time
import uuid
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.ml import MLModelArtifact, EntityCluster
from backend.app.models.entity import Wallet
from backend.app.models.alert import Alert
from backend.app.models.transaction import TransactionInput, TransactionOutput, IPObservation
from backend.app.ml.features import extract_wallet_features_from_db
from backend.app.ml.detector import AnomalyDetector
from backend.app.ml.clustering import EntityClusterer
from backend.app.ml.evaluation import evaluate_detector
from backend.app.risk.scorer import compute_deterministic_risk_score
from backend.app.explainability.explainer import explainer_engine
from backend.app.core.logging import logger

def train_and_evaluate_pipeline(
    db: Session,
    dataset_id: Optional[str] = None,
    model_type: str = "ISOLATION_FOREST",
    contamination: float = 0.05,
    benchmark_labels: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Complete ML execution:
    1. Feature Engineering (20+ features)
    2. ML Training (Isolation Forest + LOF comparison)
    3. DBSCAN Entity Clustering
    4. Deterministic Risk Prioritization (0-100)
    5. Population Baseline Explainability
    6. Ranked Alert Generation
    """
    start_time = time.time()

    # 1. Feature extraction
    df_features, feature_names = extract_wallet_features_from_db(db, dataset_id=dataset_id)
    if df_features.empty or len(df_features) < 3:
        return {
            "status": "SKIPPED",
            "message": "Not enough wallet entities in dataset to train ML model (minimum 3 required).",
            "entity_count": len(df_features)
        }

    # Compute population baseline stats for explainability
    explainer_engine.compute_population_baselines(df_features)

    # 2. Fit Primary Model (Isolation Forest)
    detector = AnomalyDetector(model_type=model_type, contamination=contamination, random_state=42)
    detector.fit(df_features)
    anomaly_scores, binary_preds = detector.predict_anomaly_scores(df_features)

    # 3. Fit Baseline Model for Comparison (Local Outlier Factor)
    baseline_detector = AnomalyDetector(model_type="LOCAL_OUTLIER_FACTOR", contamination=contamination)
    baseline_detector.fit(df_features)
    baseline_scores, baseline_preds = baseline_detector.predict_anomaly_scores(df_features)

    train_duration_ms = int((time.time() - start_time) * 1000)

    # Save model artifact to disk
    artifact_filename = f"detector_{model_type.lower()}_{uuid.uuid4().hex[:8]}.joblib"
    artifact_path = str(settings.ML_ARTIFACT_DIR / artifact_filename)
    detector.save(artifact_path)

    # Evaluate models against synthetic benchmark ground truth if available
    y_true = np.zeros(len(df_features), dtype=int)
    if benchmark_labels:
        for idx, addr in enumerate(df_features.index):
            y_true[idx] = benchmark_labels.get(addr, 0)
    else:
        # If no explicit labels supplied, evaluate against detector predictions as self-test
        y_true = binary_preds

    eval_metrics = evaluate_detector(y_true, binary_preds, anomaly_scores, train_duration_ms)
    baseline_eval = evaluate_detector(y_true, baseline_preds, baseline_scores, train_duration_ms)
    eval_metrics["baseline_comparison"] = {
        "model": "LOCAL_OUTLIER_FACTOR",
        "precision": baseline_eval["precision"],
        "recall": baseline_eval["recall"],
        "f1_score": baseline_eval["f1_score"],
        "roc_auc": baseline_eval["roc_auc"],
        "pr_auc": baseline_eval["pr_auc"]
    }

    # Persist ML Model Artifact record in DB
    model_obj = MLModelArtifact(
        id=str(uuid.uuid4()),
        model_name=f"TraceX {model_type.replace('_', ' ').title()} Detector",
        model_type=model_type,
        version="1.0.0",
        is_active=1,
        hyperparameters={"contamination": contamination, "n_estimators": 100, "random_state": 42},
        feature_names=feature_names,
        evaluation_metrics=eval_metrics,
        training_duration_ms=train_duration_ms,
        dataset_records_count=len(df_features),
        artifact_path=artifact_path,
        trained_at=datetime.now(timezone.utc)
    )
    db.add(model_obj)
    db.commit()

    # 4. DBSCAN Clustering
    clusterer = EntityClusterer(eps=0.7, min_samples=3)
    clusters_meta = clusterer.fit_predict(df_features)

    # Clean old clusters for this dataset and insert new
    if dataset_id:
        db.query(EntityCluster).filter(EntityCluster.dataset_id == dataset_id).delete()
    for c in clusters_meta:
        c_obj = EntityCluster(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            cluster_label=c["cluster_label"],
            cluster_name=c["cluster_name"],
            algorithm="DBSCAN",
            entity_type="WALLET",
            member_count=c["member_count"],
            member_ids=c["member_ids"],
            characteristics=c["characteristics"]
        )
        db.add(c_obj)
    db.commit()

    # 5. Risk Prioritization & Alert Generation
    alerts_generated = 0
    # Clean previous alerts for this dataset
    if dataset_id:
        db.query(Alert).filter(Alert.dataset_id == dataset_id).delete()
        db.commit()

    # Fetch transaction mapping for evidence summaries
    wallet_addresses = list(df_features.index)
    wallets_in_db = {w.address: w for w in db.query(Wallet).filter(Wallet.address.in_(wallet_addresses)).all()}

    for idx, addr in enumerate(wallet_addresses):
        a_score = float(anomaly_scores[idx])
        feat_dict = df_features.loc[addr].to_dict()

        # Compute deterministic risk score
        priority_score, severity, subscores = compute_deterministic_risk_score(a_score, feat_dict)

        # Update Wallet record in DB
        if addr in wallets_in_db:
            wallets_in_db[addr].risk_score = priority_score
            wallets_in_db[addr].anomaly_score = round(a_score, 4)

        # Only create alert if priority score indicates investigative relevance (score >= 35) or anomalous
        if priority_score >= 35 or a_score > 0.65:
            reasons, deviation_details = explainer_engine.explain_entity(
                addr, feat_dict, a_score, priority_score
            )

            # Build evidence provenance summary
            tx_in = [ti.txid for ti in db.query(TransactionInput.txid).filter(TransactionInput.wallet_address == addr).limit(5).all()]
            tx_out = [to.txid for to in db.query(TransactionOutput.txid).filter(TransactionOutput.wallet_address == addr).limit(5).all()]
            related_txs = list(set(tx_in + tx_out))

            ip_obs = [ipo.src_ip for ipo in db.query(IPObservation.src_ip).filter(IPObservation.txid.in_(related_txs)).limit(5).all()]

            alert_obj = Alert(
                id=str(uuid.uuid4()),
                dataset_id=dataset_id,
                entity_id=addr,
                entity_type="WALLET",
                anomaly_score=round(a_score, 4),
                priority_score=priority_score,
                severity=severity,
                confidence=round(0.80 + (a_score * 0.15), 2),
                status="NEW",
                reasons=reasons,
                explanation_details=deviation_details,
                evidence_summary={
                    "related_transactions": related_txs,
                    "observed_ips": list(set(ip_obs)),
                    "subscores": subscores,
                    "metrics": feat_dict
                }
            )
            db.add(alert_obj)
            alerts_generated += 1

    db.commit()
    logger.info(f"ML Pipeline completed: {len(df_features)} entities evaluated, {alerts_generated} alerts created.")

    return {
        "status": "COMPLETED",
        "model_id": model_obj.id,
        "model_type": model_type,
        "entity_count": len(df_features),
        "cluster_count": len(clusters_meta),
        "alerts_generated": alerts_generated,
        "evaluation_metrics": eval_metrics
    }
