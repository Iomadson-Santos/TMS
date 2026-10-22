from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.audit import AuditRead


router = APIRouter(prefix="/audit", tags=["Auditoria"])


@router.get("", response_model=list[AuditRead])
def list_audit_logs(
    limit: int = Query(default=200, ge=1, le=500),
    entity_type: str | None = Query(default=None, max_length=80),
    action: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[AuditLog]:
    statement = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if entity_type:
        statement = statement.where(AuditLog.entity_type == entity_type)
    if action:
        statement = statement.where(AuditLog.action == action)
    return list(db.scalars(statement).all())
