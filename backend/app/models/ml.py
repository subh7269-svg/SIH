import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON
from backend.app.db.base import Base

class MLModelArtifact(Base):
    __tablename__ = "ml_models"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name = Column(String(100), nullable=False)
    model_type = Column(String(50), nullable=False)  # ISOLATION_FOREST, LOCAL_OUTLIER_FACTOR
    version = Column(String(50), nullable=False)
    is_active = Column(Integer, default=1)  # 1=active, 0=inactive
    hyperparameters = Column(JSON, default=dict)
    feature_names = Column(JSON, default=list)
    evaluation_metrics = Column(JSON, default=dict)  # precision, recall, f1, roc_auc, pr_auc
    training_duration_ms = Column(Integer, default=0)
    dataset_records_count = Column(Integer, default=0)
    artifact_path = Column(String(255), nullable=True)
    trained_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EntityCluster(Base):
    __tablename__ = "entity_clusters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), nullable=True, index=True)
    cluster_label = Column(Integer, nullable=False, index=True)  # -1 is noise
    cluster_name = Column(String(100), nullable=False)
    algorithm = Column(String(50), default="DBSCAN")
    entity_type = Column(String(32), default="WALLET")
    member_count = Column(Integer, default=0)
    member_ids = Column(JSON, default=list)
    characteristics = Column(JSON, default=dict)  # mean features, avg velocity, summary
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
