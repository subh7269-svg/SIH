from fastapi import APIRouter, HTTPException
from backend.app.services.job_service import get_job

router = APIRouter(prefix="/jobs", tags=["Background Jobs"])

@router.get("/{job_id}")
def check_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return job
