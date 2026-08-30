from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # WALLET, TRANSACTION, IP, ASN, COUNTRY
    risk_score: int = 0
    anomaly_score: float = 0.0
    is_focal: bool = False
    properties: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str  # INPUT_OF, OUTPUT_TO, OBSERVED_IN, BELONGS_TO_ASN, LOCATED_IN, TRANSFERS_TO
    label: Optional[str] = None
    amount: Optional[float] = None
    timestamp: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    node_count: int
    edge_count: int
    focal_node_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PathQueryRequest(BaseModel):
    source_id: str
    target_id: str
    max_depth: int = 4
