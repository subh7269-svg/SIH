"""
Background Job Manager for Asynchronous Correlation Processing.
Tracks progress, step transitions, metrics, and completion state.
Prevents blocking of FastAPI request threads during 600+ MB processing.
"""
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import threading

class CorrelationJobManager:
    """Thread-safe singleton job manager for correlation runs."""
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_job(self, params: Optional[Dict[str, Any]] = None) -> str:
        with self._lock:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            job_id = f"corr_{ts}_{uuid.uuid4().hex[:4]}"
            self.jobs[job_id] = {
                "job_id": job_id,
                "status": "started",
                "step": "initializing",
                "progress_pct": 0.0,
                "processed_transactions": 0,
                "total_transactions": 0,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": None,
                "error": None,
                "params": params or {},
                "metrics": {
                    "transactions_processed": 0,
                    "wallets_connected": 0,
                    "network_observations": 0,
                    "correlated_transactions": 0,
                    "investigation_leads": 0,
                    "high_priority_leads": 0
                }
            }
            return job_id

    def update_progress(
        self,
        job_id: str,
        step: Optional[str] = None,
        progress_pct: Optional[float] = None,
        processed: Optional[int] = None,
        total: Optional[int] = None,
        metrics: Optional[Dict[str, Any]] = None
    ):
        with self._lock:
            if job_id not in self.jobs:
                return
            job = self.jobs[job_id]
            job["status"] = "running"
            if step:
                job["step"] = step
            if progress_pct is not None:
                job["progress_pct"] = round(min(100.0, max(0.0, progress_pct)), 1)
            if processed is not None:
                job["processed_transactions"] = processed
            if total is not None:
                job["total_transactions"] = total
            if metrics:
                job["metrics"].update(metrics)

    def mark_completed(self, job_id: str, metrics: Optional[Dict[str, Any]] = None):
        with self._lock:
            if job_id not in self.jobs:
                return
            job = self.jobs[job_id]
            job["status"] = "completed"
            job["step"] = "finished"
            job["progress_pct"] = 100.0
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            if metrics:
                job["metrics"].update(metrics)

    def mark_failed(self, job_id: str, error_message: str):
        with self._lock:
            if job_id not in self.jobs:
                return
            job = self.jobs[job_id]
            job["status"] = "failed"
            job["error"] = error_message
            job["completed_at"] = datetime.now(timezone.utc).isoformat()

    def get_job(self, job_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self.jobs:
                return None
            if job_id and job_id in self.jobs:
                return self.jobs[job_id]
            # Return most recent job if no ID provided
            latest_id = list(self.jobs.keys())[-1]
            return self.jobs[latest_id]

job_manager = CorrelationJobManager()
