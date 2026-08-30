import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Integer, Index
from backend.app.db.base import Base

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    address = Column(String(128), unique=True, nullable=False, index=True)
    first_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    total_received = Column(Float, default=0.0)
    total_sent = Column(Float, default=0.0)
    tx_count = Column(Integer, default=0)
    risk_score = Column(Integer, default=0)  # 0 to 100
    anomaly_score = Column(Float, default=0.0)  # 0.0 to 1.0
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_wallet_risk_score", "risk_score"),
    )
