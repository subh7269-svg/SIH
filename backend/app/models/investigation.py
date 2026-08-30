import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.base import Base

class InvestigationCase(Base):
    __tablename__ = "investigation_cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    lead_investigator = Column(String(100), default="Investigator")
    status = Column(String(30), default="OPEN", index=True)  # OPEN, IN_PROGRESS, CLOSED, ARCHIVED
    priority = Column(String(20), default="HIGH")  # LOW, MEDIUM, HIGH, CRITICAL
    pinned_entities = Column(JSON, default=list)
    pinned_alerts = Column(JSON, default=list)
    graph_snapshot = Column(JSON, default=dict)
    summary_report = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
