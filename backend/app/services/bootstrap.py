from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User


def ensure_bootstrap_admin(db: Session) -> User | None:
    if not settings.bootstrap_admin_enabled:
        return None

    email = settings.bootstrap_admin_email.strip().lower()
    existing = db.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        return existing

    admin = User(
        name=settings.bootstrap_admin_name,
        email=email,
        password_hash=hash_password(settings.bootstrap_admin_password),
        role=UserRole.ADMIN,
        is_active=True,
        auth_version=1,
        must_change_password=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin
