from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Optional

class MLTrainRequest(BaseModel):
    dataset_id: Optional[str] = None
    model_type: str = "ISOLATION_FOREST"  # ISOLATION_FOREST, LOCAL_OUTLIER_FACTOR, BOTH
    contamination: float = 0.05
    n_estimators: int = 100
    random_state: int = 42

class MLModelSummary(BaseModel):
    id: str
    model_name: str
    model_type: str
    version: str
    is_active: int
    feature_names: List[str]
    evaluation_metrics: Dict[str, Any]
    training_duration_ms: int
    dataset_records_count: int
    trained_at: datetime

    class Config:
        from_attributes = True

class ClusterSummary(BaseModel):
    id: str
    dataset_id: Optional[str]
    cluster_label: int
    cluster_name: str
    algorithm: str
    member_count: int
    member_ids: List[str]
    characteristics: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True

class ClusterListResponse(BaseModel):
    total_clusters: int
    noise_count: int
    clusters: List[ClusterSummary]
