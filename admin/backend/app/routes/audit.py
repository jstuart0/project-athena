"""
Audit log API routes.

Provides read-only access to audit logs for compliance and security monitoring.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import structlog

from app.database import get_db
from app.auth.oidc import get_current_user
from app.models import User, AuditLog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    """Response model for audit log data."""
    id: int
    timestamp: str
    user: str
    action: str
    resource_type: str
    resource_id: int = None
    old_value: dict = None
    new_value: dict = None
    ip_address: str = None
    success: bool
    error_message: str = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    resource_type: str = None,
    resource_id: int = None,
    user_id: int = None,
    action: str = None,
    start_date: datetime = Query(None, description="Start date for filtering (ISO format)"),
    end_date: datetime = Query(None, description="End date for filtering (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List audit logs with optional filtering.

    Requires view_audit permission.
    """
    if not current_user.has_permission('view_audit'):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view audit logs")

    query = db.query(AuditLog)

    # Apply filters
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id is not None:
        query = query.filter(AuditLog.resource_id == resource_id)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    # Order by timestamp descending (most recent first)
    query = query.order_by(AuditLog.timestamp.desc())

    # Pagination
    total_count = query.count()
    logs = query.offset(offset).limit(limit).all()

    logger.info("audit_logs_queried", user=current_user.username, count=len(logs),
                total=total_count, filters={
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'action': action
                })

    return [log.to_dict() for log in logs]


@router.get("/stats")
async def get_audit_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to include in stats"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit log statistics.

    Returns counts by action type, resource type, and user for the specified time period.
    """
    if not current_user.has_permission('view_audit'):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view audit logs")

    start_date = datetime.utcnow() - timedelta(days=days)

    # Total count
    total = db.query(AuditLog).filter(AuditLog.timestamp >= start_date).count()

    # Count by action
    actions = db.query(AuditLog.action, db.func.count(AuditLog.id))\
        .filter(AuditLog.timestamp >= start_date)\
        .group_by(AuditLog.action)\
        .all()

    # Count by resource type
    resources = db.query(AuditLog.resource_type, db.func.count(AuditLog.id))\
        .filter(AuditLog.timestamp >= start_date)\
        .group_by(AuditLog.resource_type)\
        .all()

    # Count by user (top 10)
    users = db.query(User.username, db.func.count(AuditLog.id))\
        .join(AuditLog, User.id == AuditLog.user_id)\
        .filter(AuditLog.timestamp >= start_date)\
        .group_by(User.username)\
        .order_by(db.func.count(AuditLog.id).desc())\
        .limit(10)\
        .all()

    # Failed operations
    failures = db.query(AuditLog).filter(
        AuditLog.timestamp >= start_date,
        AuditLog.success == False
    ).count()

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "total_logs": total,
        "by_action": {action: count for action, count in actions},
        "by_resource_type": {resource: count for resource, count in resources},
        "top_users": {username: count for username, count in users},
        "failed_operations": failures
    }


@router.get("/recent")
async def get_recent_audit_logs(
    limit: int = Query(20, ge=1, le=100, description="Number of recent logs to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get most recent audit logs (simplified endpoint for dashboards)."""
    if not current_user.has_permission('view_audit'):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view audit logs")

    logs = db.query(AuditLog)\
        .order_by(AuditLog.timestamp.desc())\
        .limit(limit)\
        .all()

    return [log.to_dict() for log in logs]


@router.get("/resource/{resource_type}/{resource_id}")
async def get_resource_audit_trail(
    resource_type: str,
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get complete audit trail for a specific resource."""
    if not current_user.has_permission('view_audit'):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view audit logs")

    logs = db.query(AuditLog)\
        .filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id
        )\
        .order_by(AuditLog.timestamp.desc())\
        .all()

    if not logs:
        raise HTTPException(
            status_code=404,
            detail=f"No audit logs found for {resource_type} {resource_id}"
        )

    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "log_count": len(logs),
        "first_seen": logs[-1].timestamp.isoformat() if logs else None,
        "last_modified": logs[0].timestamp.isoformat() if logs else None,
        "logs": [log.to_dict() for log in logs]
    }


@router.get("/user/{user_id}")
async def get_user_activity(
    user_id: int,
    days: int = Query(30, ge=1, le=90, description="Number of days to include"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get activity history for a specific user."""
    if not current_user.has_permission('view_audit'):
        raise HTTPException(status_code=403, detail="Insufficient permissions to view audit logs")

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    start_date = datetime.utcnow() - timedelta(days=days)

    logs = db.query(AuditLog)\
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.timestamp >= start_date
        )\
        .order_by(AuditLog.timestamp.desc())\
        .all()

    # Count by action type
    actions = db.query(AuditLog.action, db.func.count(AuditLog.id))\
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.timestamp >= start_date
        )\
        .group_by(AuditLog.action)\
        .all()

    return {
        "user_id": user_id,
        "username": user.username,
        "period_days": days,
        "total_actions": len(logs),
        "by_action": {action: count for action, count in actions},
        "recent_activity": [log.to_dict() for log in logs[:50]]  # Last 50 actions
    }
