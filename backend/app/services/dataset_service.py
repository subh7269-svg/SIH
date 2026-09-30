import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.app.models.dataset import Dataset
from backend.app.models.transaction import Transaction, TransactionInput, TransactionOutput, IPObservation
from backend.app.models.entity import Wallet
from backend.app.models.alert import Alert
from backend.app.models.feature import EntityFeature
from backend.app.models.ml import EntityCluster
from backend.app.ingestion.pipeline import process_dataset_stream
from backend.app.services.ml_service import train_and_evaluate_pipeline
from backend.app.core.errors import EntityNotFoundError
from backend.app.core.logging import logger

def create_dataset_record(db: Session, filename: str, format_str: str, size_bytes: int) -> Dataset:
    logger.info(f"[DATASET_SERVICE] Creating dataset record: filename={filename}, format={format_str}, size={size_bytes}")
    dataset = Dataset(
        id=str(uuid.uuid4()),
        filename=filename,
        format=format_str.lower(),
        size_bytes=size_bytes,
        status="PENDING"
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    logger.info(f"[DATASET_SERVICE] ✓ Dataset record created: id={dataset.id}, status={dataset.status}")
    return dataset

def list_datasets(db: Session, limit: int = 50, offset: int = 0) -> List[Dataset]:
    # CRITICAL FIX: Expire all cached objects so SQLAlchemy re-reads from DB.
    # Without this, the session's identity map can serve stale Dataset objects
    # that were loaded in a prior request on the same pooled connection.
    db.expire_all()
    logger.debug(f"[DATASET_SERVICE] Listing datasets: limit={limit}, offset={offset} (session expired for fresh read)")
    datasets = db.query(Dataset).order_by(Dataset.uploaded_at.desc()).offset(offset).limit(limit).all()
    statuses = {}
    for d in datasets:
        statuses[d.status] = statuses.get(d.status, 0) + 1
    logger.info(f"[DATASET_SERVICE] ✓ Listed {len(datasets)} datasets. Status breakdown: {statuses}")
    return datasets

def get_dataset_by_id(db: Session, dataset_id: str) -> Dataset:
    logger.debug(f"[DATASET_SERVICE] Fetching dataset by id: {dataset_id}")
    # Expire to get fresh state
    db.expire_all()
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        logger.warning(f"[DATASET_SERVICE] ✗ Dataset not found: {dataset_id}")
        raise EntityNotFoundError("Dataset", dataset_id)
    logger.debug(f"[DATASET_SERVICE] ✓ Found dataset: id={dataset.id}, status={dataset.status}")
    return dataset

def delete_dataset(db: Session, dataset_id: str) -> bool:
    """
    High-performance direct SQL dataset deletion.
    Avoids loading hundreds of thousands of ORM objects into Python memory
    which freezes the server and locks SQLite.
    Cleanly purges all related inputs, outputs, observations, alerts, profiles,
    features, clusters, and orphaned entities in a single atomic transaction.
    """
    logger.info(f"[DATASET_SERVICE] Deleting dataset: {dataset_id}")
    db.expire_all()
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        logger.warning(f"[DATASET_SERVICE] Dataset {dataset_id} not found in DB")
        raise EntityNotFoundError("Dataset", dataset_id)

    try:
        # 1. Inputs and Outputs of transactions in this dataset
        db.execute(
            text("DELETE FROM transaction_inputs WHERE transaction_id IN (SELECT id FROM transactions WHERE dataset_id = :id)"),
            {"id": dataset_id}
        )
        db.execute(
            text("DELETE FROM transaction_outputs WHERE transaction_id IN (SELECT id FROM transactions WHERE dataset_id = :id)"),
            {"id": dataset_id}
        )

        # 2. IP Observations
        db.execute(
            text("DELETE FROM ip_observations WHERE dataset_id = :id"),
            {"id": dataset_id}
        )

        # 3. Transactions
        db.execute(
            text("DELETE FROM transactions WHERE dataset_id = :id"),
            {"id": dataset_id}
        )

        # 4. Alerts
        db.execute(
            text("DELETE FROM alerts WHERE dataset_id = :id"),
            {"id": dataset_id}
        )

        # 5. Entity Behaviour Profiles
        db.execute(
            text("DELETE FROM entity_behaviour_profiles WHERE dataset_id = :id"),
            {"id": dataset_id}
        )

        # 6. Entity Features
        db.execute(
            text("DELETE FROM entity_features WHERE dataset_id = :id"),
            {"id": dataset_id}
        )

        # 7. Entity Clusters
        db.execute(
            text("DELETE FROM entity_clusters WHERE dataset_id = :id"),
            {"id": dataset_id}
        )

        # 8. Dataset Record itself
        db.execute(
            text("DELETE FROM datasets WHERE id = :id"),
            {"id": dataset_id}
        )

        # 9. Clean up orphaned wallets (not referenced in any remaining transaction inputs/outputs)
        db.execute(text("""
            DELETE FROM wallets 
            WHERE address NOT IN (
                SELECT wallet_address FROM transaction_inputs 
                UNION 
                SELECT wallet_address FROM transaction_outputs
            )
        """))

        # 10. If zero datasets remain, clean up models and any stale caches
        remaining_count = db.execute(text("SELECT COUNT(*) FROM datasets")).scalar()
        if remaining_count == 0:
            db.execute(text("DELETE FROM ml_models"))
            db.execute(text("DELETE FROM entity_features"))
            db.execute(text("DELETE FROM entity_clusters"))
            db.execute(text("DELETE FROM entity_behaviour_profiles"))
            db.execute(text("DELETE FROM wallets"))

        db.commit()
        logger.info(f"[DATASET_SERVICE] ✓ Successfully purged dataset and all related records: {dataset_id}")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"[DATASET_SERVICE] ✗ Error deleting dataset {dataset_id}: {e}", exc_info=True)
        raise
