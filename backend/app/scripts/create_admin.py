from __future__ import annotations

import argparse
from getpass import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.security import hash_password, validate_password_policy
from app.models.enums import UserRole
from app.models.user import User
from app.services.audit import register_audit


EMAIL_ADAPTER = TypeAdapter(EmailStr)


def _prompt_name(value: str | None) -> str:
    name = (value or input("Nome do administrador: ")).strip()
    if not 2 <= len(name) <= 120:
        raise ValueError("O nome deve ter entre 2 e 120 caracteres")
    return name


def _prompt_email(value: str | None) -> str:
    raw = (value or input("E-mail do administrador: ")).strip().casefold()
    try:
        return str(EMAIL_ADAPTER.validate_python(raw)).casefold()
    except ValidationError as exc:
        raise ValueError("E-mail invalido") from exc


def _prompt_password(*, email: str, name: str) -> str:
    password = getpass("Senha temporaria forte (nao sera exibida): ")
    confirmation = getpass("Confirme a senha: ")
    if password != confirmation:
        raise ValueError("As senhas nao conferem")
    validate_password_policy(password, email=email, name=name)
    return password


def create_admin(name: str, email: str, password: str) -> User:
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(func.lower(User.email) == email))
        if existing:
            raise ValueError("Ja existe um usuario com esse e-mail")

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
        register_audit(
            db,
            user_id=None,
            action="initial_admin_created",
            entity_type="user",
            entity_id=admin.id,
            details={"email": admin.email, "source": "local_cli"},
            ip_address="local-cli",
        )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Nao foi possivel criar o administrador") from exc
        db.refresh(admin)
        return admin


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cria o primeiro administrador sem expor a senha no historico do terminal"
    )
    parser.add_argument("--name", help="Nome; se omitido, sera solicitado")
    parser.add_argument("--email", help="E-mail; se omitido, sera solicitado")
    args = parser.parse_args()

    try:
        name = _prompt_name(args.name)
        email = _prompt_email(args.email)
        password = _prompt_password(email=email, name=name)
        admin = create_admin(name, email, password)
    except (EOFError, KeyboardInterrupt):
        print("\nOperacao cancelada.")
        return 130
    except (OSError, ValueError) as exc:
        print(f"Falha: {exc}")
        return 1

    print(f"Administrador criado: {admin.email}")
    print("No primeiro login, o sistema exigira a troca da senha temporaria.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
