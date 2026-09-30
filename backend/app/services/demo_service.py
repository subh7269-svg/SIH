import os
from typing import Dict, Any
from sqlalchemy.orm import Session

from backend.app.models.dataset import Dataset
from backend.app.models.transaction import Transaction, TransactionInput, TransactionOutput, IPObservation
from backend.app.models.entity import Wallet
from backend.app.models.alert import Alert
from backend.app.models.feature import EntityFeature
from backend.app.models.ml import MLModelArtifact, EntityCluster
from backend.app.models.audit import AuditLog
from backend.app.services.dataset_service import create_dataset_record
from backend.app.ingestion.pipeline import process_dataset_stream
from backend.app.services.ml_service import train_and_evaluate_pipeline
from backend.app.services.graph_service import get_or_build_graph, invalidate_graph_cache
from backend.app.services.audit_service import log_audit_event
from scripts.generate_synthetic_data import generate_synthetic_dataset

def reset_all_data(db: Session):
    """Resets all database tables for a clean slate demo."""
    db.query(Alert).delete()
    db.query(EntityCluster).delete()
    db.query(MLModelArtifact).delete()
    db.query(EntityFeature).delete()
    db.query(IPObservation).delete()
    db.query(TransactionInput).delete()
    db.query(TransactionOutput).delete()
    db.query(Transaction).delete()
    db.query(Wallet).delete()
    db.query(Dataset).delete()
    db.commit()
    invalidate_graph_cache()

def run_one_click_demo(db: Session, seed: int = 42) -> Dict[str, Any]:
    """
    Executes a deterministic end-to-end SIH demonstration workflow:
    1. Resets database
    2. Generates synthetic dataset (normal traffic + 3 controlled anomalous scenarios)
    3. Ingests and normalizes transactions & IP observations
    4. Generates Data Quality report
    5. Builds heterogeneous entity graph
    6. Extracts 20+ behavioral features
    7. Runs Isolation Forest anomaly detection vs LOF baseline
    8. Runs DBSCAN behavioral clustering
    9. Generates explainable prioritized alerts
    """
    reset_all_data(db)

    # 1. Generate synthetic benchmark package
    pkg = generate_synthetic_dataset(num_normal_txs=75, seed=seed)
    records = pkg["records"]
    labels = pkg["benchmark_labels"]

    # 2. Format as CSV payload
    import csv
    import io
    output = io.StringIO()
    fieldnames = [
        "txid", "timestamp", "fee", "script_type",
        "input_addresses", "input_amounts", "output_addresses", "output_amounts",
        "src_ip", "dst_ip", "src_port", "dst_port", "geo_country", "asn"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in records:
        row = dict(r)
        row["input_addresses"] = ";".join(row["input_addresses"])
        row["output_addresses"] = ";".join(row["output_addresses"])
        row["input_amounts"] = ";".join(map(str, row["input_amounts"]))
        row["output_amounts"] = ";".join(map(str, row["output_amounts"]))
        writer.writerow(row)
    csv_bytes = output.getvalue().encode("utf-8")

    # 3. Create and Process Dataset
    dataset = create_dataset_record(
        db=db,
        filename="sih_benchmark_demo_dataset.csv",
        format_str="csv",
        size_bytes=len(csv_bytes)
    )

    dq_metrics = process_dataset_stream(
        db=db,
        dataset_id=dataset.id,
        file_bytes=csv_bytes,
        file_format="csv"
    )

    # 4. Build in-memory NetworkX Graph
    G = get_or_build_graph(db, dataset_id=dataset.id, force_rebuild=True)

    # 5. Train ML Models, Cluster, Explain & Generate Alerts
    ml_result = train_and_evaluate_pipeline(
        db=db,
        dataset_id=dataset.id,
        model_type="ISOLATION_FOREST",
        contamination=0.08,
        benchmark_labels=labels
    )

    log_audit_event(
        db=db,
        action="DEMO_ONE_CLICK_RUN",
        target_type="DEMO",
        target_id=dataset.id,
        details={"records": len(records), "alerts": ml_result.get("alerts_generated", 0)},
        user_name="investigator_demo"
    )

    return {
        "status": "SUCCESS",
        "message": "LeadForge 1-Click Demo Pipeline executed successfully.",
        "dataset_id": dataset.id,
        "dq_metrics": dq_metrics,
        "graph_stats": {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges()
        },
        "ml_result": ml_result
    }
