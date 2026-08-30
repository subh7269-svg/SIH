from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.db.session import get_db
from backend.app.schemas.entity import EntitySearchResponse, EntityDossierSchema
from backend.app.services.investigation_service import search_entities, get_entity_dossier
from backend.app.services.audit_service import log_audit_event

router = APIRouter(prefix="/entities", tags=["Entities"])

@router.get("/search", response_model=EntitySearchResponse)
def search(q: str = Query(..., min_length=1), limit: int = 30, db: Session = Depends(get_db)):
    results = search_entities(db=db, query_str=q, limit=limit)
    return EntitySearchResponse(
        query=q,
        total_results=len(results),
        results=results
    )

@router.get("/{entity_id}", response_model=EntityDossierSchema)
def get_dossier(entity_id: str, db: Session = Depends(get_db)):
    dossier = get_entity_dossier(db=db, entity_id=entity_id)
    log_audit_event(
        db=db,
        action="ENTITY_DOSSIER_VIEWED",
        target_type="ENTITY",
        target_id=entity_id,
        details={"risk_score": dossier.risk_score, "type": dossier.entity_type}
    )
    return dossier
