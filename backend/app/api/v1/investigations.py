import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.db.session import get_db
from backend.app.models.investigation import InvestigationCase
from backend.app.models.audit import AuditLog
from backend.app.schemas.investigation import CaseCreateRequest, CaseResponse
from backend.app.services.audit_service import log_audit_event

router = APIRouter(prefix="/investigations", tags=["Investigations & Cases"])

@router.post("/cases", response_model=CaseResponse)
def create_case(req: CaseCreateRequest, db: Session = Depends(get_db)):
    case_num = f"CASE-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:4].upper()}"
    case_obj = InvestigationCase(
        id=str(uuid.uuid4()),
        case_number=case_num,
        title=req.title,
        description=req.description,
        lead_investigator=req.lead_investigator,
        priority=req.priority,
        status="OPEN",
        pinned_entities=req.pinned_entities,
        pinned_alerts=req.pinned_alerts
    )
    db.add(case_obj)
    db.commit()
    db.refresh(case_obj)

    log_audit_event(
        db=db,
        action="CASE_CREATED",
        target_type="CASE",
        target_id=case_obj.id,
        details={"case_number": case_num, "title": req.title}
    )

    return CaseResponse.model_validate(case_obj)

@router.get("/cases", response_model=List[CaseResponse])
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(InvestigationCase).order_by(InvestigationCase.created_at.desc()).all()
    return [CaseResponse.model_validate(c) for c in cases]

@router.get("/audit-logs")
def get_audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [{
        "id": l.id,
        "user_name": l.user_name,
        "action": l.action,
        "target_type": l.target_type,
        "target_id": l.target_id,
        "details": l.details,
        "timestamp": l.timestamp.isoformat()
    } for l in logs]
