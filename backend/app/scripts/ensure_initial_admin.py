from __future__ import annotations

import os
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.security import hash_password, validate_password_policy
from app.models.enums import UserRole
from app.models.user import User
from app.services.audit import register_audit


EMAIL_ADAPTER = TypeAdapter(EmailStr)


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Variavel obrigatoria ausente: {name}")
    return value


def ensure_initial_admin() -> int:
    with SessionLocal() as db:
        existing_admin = db.scalar(select(User).where(User.role == UserRole.ADMIN))
        if existing_admin:
            if existing_admin.is_active:
                print("Administrador ativo ja existe; inicializacao ignorada.")
                return 0
            raise ValueError(
                "Existe um administrador inativo. Use o procedimento de recuperacao; "
                "a inicializacao automatica nao reativa contas."
            )

        name = _required_env("INITIAL_ADMIN_NAME")
        email_raw = _required_env("INITIAL_ADMIN_EMAIL").casefold()
        password = _required_env("INITIAL_ADMIN_PASSWORD")

        if not 2 <= len(name) <= 120:
            raise ValueError("INITIAL_ADMIN_NAME deve ter entre 2 e 120 caracteres")
        try:
            email = str(EMAIL_ADAPTER.validate_python(email_raw)).casefold()
        except ValidationError as exc:
            raise ValueError("INITIAL_ADMIN_EMAIL invalido") from exc

        validate_password_policy(password, email=email, name=name)

        existing = db.scalar(select(User).where(func.lower(User.email) == email))
        if existing:
            raise ValueError("Ja existe um usuario com INITIAL_ADMIN_EMAIL")

        admin = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
            auth_version=1,
            must_change_password=True,
        )
        db.add(admin)
        db.flush()
        action = "initial_admin_created"

        register_audit(
            db,
            user_id=None,
            action=action,
            entity_type="user",
            entity_id=admin.id,
            details={"email": admin.email, "source": "production_bootstrap"},
            ip_address="platform-startup",
        )
        db.commit()

    print("Administrador inicial preparado. A troca de senha sera exigida no primeiro login.")
    return 0


def main() -> int:
    try:
        return ensure_initial_admin()
    except ValueError as exc:
        print(f"Falha ao preparar administrador inicial: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
