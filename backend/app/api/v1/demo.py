from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.db.session import get_db
from backend.app.services.demo_service import run_one_click_demo, reset_all_data

router = APIRouter(prefix="/demo", tags=["Demo Mode"])

@router.post("/run")
def execute_demo(seed: int = Query(42), db: Session = Depends(get_db)):
    """
    1-Click SIH 2026 Demo Execution.
    Generates synthetic dataset, ingests, correlates, builds graph, runs Isolation Forest & LOF,
    clusters with DBSCAN, calculates risk priority scores, and generates ranked explainable alerts.
    """
    return run_one_click_demo(db=db, seed=seed)

@router.post("/reset")
def reset_demo(db: Session = Depends(get_db)):
    reset_all_data(db)
    return {"status": "SUCCESS", "message": "All investigative datasets and entities reset to clean slate."}
