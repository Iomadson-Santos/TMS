from datetime import datetime
from typing import Any

from app.schemas.base import ORMModel
from app.schemas.user import UserRead


class AuditRead(ORMModel):
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime
    user: UserRead | None
