import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Index
from backend.app.db.base import Base

class EntityFeature(Base):
    __tablename__ = "entity_features"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_id = Column(String(128), nullable=False, index=True)
    entity_type = Column(String(32), default="WALLET", index=True)  # WALLET, IP, TRANSACTION
    dataset_id = Column(String(36), nullable=True, index=True)
    features = Column(JSON, default=dict)
    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_feature_entity_dataset", "entity_id", "dataset_id"),
    )
