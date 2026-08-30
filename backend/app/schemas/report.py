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

class ReportGenerateRequest(BaseModel):
    title: str
    entity_id: str
    entity_type: str = "WALLET"
    include_graph_summary: bool = True
    include_evidence: bool = True
    analyst_notes: Optional[str] = None

class ReportResponse(BaseModel):
    report_id: str
    generated_at: datetime
    title: str
    entity_id: str
    entity_type: str
    risk_score: int
    anomaly_score: float
    severity: str
    disclaimer: str
    explanation: List[str]
    feature_breakdown: Dict[str, Any]
    transaction_evidence: List[Dict[str, Any]]
    network_observations: List[Dict[str, Any]]
    counterparties: List[Dict[str, Any]]
    analyst_notes: Optional[str]
    markdown_content: str
