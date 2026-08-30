from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from backend.app.db.session import get_db
from backend.app.schemas.dataset import DatasetResponse, DatasetListResponse
from backend.app.services.dataset_service import create_dataset_record, list_datasets, get_dataset_by_id, delete_dataset
from backend.app.ingestion.pipeline import process_dataset_stream
from backend.app.services.ml_service import train_and_evaluate_pipeline
from backend.app.services.graph_service import invalidate_graph_cache
from backend.app.services.audit_service import log_audit_event

router = APIRouter(prefix="/datasets", tags=["Datasets"])

@router.post("", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    run_ml: bool = Form(True),
    db: Session = Depends(get_db)
):
    filename = file.filename or "uploaded_dataset.csv"
    ext = filename.split(".")[-1].lower() if "." in filename else "csv"
    if ext not in ("csv", "json", "xml"):
        ext = "csv"

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 1. Create dataset record
    dataset = create_dataset_record(
        db=db,
        filename=filename,
        format_str=ext,
        size_bytes=len(content)
    )

    # 2. Process dataset stream synchronously or return
    dq_metrics = process_dataset_stream(
        db=db,
        dataset_id=dataset.id,
        file_bytes=content,
        file_format=ext
    )

    invalidate_graph_cache(dataset.id)

    # 3. Trigger ML pipeline if requested
    if run_ml:
        try:
            train_and_evaluate_pipeline(db=db, dataset_id=dataset.id)
        except Exception:
            pass

    log_audit_event(
        db=db,
        action="DATASET_UPLOAD_AND_PROCESS",
        target_type="DATASET",
        target_id=dataset.id,
        details={"filename": filename, "format": ext, "size": len(content), "valid_records": dq_metrics["valid_records"]}
    )

    db.refresh(dataset)
    return DatasetResponse.model_validate(dataset)

@router.get("", response_model=DatasetListResponse)
def get_datasets(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    items = list_datasets(db=db, limit=limit, offset=offset)
    total = len(items)
    return DatasetListResponse(
        total=total,
        datasets=[DatasetResponse.model_validate(d) for d in items]
    )

@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset = get_dataset_by_id(db=db, dataset_id=dataset_id)
    return DatasetResponse.model_validate(dataset)

@router.post("/{dataset_id}/process", response_model=DatasetResponse)
def reprocess_dataset(dataset_id: str, db: Session = Depends(get_db)):
    train_and_evaluate_pipeline(db=db, dataset_id=dataset_id)
    invalidate_graph_cache(dataset_id)
    dataset = get_dataset_by_id(db=db, dataset_id=dataset_id)
    return DatasetResponse.model_validate(dataset)

@router.delete("/{dataset_id}")
def remove_dataset(dataset_id: str, db: Session = Depends(get_db)):
    delete_dataset(db=db, dataset_id=dataset_id)
    invalidate_graph_cache(dataset_id)
    return {"status": "DELETED", "dataset_id": dataset_id}
