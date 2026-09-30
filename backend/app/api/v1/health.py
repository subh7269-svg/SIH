from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.db.session import get_db

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "LeadForge Bitcoin Investigation Platform",
        "version": "1.0.0",
        "mode": "offline-ready"
    }

@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
            "offline_geoip": "loaded"
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "database": f"error: {str(e)}"
        }
