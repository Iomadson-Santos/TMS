from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utc_now

if TYPE_CHECKING:
    from app.models.user import User


class LoginThrottle(TimestampMixin, Base):
    """Contador persistente para limitar tentativas de autenticacao.

    A chave e um HMAC do e-mail ou IP. O identificador original nao e armazenado.
    """

    __tablename__ = "login_throttles"
    __table_args__ = (
        UniqueConstraint("scope", "key_hash", name="uq_login_throttles_scope_key"),
        Index("ix_login_throttles_locked_until", "locked_until"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lock_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(TimestampMixin, Base):
    """Sessao de navegador associada a um refresh token opaco e rotativo.

    Somente o HMAC do segredo de refresh e persistido. Um token antigo reutilizado
    invalida a sessao, reduzindo o impacto do roubo de cookies.
    """

    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_user_active", "user_id", "revoked_at", "expires_at"),
        Index("ix_auth_sessions_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_refresh_hash: Mapped[str | None] = mapped_column(String(64))
    previous_valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent_hash: Mapped[str | None] = mapped_column(String(64))

    user: Mapped["User"] = relationship(back_populates="auth_sessions")


class RevokedToken(Base):
    """JWTs Bearer sem sessao invalidados explicitamente."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
