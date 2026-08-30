from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.db.session import get_db
from backend.app.schemas.ml import MLTrainRequest, MLModelSummary
from backend.app.models.ml import MLModelArtifact
from backend.app.services.ml_service import train_and_evaluate_pipeline
from backend.app.services.audit_service import log_audit_event

router = APIRouter(prefix="/models", tags=["Machine Learning"])

@router.post("/train")
def train_model(req: MLTrainRequest, db: Session = Depends(get_db)):
    result = train_and_evaluate_pipeline(
        db=db,
        dataset_id=req.dataset_id,
        model_type=req.model_type,
        contamination=req.contamination
    )

    log_audit_event(
        db=db,
        action="ML_MODEL_TRAIN",
        target_type="MODEL",
        target_id=result.get("model_id"),
        details={"model_type": req.model_type, "contamination": req.contamination}
    )

    return result

@router.get("", response_model=List[MLModelSummary])
def get_models(limit: int = 20, db: Session = Depends(get_db)):
    models = db.query(MLModelArtifact).order_by(MLModelArtifact.trained_at.desc()).limit(limit).all()
    return [MLModelSummary.model_validate(m) for m in models]

@router.get("/{model_id}", response_model=MLModelSummary)
def get_model(model_id: str, db: Session = Depends(get_db)):
    m = db.query(MLModelArtifact).filter(MLModelArtifact.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model artifact not found.")
    return MLModelSummary.model_validate(m)
