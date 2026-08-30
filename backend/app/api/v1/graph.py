from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.db.session import get_db
from backend.app.schemas.graph import GraphResponse, PathQueryRequest
from backend.app.services.graph_service import (
    query_entity_subgraph,
    query_shortest_path,
    query_global_graph_overview
)

router = APIRouter(prefix="/graph", tags=["Graph Explorer"])

@router.get("/overview", response_model=GraphResponse)
def get_graph_overview(limit: int = 75, dataset_id: Optional[str] = None, db: Session = Depends(get_db)):
    return query_global_graph_overview(db=db, limit=limit, dataset_id=dataset_id)

@router.get("/entity/{entity_id}", response_model=GraphResponse)
def get_entity_graph(
    entity_id: str,
    k: int = Query(2, ge=1, le=4),
    dataset_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return query_entity_subgraph(db=db, entity_id=entity_id, k=k, dataset_id=dataset_id)

@router.post("/path", response_model=GraphResponse)
def get_path_graph(req: PathQueryRequest, dataset_id: Optional[str] = None, db: Session = Depends(get_db)):
    return query_shortest_path(db=db, source_id=req.source_id, target_id=req.target_id, dataset_id=dataset_id)
