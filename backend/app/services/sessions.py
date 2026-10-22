from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hmac

from fastapi import Request
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    build_refresh_token,
    new_refresh_secret,
    new_session_id,
    parse_refresh_token,
    refresh_token_hash,
    security_digest,
)
from app.models.auth import AuthSession
from app.models.base import utc_now
from app.models.user import User
from app.services.auth_security import client_ip


@dataclass(frozen=True)
class BrowserSessionCreated:
    session: AuthSession
    refresh_token: str


class BrowserSessionError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _fingerprints(request: Request) -> tuple[str, str]:
    ip_hash = security_digest("session-ip", client_ip(request))
    user_agent = request.headers.get("user-agent", "unknown")[:512]
    user_agent_hash = security_digest("session-ua", user_agent)
    return ip_hash, user_agent_hash


def _idle_deadline(session: AuthSession) -> datetime | None:
    last_used = as_utc(session.last_used_at)
    if not last_used:
        return None
    return last_used + timedelta(minutes=settings.session_idle_minutes)


def is_session_active(session: AuthSession | None, now: datetime | None = None) -> bool:
    if session is None or session.revoked_at is not None:
        return False
    current = as_utc(now) or utc_now()
    expires_at = as_utc(session.expires_at)
    idle_deadline = _idle_deadline(session)
    return bool(
        expires_at
        and expires_at > current
        and idle_deadline
        and idle_deadline > current
    )


def get_active_session(db: Session, session_id: str) -> AuthSession | None:
    session = db.get(AuthSession, session_id)
    if is_session_active(session):
        return session
    if session and session.revoked_at is None:
        session.revoked_at = utc_now()
    return None


def cleanup_auth_sessions(db: Session) -> None:
    """Remove sessoes antigas sem avaliar datas no mapa de identidade do ORM."""

    stale_cutoff = utc_now() - timedelta(days=settings.session_retention_days)
    statement = delete(AuthSession).where(
        (AuthSession.expires_at < stale_cutoff)
        | (
            AuthSession.revoked_at.is_not(None)
            & (AuthSession.revoked_at < stale_cutoff)
        )
    )
    db.execute(statement.execution_options(synchronize_session=False))


def _enforce_session_limit(db: Session, user_id: int, now: datetime) -> None:
    active = list(
        db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .order_by(AuthSession.last_used_at.asc(), AuthSession.created_at.asc())
            .with_for_update()
        ).all()
    )
    active = [item for item in active if is_session_active(item, now)]
    overflow = len(active) - settings.max_active_sessions_per_user + 1
    for session in active[: max(0, overflow)]:
        session.revoked_at = now


def create_browser_session(
    db: Session,
    user: User,
    request: Request,
) -> BrowserSessionCreated:
    now = utc_now()
    cleanup_auth_sessions(db)
    _enforce_session_limit(db, user.id, now)

    session_id = new_session_id()
    secret = new_refresh_secret()
    ip_hash, user_agent_hash = _fingerprints(request)
    session = AuthSession(
        id=session_id,
        user_id=user.id,
        refresh_hash=refresh_token_hash(session_id, secret),
        previous_refresh_hash=None,
        previous_valid_until=None,
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        last_used_at=now,
        revoked_at=None,
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
    )
    db.add(session)
    db.flush()
    return BrowserSessionCreated(
        session=session,
        refresh_token=build_refresh_token(session_id, secret),
    )


def rotate_browser_session(
    db: Session,
    raw_refresh_token: str | None,
    request: Request,
) -> BrowserSessionCreated:
    parsed = parse_refresh_token(raw_refresh_token)
    if parsed is None:
        raise BrowserSessionError("invalid")

    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.id == parsed.session_id)
        .with_for_update()
    )
    now = utc_now()
    if session is None:
        raise BrowserSessionError("invalid")
    if session.revoked_at is not None:
        raise BrowserSessionError("revoked")

    expires_at = as_utc(session.expires_at)
    if not expires_at or expires_at <= now:
        session.revoked_at = now
        raise BrowserSessionError("expired")

    idle_deadline = _idle_deadline(session)
    if not idle_deadline or idle_deadline <= now:
        session.revoked_at = now
        raise BrowserSessionError("idle")

    presented_hash = refresh_token_hash(parsed.session_id, parsed.secret)
    current_match = hmac.compare_digest(presented_hash, session.refresh_hash)
    previous_valid_until = as_utc(session.previous_valid_until)
    previous_match = bool(
        session.previous_refresh_hash
        and previous_valid_until
        and previous_valid_until > now
        and hmac.compare_digest(presented_hash, session.previous_refresh_hash)
    )
    if previous_match:
        # Outra aba pode ter concluido a rotacao milissegundos antes. O token
        # anterior nunca recebe uma nova credencial: o cliente deve reutilizar os
        # cookies atuais do navegador. Fora da janela, a reutilizacao revoga a
        # familia inteira como possivel roubo de refresh token.
        raise BrowserSessionError("stale")
    if not current_match:
        session.revoked_at = now
        raise BrowserSessionError("reuse")

    new_secret = new_refresh_secret()
    session.previous_refresh_hash = session.refresh_hash
    session.previous_valid_until = now + timedelta(
        seconds=settings.refresh_rotation_grace_seconds
    )
    session.refresh_hash = refresh_token_hash(session.id, new_secret)
    session.last_used_at = now
    session.ip_hash, session.user_agent_hash = _fingerprints(request)
    db.flush()
    return BrowserSessionCreated(
        session=session,
        refresh_token=build_refresh_token(session.id, new_secret),
    )


def revoke_session(db: Session, session_id: str | None) -> None:
    if not session_id:
        return
    session = db.get(AuthSession, session_id)
    if session and session.revoked_at is None:
        session.revoked_at = utc_now()


def revoke_user_sessions(
    db: Session,
    user_id: int,
    *,
    except_session_id: str | None = None,
) -> int:
    statement = (
        update(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=utc_now())
    )
    if except_session_id:
        statement = statement.where(AuthSession.id != except_session_id)
    result = db.execute(statement.execution_options(synchronize_session=False))
    return int(result.rowcount or 0)


def list_user_sessions(db: Session, user_id: int) -> list[AuthSession]:
    now = utc_now()
    candidates = list(
        db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .order_by(AuthSession.last_used_at.desc())
        ).all()
    )
    active: list[AuthSession] = []
    for session in candidates:
        if is_session_active(session, now):
            active.append(session)
        else:
            session.revoked_at = now
    return active
