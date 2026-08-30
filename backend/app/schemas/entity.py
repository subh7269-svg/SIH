from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

class WalletSummarySchema(BaseModel):
    id: str
    address: str
    first_seen: datetime
    last_seen: datetime
    total_received: float
    total_sent: float
    tx_count: int
    risk_score: int
    anomaly_score: float

    class Config:
        from_attributes = True

class EntityDossierSchema(BaseModel):
    entity_id: str
    entity_type: str  # WALLET, IP, TXID, ASN
    risk_score: int
    anomaly_score: float
    severity: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_volume_btc: float = 0.0
    transaction_count: int = 0
    unique_counterparties: int = 0
    observed_ips: List[Dict[str, Any]] = []
    observed_countries: List[str] = []
    observed_asns: List[str] = []
    features: Dict[str, Any] = {}
    explanation_reasons: List[str] = []
    feature_deviations: Dict[str, Any] = {}
    recent_transactions: List[Dict[str, Any]] = []
    related_alerts: List[Dict[str, Any]] = []
    cluster_info: Optional[Dict[str, Any]] = None

class EntitySearchResult(BaseModel):
    entity_id: str
    entity_type: str
    label: str
    subtext: str
    risk_score: int
    anomaly_score: float
    metadata: Dict[str, Any] = {}

class EntitySearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[EntitySearchResult]
