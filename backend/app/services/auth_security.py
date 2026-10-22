from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import security_digest
from app.models.auth import LoginThrottle, RevokedToken
from app.models.base import utc_now


IDENTITY_SCOPE = "identity"
IP_SCOPE = "ip"
PASSWORD_CHANGE_SCOPE = "password_change"


@dataclass(frozen=True)
class LoginLock:
    retry_after_seconds: int
    scope: str


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def client_ip(request: Request) -> str:
    # Nao le X-Forwarded-For diretamente. Em producao, o Uvicorn deve aceitar
    # headers encaminhados apenas do IP do proxy reverso confiavel.
    return (request.client.host if request.client else "unknown")[:64]


def normalize_identifier(value: str) -> str:
    return value.strip().casefold()


def mask_identifier(value: str) -> str:
    normalized = normalize_identifier(value)[:254]
    if "@" not in normalized:
        return "***"
    local, domain = normalized.split("@", 1)
    return f"{local[:1] or '*'}***@{domain}"


def _key(scope: str, value: str) -> str:
    return security_digest(scope, value)


def _record(
    db: Session,
    scope: str,
    value: str,
    *,
    for_update: bool = False,
) -> LoginThrottle | None:
    statement = select(LoginThrottle).where(
        LoginThrottle.scope == scope,
        LoginThrottle.key_hash == _key(scope, value),
    )
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def _get_or_create(db: Session, scope: str, value: str, now: datetime) -> LoginThrottle:
    record = _record(db, scope, value, for_update=True)
    if record is not None:
        return record

    record = LoginThrottle(
        scope=scope,
        key_hash=_key(scope, value),
        failed_attempts=0,
        lock_count=0,
        window_started_at=now,
    )
    try:
        with db.begin_nested():
            db.add(record)
            db.flush()
        return record
    except IntegrityError:
        # Outra requisicao pode ter criado o mesmo contador simultaneamente.
        existing = _record(db, scope, value, for_update=True)
        if existing is None:
            raise
        return existing


def _threshold(scope: str) -> int:
    return (
        settings.login_max_attempts
        if scope == IDENTITY_SCOPE
        else settings.login_ip_max_attempts
    )


def _lock_duration_seconds(lock_count: int) -> int:
    multiplier = 2 ** max(0, lock_count - 1)
    return min(
        settings.login_lock_seconds * multiplier,
        settings.login_lock_max_seconds,
    )


def _remaining_seconds(locked_until: datetime, now: datetime) -> int:
    return max(1, math.ceil((locked_until - now).total_seconds()))


def get_login_lock(db: Session, identifier: str, ip_address: str) -> LoginLock | None:
    now = utc_now()
    active: list[LoginLock] = []
    for scope, value in (
        (IDENTITY_SCOPE, normalize_identifier(identifier)),
        (IP_SCOPE, ip_address),
    ):
        record = _record(db, scope, value)
        locked_until = as_utc(record.locked_until) if record else None
        if locked_until and locked_until > now:
            active.append(
                LoginLock(
                    retry_after_seconds=_remaining_seconds(locked_until, now),
                    scope=scope,
                )
            )
    if not active:
        return None
    return max(active, key=lambda item: item.retry_after_seconds)


def register_login_failure(
    db: Session,
    identifier: str,
    ip_address: str,
) -> LoginLock | None:
    now = utc_now()
    window = timedelta(seconds=settings.login_attempt_window_seconds)
    locks: list[LoginLock] = []

    for scope, value in (
        (IDENTITY_SCOPE, normalize_identifier(identifier)),
        (IP_SCOPE, ip_address),
    ):
        record = _get_or_create(db, scope, value, now)
        window_started = as_utc(record.window_started_at) or now
        locked_until = as_utc(record.locked_until)

        if locked_until and locked_until > now:
            locks.append(
                LoginLock(
                    retry_after_seconds=_remaining_seconds(locked_until, now),
                    scope=scope,
                )
            )
            continue

        if now - window_started > window:
            record.failed_attempts = 0
            record.lock_count = 0
            record.locked_until = None
            record.window_started_at = now
        elif locked_until and locked_until <= now:
            record.failed_attempts = 0
            record.locked_until = None

        record.failed_attempts += 1
        if record.failed_attempts >= _threshold(scope):
            record.failed_attempts = 0
            record.lock_count += 1
            duration = _lock_duration_seconds(record.lock_count)
            record.locked_until = now + timedelta(seconds=duration)
            locks.append(LoginLock(retry_after_seconds=duration, scope=scope))

    return max(locks, key=lambda item: item.retry_after_seconds) if locks else None


def get_action_lock(db: Session, scope: str, value: str) -> LoginLock | None:
    now = utc_now()
    record = _record(db, scope, value)
    locked_until = as_utc(record.locked_until) if record else None
    if not locked_until or locked_until <= now:
        return None
    return LoginLock(
        retry_after_seconds=_remaining_seconds(locked_until, now),
        scope=scope,
    )


def register_action_failure(
    db: Session,
    scope: str,
    value: str,
    *,
    threshold: int | None = None,
) -> LoginLock | None:
    """Aplica o mesmo bloqueio progressivo a operacoes de reautenticacao."""

    now = utc_now()
    window = timedelta(seconds=settings.login_attempt_window_seconds)
    record = _get_or_create(db, scope, value, now)
    window_started = as_utc(record.window_started_at) or now
    locked_until = as_utc(record.locked_until)

    if locked_until and locked_until > now:
        return LoginLock(
            retry_after_seconds=_remaining_seconds(locked_until, now),
            scope=scope,
        )

    if now - window_started > window:
        record.failed_attempts = 0
        record.lock_count = 0
        record.locked_until = None
        record.window_started_at = now
    elif locked_until and locked_until <= now:
        record.failed_attempts = 0
        record.locked_until = None

    record.failed_attempts += 1
    if record.failed_attempts < (threshold or settings.login_max_attempts):
        return None

    record.failed_attempts = 0
    record.lock_count += 1
    duration = _lock_duration_seconds(record.lock_count)
    record.locked_until = now + timedelta(seconds=duration)
    return LoginLock(retry_after_seconds=duration, scope=scope)


def clear_action_failures(db: Session, scope: str, value: str) -> None:
    db.execute(
        delete(LoginThrottle).where(
            LoginThrottle.scope == scope,
            LoginThrottle.key_hash == _key(scope, value),
        )
    )


def clear_login_failures(db: Session, identifier: str, ip_address: str) -> None:
    keys = [
        (IDENTITY_SCOPE, _key(IDENTITY_SCOPE, normalize_identifier(identifier))),
        (IP_SCOPE, _key(IP_SCOPE, ip_address)),
    ]
    for scope, key_hash in keys:
        db.execute(
            delete(LoginThrottle).where(
                LoginThrottle.scope == scope,
                LoginThrottle.key_hash == key_hash,
            )
        )


def cleanup_security_records(db: Session) -> None:
    now = utc_now()
    throttle_cutoff = now - timedelta(days=settings.login_throttle_retention_days)
    db.execute(
        delete(LoginThrottle)
        .where(LoginThrottle.updated_at < throttle_cutoff)
        .execution_options(synchronize_session=False)
    )
    db.execute(
        delete(RevokedToken)
        .where(RevokedToken.expires_at < now)
        .execution_options(synchronize_session=False)
    )
