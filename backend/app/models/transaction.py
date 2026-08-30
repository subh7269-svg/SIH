import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.db.base import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    txid = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    fee = Column(Float, default=0.0)
    script_type = Column(String(50), default="P2PKH")
    input_total = Column(Float, default=0.0)
    output_total = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    dataset = relationship("Dataset", back_populates="transactions")
    inputs = relationship("TransactionInput", back_populates="transaction", cascade="all, delete-orphan")
    outputs = relationship("TransactionOutput", back_populates="transaction", cascade="all, delete-orphan")
    ip_observations = relationship("IPObservation", back_populates="transaction")

    __table_args__ = (
        Index("ix_tx_dataset_txid", "dataset_id", "txid"),
    )


class TransactionInput(Base):
    __tablename__ = "transaction_inputs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    txid = Column(String(64), nullable=False, index=True)
    wallet_address = Column(String(128), nullable=False, index=True)
    amount = Column(Float, default=0.0)

    transaction = relationship("Transaction", back_populates="inputs")


class TransactionOutput(Base):
    __tablename__ = "transaction_outputs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    txid = Column(String(64), nullable=False, index=True)
    wallet_address = Column(String(128), nullable=False, index=True)
    amount = Column(Float, default=0.0)

    transaction = relationship("Transaction", back_populates="outputs")


class IPObservation(Base):
    """
    Network-layer observation linking an IP to a broadcasted transaction.
    IMPORTANT: This represents network wire observation, NOT proof of wallet ownership.
    """
    __tablename__ = "ip_observations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    txid = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    src_ip = Column(String(45), nullable=False, index=True)
    dst_ip = Column(String(45), nullable=True, index=True)
    src_port = Column(Integer, nullable=True)
    dst_port = Column(Integer, nullable=True)
    country = Column(String(100), default="UNKNOWN", index=True)
    asn = Column(String(100), default="UNKNOWN", index=True)

    dataset = relationship("Dataset", back_populates="ip_observations")
    transaction = relationship("Transaction", back_populates="ip_observations")

    __table_args__ = (
        Index("ix_ipobs_src_ip_txid", "src_ip", "txid"),
    )
