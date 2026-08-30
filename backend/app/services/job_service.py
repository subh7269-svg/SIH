import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# In-memory thread-safe background job registry
_JOBS: Dict[str, Dict[str, Any]] = {}

def create_job(job_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {
        "id": job_id,
        "type": job_type,
        "status": "QUEUED",  # QUEUED, RUNNING, COMPLETED, FAILED
        "progress": 0,
        "message": "Job queued for processing",
        "result": None,
        "error": None,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    return job_id

def update_job(job_id: str, status: str, progress: int = 0, message: str = "", result: Any = None, error: str = None):
    if job_id in _JOBS:
        _JOBS[job_id]["status"] = status
        _JOBS[job_id]["progress"] = progress
        _JOBS[job_id]["message"] = message
        _JOBS[job_id]["result"] = result
        _JOBS[job_id]["error"] = error
        _JOBS[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return _JOBS.get(job_id)
