import uuid
from typing import List, Dict, Any, Optional
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

def create_dataset_record(db: Session, filename: str, format_str: str, size_bytes: int) -> Dataset:
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
    return dataset

def list_datasets(db: Session, limit: int = 50, offset: int = 0) -> List[Dataset]:
    return db.query(Dataset).order_by(Dataset.uploaded_at.desc()).offset(offset).limit(limit).all()

def get_dataset_by_id(db: Session, dataset_id: str) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise EntityNotFoundError("Dataset", dataset_id)
    return dataset

def delete_dataset(db: Session, dataset_id: str) -> bool:
    dataset = get_dataset_by_id(db, dataset_id)
    # Cascade deletes transactions, alerts, etc.
    db.delete(dataset)
    db.commit()
    return True
