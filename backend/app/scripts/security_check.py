from __future__ import annotations

import argparse
from collections import Counter
import sys

from app.core.config import DEFAULT_SECRET_KEY, settings


KNOWN_DEMO_PASSWORDS = {
    "admin@tmsciranda.com.br": "Admin123!",
    "operador@tmsciranda.com.br": "Operador123!",
    "motorista@tmsciranda.com.br": "Motorista123!",
}
REQUIRED_TABLES = {
    "users",
    "login_throttles",
    "revoked_tokens",
    "auth_sessions",
    "audit_logs",
    "vehicles",
    "deliveries",
    "routes",
}


def config_findings() -> tuple[list[str], list[str]]:
    errors = list(settings.production_security_errors())
    warnings: list[str] = []

    if not settings.is_production:
        errors.append("ENVIRONMENT deve ser production para a verificacao de publicacao")
    if len({settings.auth_cookie_name, settings.refresh_cookie_name, settings.csrf_cookie_name}) != 3:
        errors.append("Os cookies de sessao, refresh e CSRF precisam ter nomes diferentes")
    if settings.secret_key == DEFAULT_SECRET_KEY:
        errors.append("SECRET_KEY ainda usa o valor padrao")
    if len(set(settings.secret_key)) < 16:
        errors.append("SECRET_KEY tem pouca diversidade de caracteres")
    if settings.login_lock_max_seconds < settings.login_lock_seconds:
        errors.append("LOGIN_LOCK_MAX_SECONDS nao pode ser menor que LOGIN_LOCK_SECONDS")
    if settings.tracking_retention_days == 0:
        warnings.append("TRACKING_RETENTION_DAYS=0 mantem historico de GPS sem prazo")
    return errors, warnings


def database_findings() -> tuple[list[str], list[str]]:
    # Os imports de banco ficam dentro desta funcao. Assim, --config-only pode
    # validar um arquivo de producao antes mesmo de o driver PostgreSQL estar
    # instalado ou de o banco estar acessivel.
    from sqlalchemy import func, inspect, select
    from sqlalchemy.exc import SQLAlchemyError

    from app.core.database import SessionLocal, engine
    from app.core.security import hash_password, verify_password
    from app.models.enums import UserRole
    from app.models.user import User

    errors: list[str] = []
    warnings: list[str] = []

    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
    except SQLAlchemyError as exc:
        return [f"Nao foi possivel conectar ao banco: {type(exc).__name__}"], warnings

    missing_tables = sorted(REQUIRED_TABLES - tables)
    if missing_tables:
        errors.append(f"Migracoes pendentes; tabelas ausentes: {', '.join(missing_tables)}")
        return errors, warnings

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    for required in {"auth_version", "must_change_password"}:
        if required not in user_columns:
            errors.append(f"Migracao de seguranca ausente: users.{required}")

    try:
        with SessionLocal() as db:
            active_admins = int(
                db.scalar(
                    select(func.count())
                    .select_from(User)
                    .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
                )
                or 0
            )
            if active_admins < 1:
                errors.append("Nao existe administrador ativo")

            users = list(db.scalars(select(User)).all())
            by_email = {user.email.casefold(): user for user in users}
            for email, password in KNOWN_DEMO_PASSWORDS.items():
                user = by_email.get(email)
                if user and verify_password(password, user.password_hash):
                    errors.append(
                        f"A conta {email} ainda usa a senha publica de demonstracao"
                    )

            temporary = [
                user.email
                for user in users
                if user.is_active and user.must_change_password
            ]
            if temporary:
                warnings.append(
                    f"{len(temporary)} conta(s) ativa(s) aguardam troca de senha obrigatoria"
                )

            duplicate_emails = [
                email
                for email, count in Counter(user.email.casefold() for user in users).items()
                if count > 1
            ]
            if duplicate_emails:
                errors.append("Existem e-mails duplicados sem diferenca de maiusculas/minusculas")
    except SQLAlchemyError as exc:
        errors.append(f"Falha ao validar dados de seguranca: {type(exc).__name__}")

    try:
        test_hash = hash_password("teste-interno-de-algoritmo-nao-persistido")
        if not test_hash.startswith("$argon2id$"):
            errors.append("O algoritmo de senha ativo nao e Argon2id")
    except Exception as exc:  # pragma: no cover - diagnostico de ambiente
        errors.append(f"Nao foi possivel validar o hash de senha: {type(exc).__name__}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica pre-requisitos de seguranca")
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Valida apenas variaveis de ambiente, antes das migracoes",
    )
    args = parser.parse_args()

    errors, warnings = config_findings()
    if not args.config_only and not errors:
        db_errors, db_warnings = database_findings()
        errors.extend(db_errors)
        warnings.extend(db_warnings)

    print("\nVerificacao de seguranca do TMS")
    print("=" * 34)
    for warning in warnings:
        print(f"[AVISO] {warning}")
    for error in errors:
        print(f"[ERRO]  {error}")

    if errors:
        print("\nPublicacao bloqueada. Corrija os itens acima.")
        return 1

    print("[OK] Configuracao aprovada para iniciar o processo de publicacao.")
    if args.config_only:
        print("[OK] Execute as migracoes e depois rode a verificacao completa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
