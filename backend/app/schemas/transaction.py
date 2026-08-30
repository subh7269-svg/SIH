from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class TransactionInputSchema(BaseModel):
    wallet_address: str
    amount: float

class TransactionOutputSchema(BaseModel):
    wallet_address: str
    amount: float

class IPObservationSchema(BaseModel):
    id: Optional[str] = None
    txid: str
    timestamp: datetime
    src_ip: str
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    country: Optional[str] = "UNKNOWN"
    asn: Optional[str] = "UNKNOWN"

    class Config:
        from_attributes = True

class TransactionDetailSchema(BaseModel):
    id: str
    txid: str
    dataset_id: str
    timestamp: datetime
    fee: float
    script_type: str
    input_total: float
    output_total: float
    inputs: List[TransactionInputSchema] = []
    outputs: List[TransactionOutputSchema] = []
    ip_observations: List[IPObservationSchema] = []

    class Config:
        from_attributes = True

class TransactionListResponse(BaseModel):
    total: int
    transactions: List[TransactionDetailSchema]
