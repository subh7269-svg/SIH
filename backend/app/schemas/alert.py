from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Optional

class AlertUpdateStatus(BaseModel):
    status: str  # NEW, REVIEWING, DISMISSED, ESCALATED, RESOLVED
    note: Optional[str] = None
    assigned_to: Optional[str] = None

class AlertResponse(BaseModel):
    id: str
    dataset_id: Optional[str]
    entity_id: str
    entity_type: str
    anomaly_score: float
    priority_score: int
    severity: str
    confidence: float
    status: str
    reasons: List[str]
    explanation_details: Dict[str, Any]
    evidence_summary: Dict[str, Any]
    assigned_to: Optional[str]
    notes: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AlertListResponse(BaseModel):
    total: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    alerts: List[AlertResponse]
