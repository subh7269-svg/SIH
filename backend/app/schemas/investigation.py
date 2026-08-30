from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Optional

class CaseCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "HIGH"
    lead_investigator: str = "Investigator"
    pinned_entities: List[str] = []
    pinned_alerts: List[str] = []

class CaseResponse(BaseModel):
    id: str
    case_number: str
    title: str
    description: Optional[str]
    lead_investigator: str
    status: str
    priority: str
    pinned_entities: List[str]
    pinned_alerts: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
