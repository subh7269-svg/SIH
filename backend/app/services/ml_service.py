import time
import gc
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
from backend.app.validation.contextual_validator import contextual_validator
from backend.app.validation.profiler import build_and_store_profiles_for_dataset
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
    logger.info(f"[ML_SERVICE] ▶ Starting ML pipeline: dataset={dataset_id}, model={model_type}, contamination={contamination}")

    # 1. Feature extraction
    logger.info(f"[ML_SERVICE] Step 1/6: Extracting features...")
    df_features, feature_names = extract_wallet_features_from_db(db, dataset_id=dataset_id)
    logger.info(f"[ML_SERVICE] Features extracted: {len(df_features)} entities, {len(feature_names)} features")
    if df_features.empty or len(df_features) < 3:
        logger.warning(f"[ML_SERVICE] ✗ SKIPPED — Not enough entities ({len(df_features)} < 3)")
        return {
            "status": "SKIPPED",
            "message": "Not enough wallet entities in dataset to train ML model (minimum 3 required).",
            "entity_count": len(df_features)
        }

    # Compute population baseline stats for explainability
    explainer_engine.compute_population_baselines(df_features)

    # 2. Fit Primary Model (Isolation Forest)
    logger.info(f"[ML_SERVICE] Step 2/6: Training {model_type}...")
    detector = AnomalyDetector(model_type=model_type, contamination=contamination, random_state=42)
    detector.fit(df_features)
    anomaly_scores, binary_preds = detector.predict_anomaly_scores(df_features)
    logger.info(f"[ML_SERVICE] {model_type} trained: {int(binary_preds.sum())} anomalies detected out of {len(binary_preds)}")

    # 3. Fit Baseline Model for Comparison (Local Outlier Factor)
    # LOF stores the full training set internally — skip for large datasets to save memory
    if len(df_features) <= 5000:
        logger.info(f"[ML_SERVICE] Step 3/6: Training LOF baseline for comparison...")
        baseline_detector = AnomalyDetector(model_type="LOCAL_OUTLIER_FACTOR", contamination=contamination)
        baseline_detector.fit(df_features)
        baseline_scores, baseline_preds = baseline_detector.predict_anomaly_scores(df_features)
        logger.info(f"[ML_SERVICE] LOF baseline: {int(baseline_preds.sum())} anomalies detected")
    else:
        logger.info(f"[ML_SERVICE] Step 3/6: SKIPPED LOF baseline — dataset too large ({len(df_features)} entities, threshold=5000)")
        baseline_scores = anomaly_scores.copy()
        baseline_preds = binary_preds.copy()

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
    del baseline_scores, baseline_preds, baseline_eval
    gc.collect()

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
    logger.info(f"[ML_SERVICE] Model artifact saved: id={model_obj.id}, path={artifact_path}")
    del detector
    gc.collect()

    # 4. DBSCAN Clustering
    logger.info(f"[ML_SERVICE] Step 4/6: Running DBSCAN clustering...")
    clusterer = EntityClusterer(eps=0.7, min_samples=3)
    clusters_meta = clusterer.fit_predict(df_features)
    logger.info(f"[ML_SERVICE] Clustering done: {len(clusters_meta)} clusters found")

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
    logger.info(f"[ML_SERVICE] Clusters persisted to DB")
    del clusterer
    cluster_count = len(clusters_meta)
    del clusters_meta
    gc.collect()

    # 4.5 Derive and persist historical behavioural baselines from raw dataset observations (No leakage)
    if dataset_id:
        logger.info(f"[ML_SERVICE] Step 5/6: Building behavioural profiles...")
        build_and_store_profiles_for_dataset(db, dataset_id=dataset_id)
        logger.info(f"[ML_SERVICE] Behavioural profiles stored")

    # 5. Risk Prioritization & Alert Generation
    logger.info(f"[ML_SERVICE] Step 6/6: Risk scoring & alert generation for {len(wallet_addresses) if 'wallet_addresses' in dir() else len(df_features)} entities...")
    alerts_generated = 0
    # Clean previous alerts for this dataset
    if dataset_id:
        db.query(Alert).filter(Alert.dataset_id == dataset_id).delete()
        db.commit()

    # Fetch transaction mapping for evidence summaries
    wallet_addresses = list(df_features.index)
    wallets_in_db = {}
    for i in range(0, len(wallet_addresses), 500):
        sub_addrs = wallet_addresses[i:i + 500]
        for w in db.query(Wallet).filter(Wallet.address.in_(sub_addrs)).all():
            wallets_in_db[w.address] = w

    candidates = []
    for idx, addr in enumerate(wallet_addresses):
        a_score = float(anomaly_scores[idx])
        feat_dict = df_features.loc[addr].to_dict()

        # Compute deterministic risk score
        priority_score, severity, subscores = compute_deterministic_risk_score(a_score, feat_dict)

        # Update Wallet record in DB
        if addr in wallets_in_db:
            wallets_in_db[addr].risk_score = priority_score
            wallets_in_db[addr].anomaly_score = round(a_score, 4)

        # Only consider alert if priority score indicates investigative relevance (score >= 35) or anomalous
        if priority_score >= 35 or a_score > 0.65:
            candidates.append((priority_score, a_score, addr, feat_dict, severity, subscores))

    # Sort candidates by priority score and anomaly score descending
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    # Triage top 200 highest-priority anomalous leads for deep forensic provenance
    top_candidates = candidates[:200]

    for priority_score, a_score, addr, feat_dict, severity, subscores in top_candidates:
        reasons, deviation_details = explainer_engine.explain_entity(
            addr, feat_dict, a_score, priority_score
        )

        # Build evidence provenance summary
        tx_in = [ti.txid for ti in db.query(TransactionInput.txid).filter(TransactionInput.wallet_address == addr).limit(5).all()]
        tx_out = [to.txid for to in db.query(TransactionOutput.txid).filter(TransactionOutput.wallet_address == addr).limit(5).all()]
        related_txs = list(set(tx_in + tx_out))

        ip_obs = [ipo.src_ip for ipo in db.query(IPObservation.src_ip).filter(IPObservation.txid.in_(related_txs)).limit(5).all()]

        # Contextual Validation Layer (Entity Behaviour vs Entity's Historical Baseline)
        val_res = contextual_validator.validate_entity_anomaly(
            entity_id=addr,
            current_features=feat_dict,
            raw_anomaly_score=a_score,
            db=db,
            dataset_id=dataset_id
        )

        alert_obj = Alert(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            entity_id=addr,
            entity_type="WALLET",
            anomaly_score=round(a_score, 4),  # Preserved as-is for backwards compatibility
            raw_anomaly_score=val_res["raw_anomaly_score"],  # Preserved raw Isolation Forest score
            validation_score=val_res["validation_score"],  # Contextual validation score
            priority_score=priority_score,
            severity=severity,
            confidence=val_res["confidence"],  # Contextual confidence
            status="NEW",
            reasons=reasons,
            explanation_details=deviation_details,
            behavioural_deviation=val_res.get("behavioural_deviation"),
            supporting_evidence=val_res["supporting_evidence"],
            counter_evidence=val_res["counter_evidence"],
            historical_context=val_res["historical_context"],
            validation_explanation=val_res["validation_explanation"],
            evidence_summary={
                "related_transactions": related_txs,
                "observed_ips": list(set(ip_obs)),
                "subscores": subscores,
                "metrics": feat_dict,
                "contextual_validation": val_res
            }
        )
        db.add(alert_obj)
        alerts_generated += 1

        # Periodic commit to release ORM session memory on large datasets
        if alerts_generated % 50 == 0:
            db.commit()

    db.commit()
    logger.info(f"[ML_SERVICE] ✓ ML Pipeline COMPLETED: {len(df_features)} entities evaluated, {alerts_generated} alerts generated, {cluster_count} clusters")

    return {
        "status": "COMPLETED",
        "model_id": model_obj.id,
        "model_type": model_type,
        "entity_count": len(df_features),
        "cluster_count": cluster_count,
        "alerts_generated": alerts_generated,
        "evaluation_metrics": eval_metrics
    }
