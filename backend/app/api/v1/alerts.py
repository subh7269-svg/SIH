from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.db.session import get_db
from backend.app.schemas.alert import AlertListResponse, AlertResponse, AlertUpdateStatus
from backend.app.schemas.replay import InvestigationReplayResponse
from backend.app.services.alert_service import list_alerts, get_alert_by_id, update_alert_status
from backend.app.services.replay_service import get_investigation_replay, get_investigation_replay_by_entity

router = APIRouter(prefix="/alerts", tags=["Alerts & Prioritization"])

@router.get("", response_model=AlertListResponse)
def get_alerts(
    dataset_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    result = list_alerts(
        db=db,
        dataset_id=dataset_id,
        severity=severity,
        status=status,
        min_score=min_score,
        limit=limit,
        offset=offset
    )
    return AlertListResponse(
        total=result["total"],
        critical_count=result["critical_count"],
        high_count=result["high_count"],
        medium_count=result["medium_count"],
        low_count=result["low_count"],
        alerts=[AlertResponse.model_validate(a) for a in result["alerts"]]
    )

@router.get("/entity/{entity_id}/replay", response_model=InvestigationReplayResponse)
def get_entity_replay(entity_id: str, db: Session = Depends(get_db)):
    return get_investigation_replay_by_entity(db=db, entity_id=entity_id)

@router.get("/{alert_id}/replay", response_model=InvestigationReplayResponse)
def get_alert_replay(alert_id: str, db: Session = Depends(get_db)):
    return get_investigation_replay(db=db, alert_id=alert_id)

@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = get_alert_by_id(db=db, alert_id=alert_id)
    return AlertResponse.model_validate(alert)

@router.patch("/{alert_id}/status", response_model=AlertResponse)
def update_status(alert_id: str, body: AlertUpdateStatus, db: Session = Depends(get_db)):
    alert = update_alert_status(
        db=db,
        alert_id=alert_id,
        new_status=body.status,
        note=body.note,
        assigned_to=body.assigned_to
    )
    return AlertResponse.model_validate(alert)
