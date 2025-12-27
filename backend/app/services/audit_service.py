from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


async def audit_log(
    db: Session,
    user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    description: str = "",
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,  # Kept param name for backward compat
    success: str = "success",
    error_message: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None
) -> AuditLog:
    """Create an audit log entry."""
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        old_values=old_values,
        new_values=new_values,
        extra_data=metadata,  # Renamed field in model
        success=success,
        error_message=error_message,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id
    )

    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)

    return audit_entry


def get_audit_logs(
    db: Session,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> list[AuditLog]:
    """Retrieve audit logs with optional filtering."""
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if action:
        query = query.filter(AuditLog.action == action)

    query = query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)

    return query.all()


def get_user_activity_summary(
    db: Session,
    user_id: int,
    days: int = 30
) -> Dict[str, Any]:
    """Get activity summary for a user."""
    from sqlalchemy import func, text

    # Get activity counts by action type
    activity_counts = db.query(
        AuditLog.action,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.user_id == user_id,
        AuditLog.timestamp >= text(f"NOW() - INTERVAL '{days} days'")
    ).group_by(AuditLog.action).all()

    # Get recent logins
    recent_logins = db.query(AuditLog).filter(
        AuditLog.user_id == user_id,
        AuditLog.action == "login",
        AuditLog.timestamp >= text(f"NOW() - INTERVAL '{days} days'")
    ).order_by(AuditLog.timestamp.desc()).limit(10).all()

    return {
        "activity_counts": {row.action: row.count for row in activity_counts},
        "recent_logins": [
            {
                "timestamp": login.timestamp,
                "ip_address": login.ip_address,
                "user_agent": login.user_agent
            } for login in recent_logins
        ]
    }
