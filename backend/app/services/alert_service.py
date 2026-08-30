from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.models.alert import Alert
from backend.app.core.errors import EntityNotFoundError
from backend.app.services.audit_service import log_audit_event

def list_alerts(
    db: Session,
    dataset_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    query = db.query(Alert)

    if dataset_id:
        query = query.filter(Alert.dataset_id == dataset_id)
    if severity:
        query = query.filter(Alert.severity == severity.upper())
    if status:
        query = query.filter(Alert.status == status.upper())
    if min_score is not None:
        query = query.filter(Alert.priority_score >= min_score)

    total = query.count()
    alerts = query.order_by(Alert.priority_score.desc(), Alert.anomaly_score.desc()).offset(offset).limit(limit).all()

    # Severity distribution
    crit_count = db.query(Alert).filter(Alert.severity == "CRITICAL").count()
    high_count = db.query(Alert).filter(Alert.severity == "HIGH").count()
    med_count = db.query(Alert).filter(Alert.severity == "MEDIUM").count()
    low_count = db.query(Alert).filter(Alert.severity == "LOW").count()

    return {
        "total": total,
        "critical_count": crit_count,
        "high_count": high_count,
        "medium_count": med_count,
        "low_count": low_count,
        "alerts": alerts
    }

def get_alert_by_id(db: Session, alert_id: str) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise EntityNotFoundError("Alert", alert_id)
    return alert

def update_alert_status(
    db: Session,
    alert_id: str,
    new_status: str,
    note: Optional[str] = None,
    assigned_to: Optional[str] = None,
    user_name: str = "investigator"
) -> Alert:
    alert = get_alert_by_id(db, alert_id)
    old_status = alert.status
    alert.status = new_status.upper()
    alert.updated_at = datetime.now(timezone.utc)
    if assigned_to:
        alert.assigned_to = assigned_to

    if note:
        current_notes = list(alert.notes or [])
        current_notes.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user_name,
            "note": note,
            "status_change": f"{old_status} -> {alert.status}"
        })
        alert.notes = current_notes

    db.commit()
    db.refresh(alert)

    log_audit_event(
        db=db,
        action="ALERT_TRIAGE_STATUS_UPDATE",
        target_type="ALERT",
        target_id=alert_id,
        details={"old_status": old_status, "new_status": alert.status, "note": note},
        user_name=user_name
    )

    return alert
