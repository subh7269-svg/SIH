from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.app.schemas.graph import GraphResponse

class ReplayStageSchema(BaseModel):
    stage_id: str
    stage_name: str
    order: int
    status: str = "COMPLETED"
    timestamp: Optional[datetime] = None
    summary: str
    data: Dict[str, Any] = Field(default_factory=dict)

class InvestigationReplayResponse(BaseModel):
    replay_id: str
    alert_id: str
    entity_id: str
    entity_type: str
    priority_score: int
    severity: str
    status: str
    dataset_id: Optional[str] = None
    created_at: datetime
    stages: List[ReplayStageSchema]
    graph_data: Optional[GraphResponse] = None
