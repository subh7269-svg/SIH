import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.db.base import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    format = Column(String(10), nullable=False)  # csv, json, xml
    size_bytes = Column(Integer, default=0)
    status = Column(String(50), default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    rejected_records = Column(Integer, default=0)
    data_quality_metrics = Column(JSON, default=dict)
    error_summary = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    transactions = relationship("Transaction", back_populates="dataset", cascade="all, delete-orphan")
    ip_observations = relationship("IPObservation", back_populates="dataset", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="dataset", cascade="all, delete-orphan")
    entity_profiles = relationship("EntityBehaviourProfile", back_populates="dataset", cascade="all, delete-orphan")
