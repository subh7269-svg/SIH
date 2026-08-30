import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Text, Index
from backend.app.db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_name = Column(String(100), default="investigator", index=True)
    action = Column(String(100), nullable=False, index=True)  # DATASET_UPLOAD, ML_TRAIN, ALERT_TRIAGE, REPORT_GEN
    target_type = Column(String(50), nullable=True)  # DATASET, ALERT, ENTITY, MODEL, REPORT
    target_id = Column(String(128), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), default="127.0.0.1")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("ix_audit_user_timestamp", "user_name", "timestamp"),
    )
