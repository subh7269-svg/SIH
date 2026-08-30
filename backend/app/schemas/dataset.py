from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List

class DataQualityMetrics(BaseModel):
    total_records: int = 0
    valid_records: int = 0
    rejected_records: int = 0
    duplicate_records: int = 0
    missing_fields_count: int = 0
    unique_wallets: int = 0
    unique_txids: int = 0
    unique_src_ips: int = 0
    unique_countries: int = 0
    unique_asns: int = 0
    time_min: Optional[str] = None
    time_max: Optional[str] = None
    total_btc_volume: float = 0.0
    avg_fee: float = 0.0
    field_completeness: Dict[str, float] = Field(default_factory=dict)
    rejected_reasons: Dict[str, int] = Field(default_factory=dict)

class DatasetBase(BaseModel):
    filename: str
    format: str

class DatasetCreate(DatasetBase):
    size_bytes: int = 0

class DatasetResponse(DatasetBase):
    id: str
    size_bytes: int
    status: str
    total_records: int
    processed_records: int
    rejected_records: int
    data_quality_metrics: Optional[Dict[str, Any]] = None
    error_summary: Optional[str] = None
    uploaded_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DatasetListResponse(BaseModel):
    total: int
    datasets: List[DatasetResponse]
