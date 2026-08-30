import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.audit import AuditLog

def log_audit_event(
    db: Session,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    user_name: str = "investigator",
    ip_address: str = "127.0.0.1"
) -> AuditLog:
    """
    Records an immutable audit entry for investigator actions.
    """
    entry = AuditLog(
        id=str(uuid.uuid4()),
        user_name=user_name,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details or {},
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(entry)
    db.commit()
    return entry
