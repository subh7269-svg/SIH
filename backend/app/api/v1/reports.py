from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.schemas.report import ReportGenerateRequest, ReportResponse
from backend.app.services.report_service import generate_investigation_report

router = APIRouter(prefix="/reports", tags=["Forensic Reports"])

@router.post("/generate", response_model=ReportResponse)
def create_report(req: ReportGenerateRequest, db: Session = Depends(get_db)):
    return generate_investigation_report(db=db, request=req, user_name="investigator")
