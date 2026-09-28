import os
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import uuid

from backend.app.db.session import get_db, SessionLocal
from backend.app.schemas.dataset import DatasetResponse, DatasetListResponse, BatchDatasetResponse, BatchDatasetItemError
from backend.app.services.dataset_service import create_dataset_record, list_datasets, get_dataset_by_id, delete_dataset
from backend.app.ingestion.pipeline import process_dataset_stream
from backend.app.services.ml_service import train_and_evaluate_pipeline
from backend.app.services.graph_service import invalidate_graph_cache
from backend.app.services.audit_service import log_audit_event
from backend.app.core.logging import logger
from backend.app.models.dataset import Dataset

router = APIRouter(prefix="/datasets", tags=["Datasets"])

# Thread pool for heavy processing — prevents blocking the asyncio event loop
_processing_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dataset-worker")


def _run_ingestion_and_ml(
    dataset_id: str,
    tmp_path: str,
    file_format: str,
    filename: str,
    file_size: int,
    run_ml: bool
):
    """
    Runs the heavy ingestion + ML pipeline in a background thread with its OWN
    DB session.  This is the critical fix: previously this ran directly on the
    asyncio event loop, blocking every other HTTP request until it finished.
    """
    db = SessionLocal()
    logger.info(f"[BG_WORKER] ▶ Background processing started: dataset={dataset_id}, file={filename}")
    try:
        # ── 1. Ingestion ─────────────────────────────────────────────
        logger.info(f"[BG_WORKER] Starting ingestion pipeline for dataset={dataset_id}")
        dq_metrics = process_dataset_stream(
            db=db,
            dataset_id=dataset_id,
            file_path=tmp_path,
            file_format=file_format
        )
        logger.info(
            f"[BG_WORKER] ✓ Ingestion complete for dataset={dataset_id}: "
            f"valid={dq_metrics.get('valid_records', 0)}"
        )

        invalidate_graph_cache(dataset_id)

        # ── 2. ML Pipeline ───────────────────────────────────────────
        if run_ml:
            try:
                logger.info(f"[BG_WORKER] Starting ML pipeline for dataset={dataset_id}")
                train_and_evaluate_pipeline(db=db, dataset_id=dataset_id)
                logger.info(f"[BG_WORKER] ✓ ML pipeline complete for dataset={dataset_id}")
            except Exception as e:
                logger.error(
                    f"[BG_WORKER] ✗ ML pipeline failed for dataset={dataset_id}: {e}",
                    exc_info=True
                )

        # ── 3. Audit log ─────────────────────────────────────────────
        try:
            log_audit_event(
                db=db,
                action="DATASET_UPLOAD_AND_PROCESS",
                target_type="DATASET",
                target_id=dataset_id,
                details={
                    "filename": filename,
                    "format": file_format,
                    "size": file_size,
                    "valid_records": dq_metrics.get("valid_records", 0),
                }
            )
        except Exception as e:
            logger.error(f"[BG_WORKER] ✗ Audit log failed: {e}", exc_info=True)

        logger.info(f"[BG_WORKER] ✓ Background processing DONE for dataset={dataset_id}")

    except Exception as e:
        logger.error(
            f"[BG_WORKER] ✗ FATAL — Ingestion failed for dataset={dataset_id}: {e}",
            exc_info=True
        )
        try:
            db.rollback()
            ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if ds and ds.status != "FAILED":
                ds.status = "FAILED"
                ds.error_summary = f"Ingestion failed: {str(e)}"
                db.commit()
                logger.info(f"[BG_WORKER] Dataset {dataset_id} marked as FAILED")
        except Exception as inner:
            logger.error(f"[BG_WORKER] ✗ Could not mark dataset as FAILED: {inner}", exc_info=True)
    finally:
        db.close()
        # Clean up the temp file
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                logger.debug(f"[BG_WORKER] Temp file deleted: {tmp_path}")
            except Exception as e:
                logger.warning(f"[BG_WORKER] Could not delete temp file {tmp_path}: {e}")


@router.post("", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    run_ml: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Upload and ingest a dataset.

    The endpoint streams the file to disk, creates a PENDING dataset record,
    and IMMEDIATELY returns it to the caller.  The heavy ingestion + ML work
    runs in a background thread so the server stays responsive.
    """
    filename = file.filename or "uploaded_dataset.csv"
    ext = filename.split(".")[-1].lower() if "." in filename else "csv"
    if ext not in ("csv", "json", "xml"):
        ext = "csv"

    logger.info(f"[DATASETS_API] POST /datasets — Upload started: filename={filename}, format={ext}, run_ml={run_ml}")

    # Stream file to disk in 1 MB chunks to avoid memory exhaustion
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
    tmp_path = tmp.name
    try:
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
        tmp.close()

        file_size = os.path.getsize(tmp_path)
        if file_size == 0:
            logger.warning(f"[DATASETS_API] ✗ Upload rejected: file is empty — {filename}")
            os.unlink(tmp_path)
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        logger.info(f"[DATASETS_API] File saved to temp: {tmp_path} ({file_size} bytes)")

        # 1. Create dataset record — quick DB insert
        dataset = create_dataset_record(
            db=db,
            filename=filename,
            format_str=ext,
            size_bytes=file_size
        )

        # 2. Kick off heavy work in background thread (does NOT block event loop)
        loop = asyncio.get_running_loop()
        loop.run_in_executor(
            _processing_pool,
            _run_ingestion_and_ml,
            dataset.id,
            tmp_path,
            ext,
            filename,
            file_size,
            run_ml
        )

        # 3. Return immediately — frontend polls for status via GET /datasets
        logger.info(
            f"[DATASETS_API] ✓ Dataset record created, background processing dispatched — "
            f"id={dataset.id}, status={dataset.status}"
        )
        return DatasetResponse.model_validate(dataset)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DATASETS_API] ✗ Upload failed: {e}", exc_info=True)
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Dataset upload failed: {str(e)}")


@router.post("/batch", response_model=BatchDatasetResponse)
async def upload_datasets_batch(
    files: List[UploadFile] = File(...),
    run_ml: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Ingests multiple files independently in one batch operation.
    Each file is saved to disk and dispatched for background processing.
    The response returns immediately with PENDING dataset records.
    """
    logger.info(f"[DATASETS_API] POST /datasets/batch — Batch upload started: {len(files)} files, run_ml={run_ml}")
    results: List[DatasetResponse] = []
    errors: List[BatchDatasetItemError] = []
    loop = asyncio.get_running_loop()

    for file_idx, file in enumerate(files):
        filename = file.filename or "uploaded_dataset.csv"
        ext = filename.split(".")[-1].lower() if "." in filename else "csv"
        if ext not in ("csv", "json", "xml"):
            ext = "csv"

        logger.info(f"[DATASETS_API] Batch [{file_idx+1}/{len(files)}] Saving: {filename}")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
        tmp_path = tmp.name
        try:
            while chunk := await file.read(1024 * 1024):
                tmp.write(chunk)
            tmp.close()

            file_size = os.path.getsize(tmp_path)
            if file_size == 0:
                logger.warning(f"[DATASETS_API] Batch [{file_idx+1}] ✗ Skipped empty file: {filename}")
                errors.append(BatchDatasetItemError(filename=filename, error="Uploaded file is empty."))
                os.unlink(tmp_path)
                continue

            dataset = create_dataset_record(
                db=db,
                filename=filename,
                format_str=ext,
                size_bytes=file_size
            )

            # Dispatch to background thread
            loop.run_in_executor(
                _processing_pool,
                _run_ingestion_and_ml,
                dataset.id,
                tmp_path,
                ext,
                filename,
                file_size,
                run_ml
            )

            results.append(DatasetResponse.model_validate(dataset))
            logger.info(f"[DATASETS_API] Batch [{file_idx+1}] ✓ Dispatched: {filename} → id={dataset.id}")

        except Exception as e:
            logger.error(f"[DATASETS_API] Batch [{file_idx+1}] ✗ Failed to save {filename}: {e}", exc_info=True)
            errors.append(BatchDatasetItemError(filename=filename, error=str(e)))
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    logger.info(f"[DATASETS_API] ✓ Batch dispatched: {len(results)} queued, {len(errors)} failed upfront")

    return BatchDatasetResponse(
        total_files=len(files),
        successful_count=len(results),
        failed_count=len(errors),
        datasets=results,
        errors=errors
    )


@router.get("", response_model=DatasetListResponse)
def get_datasets(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    logger.debug(f"[DATASETS_API] GET /datasets — limit={limit}, offset={offset}")
    items = list_datasets(db=db, limit=limit, offset=offset)
    total = len(items)
    logger.debug(f"[DATASETS_API] ✓ Returning {total} datasets")
    return DatasetListResponse(
        total=total,
        datasets=[DatasetResponse.model_validate(d) for d in items]
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    logger.debug(f"[DATASETS_API] GET /datasets/{dataset_id}")
    dataset = get_dataset_by_id(db=db, dataset_id=dataset_id)
    return DatasetResponse.model_validate(dataset)


@router.post("/{dataset_id}/process", response_model=DatasetResponse)
def reprocess_dataset(dataset_id: str, db: Session = Depends(get_db)):
    logger.info(f"[DATASETS_API] POST /datasets/{dataset_id}/process — Reprocessing")
    train_and_evaluate_pipeline(db=db, dataset_id=dataset_id)
    invalidate_graph_cache(dataset_id)
    dataset = get_dataset_by_id(db=db, dataset_id=dataset_id)
    logger.info(f"[DATASETS_API] ✓ Reprocessed dataset={dataset_id}, status={dataset.status}")
    return DatasetResponse.model_validate(dataset)


@router.delete("/{dataset_id}")
def remove_dataset(dataset_id: str, db: Session = Depends(get_db)):
    logger.info(f"[DATASETS_API] DELETE /datasets/{dataset_id}")
    delete_dataset(db=db, dataset_id=dataset_id)
    invalidate_graph_cache(dataset_id)
    logger.info(f"[DATASETS_API] ✓ Deleted dataset={dataset_id}")
    return {"status": "DELETED", "dataset_id": dataset_id}
