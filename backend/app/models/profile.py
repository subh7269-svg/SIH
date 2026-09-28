import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Index, Boolean
from sqlalchemy.orm import relationship
from backend.app.db.base import Base

class EntityBehaviourProfile(Base):
    """
    Entity Behavioural Profile derived strictly from raw historical observations in the dataset.
    Stores the learned historical baseline separately from raw transaction records.
    """
    __tablename__ = "entity_behaviour_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True)
    entity_id = Column(String(128), nullable=False, index=True)
    entity_type = Column(String(32), default="WALLET", index=True)

    observation_count = Column(Integer, default=0)
    has_sufficient_history = Column(Boolean, default=False)
    profile_reliability = Column(String(30), default="INSUFFICIENT_HISTORY")  # HIGH, MEDIUM, LOW, INSUFFICIENT_HISTORY

    # Transaction Amount Behaviour
    avg_input_amount = Column(Float, default=0.0)
    median_input_amount = Column(Float, default=0.0)
    input_amount_dispersion = Column(Float, default=0.0)
    avg_output_amount = Column(Float, default=0.0)
    median_output_amount = Column(Float, default=0.0)
    output_amount_dispersion = Column(Float, default=0.0)
    total_input_value = Column(Float, default=0.0)
    total_output_value = Column(Float, default=0.0)
    amount_dispersion = Column(Float, default=0.0)

    # Transaction Activity
    transaction_frequency = Column(Float, default=0.0)  # Txs per day
    transaction_velocity = Column(Float, default=0.0)   # Typical txs per hour
    min_velocity = Column(Float, default=0.0)
    max_velocity = Column(Float, default=0.0)
    avg_inter_transaction_time = Column(Float, default=0.0)  # Seconds

    # Flow Behaviour
    typical_fan_in = Column(Float, default=0.0)
    typical_fan_out = Column(Float, default=0.0)
    unique_counterparty_count = Column(Integer, default=0)

    # Network Behaviour (only where correlation establishes an association)
    network_statistics = Column(JSON, default=dict)

    # Temporal Behaviour
    temporal_statistics = Column(JSON, default=dict)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    dataset = relationship("Dataset", back_populates="entity_profiles")

    __table_args__ = (
        Index("ix_profile_entity_dataset", "entity_id", "dataset_id"),
    )
