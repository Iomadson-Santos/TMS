from __future__ import annotations

import argparse
from getpass import getpass
import sys
from pathlib import Path

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import (
    hash_password,
    security_digest,
    validate_password_policy,
    verify_password,
)
from app.models.auth import LoginThrottle
from app.models.enums import UserRole
from app.models.user import User
from app.scripts.backup_database import create_backup
from app.services.audit import register_audit
from app.services.auth_security import (
    IDENTITY_SCOPE,
    IP_SCOPE,
    PASSWORD_CHANGE_SCOPE,
    normalize_identifier,
)
from app.services.sessions import revoke_user_sessions


EMAIL_ADAPTER = TypeAdapter(EmailStr)
LOCAL_IPS = ("127.0.0.1", "::1")


def _normalize_email(value: str) -> str:
    raw = value.strip().casefold()
    try:
        return str(EMAIL_ADAPTER.validate_python(raw)).casefold()
    except ValidationError as exc:
        raise ValueError("E-mail invalido") from exc


def _prompt_email(value: str | None) -> str:
    default = settings.bootstrap_admin_email.strip().casefold()
    raw = value
    if raw is None:
        entered = input(f"E-mail do administrador [{default}]: ").strip()
        raw = entered or default
    return _normalize_email(raw)


def _prompt_password(*, email: str, name: str, current_hash: str) -> str:
    password = getpass("Nova senha (nao sera exibida): ")
    confirmation = getpass("Confirme a nova senha: ")
    if password != confirmation:
        raise ValueError("As senhas nao conferem")
    validate_password_policy(password, email=email, name=name)
    if verify_password(password, current_hash):
        raise ValueError("A nova senha deve ser diferente da senha atual")
    return password


def _prompt_force_change() -> bool:
    answer = input("Exigir outra troca de senha no proximo login? [s/N]: ").strip().casefold()
    return answer in {"s", "sim", "y", "yes"}


def _find_admin(email: str) -> User:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == email))
        if user is None or user.role != UserRole.ADMIN:
            raise ValueError("Administrador nao encontrado com esse e-mail")
        db.expunge(user)
        return user


def _clear_admin_throttles(db, *, user_id: int, email: str) -> int:
    conditions = [
        (
            (LoginThrottle.scope == IDENTITY_SCOPE)
            & (
                LoginThrottle.key_hash
                == security_digest(IDENTITY_SCOPE, normalize_identifier(email))
            )
        )
    ]

    for ip_address in LOCAL_IPS:
        conditions.append(
            (
                (LoginThrottle.scope == IP_SCOPE)
                & (
                    LoginThrottle.key_hash
                    == security_digest(IP_SCOPE, ip_address)
                )
            )
        )
        reauth_key = f"{user_id}:{ip_address}"
        conditions.append(
            (
                (LoginThrottle.scope == PASSWORD_CHANGE_SCOPE)
                & (
                    LoginThrottle.key_hash
                    == security_digest(PASSWORD_CHANGE_SCOPE, reauth_key)
                )
            )
        )

    result = db.execute(
        delete(LoginThrottle)
        .where(or_(*conditions))
        .execution_options(synchronize_session=False)
    )
    return int(result.rowcount or 0)


def reset_admin_password(
    *,
    email: str,
    password: str,
    force_change: bool,
    backup_first: bool = True,
) -> tuple[int, int, Path | None]:
    normalized_email = _normalize_email(email)
    profile = _find_admin(normalized_email)
    validate_password_policy(password, email=profile.email, name=profile.name)
    if verify_password(password, profile.password_hash):
        raise ValueError("A nova senha deve ser diferente da senha atual")

    backup_path: Path | None = None
    if backup_first:
        backup_path = create_backup()
        if settings.database_url.startswith("sqlite") and backup_path is None:
            raise RuntimeError("Nao foi possivel criar o backup do banco SQLite")

    with SessionLocal() as db:
        user = db.scalar(
            select(User)
            .where(func.lower(User.email) == normalized_email)
            .with_for_update()
        )
        if user is None or user.role != UserRole.ADMIN:
            raise ValueError("Administrador nao encontrado com esse e-mail")
        if not user.is_active:
            raise ValueError(
                "A conta do administrador esta inativa. Reative-a com outro administrador "
                "ou revise o banco antes do reset."
            )

        user.password_hash = hash_password(password)
        user.auth_version = max(1, int(user.auth_version or 0) + 1)
        user.must_change_password = force_change

        sessions_revoked = revoke_user_sessions(db, user.id)
        throttles_removed = _clear_admin_throttles(
            db,
            user_id=user.id,
            email=user.email,
        )
        register_audit(
            db,
            user_id=user.id,
            action="admin_password_emergency_reset",
            entity_type="user",
            entity_id=user.id,
            details={
                "source": "local_cli",
                "sessions_revoked": sessions_revoked,
                "throttles_removed": throttles_removed,
                "password_change_required": force_change,
            },
            ip_address="local-cli",
        )
        db.commit()
        return sessions_revoked, throttles_removed, backup_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Redefine com seguranca a senha de um administrador local, "
            "revoga sessoes e limpa o bloqueio de login da conta."
        )
    )
    parser.add_argument(
        "--email",
        help="E-mail do administrador; se omitido, sera solicitado",
    )
    parser.add_argument(
        "--force-change",
        action="store_true",
        help="Exige outra troca de senha no proximo login sem perguntar",
    )
    parser.add_argument(
        "--no-force-change",
        action="store_true",
        help="Mantem a senha informada como definitiva sem perguntar",
    )
    args = parser.parse_args()

    if args.force_change and args.no_force_change:
        print("Falha: use apenas uma opcao entre --force-change e --no-force-change")
        return 2

    try:
        email = _prompt_email(args.email)
        profile = _find_admin(email)
        print(f"Administrador localizado: {profile.name} ({profile.email})")
        password = _prompt_password(
            email=profile.email,
            name=profile.name,
            current_hash=profile.password_hash,
        )
        if args.force_change:
            force_change = True
        elif args.no_force_change:
            force_change = False
        else:
            force_change = _prompt_force_change()

        print("Criando backup antes da alteracao...")
        sessions_revoked, throttles_removed, backup_path = reset_admin_password(
            email=email,
            password=password,
            force_change=force_change,
            backup_first=True,
        )
    except (EOFError, KeyboardInterrupt):
        print("\nOperacao cancelada. Nenhuma senha foi alterada.")
        return 130
    except (OSError, RuntimeError, SQLAlchemyError, ValueError) as exc:
        print(f"Falha: {exc}")
        return 1

    print("\nSenha do administrador redefinida com sucesso.")
    if backup_path:
        print(f"Backup criado: {backup_path.resolve()}")
    print(f"Sessoes revogadas: {sessions_revoked}")
    print(f"Bloqueios locais removidos: {throttles_removed}")
    if force_change:
        print("No proximo login, o sistema exigira outra troca de senha.")
    else:
        print("A senha informada ja e a senha definitiva.")
    print("Inicie o TMS e entre novamente. As sessoes antigas nao funcionarao.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
