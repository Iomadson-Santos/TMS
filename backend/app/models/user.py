from __future__ import annotations

from sqlalchemy import Boolean, Enum as SAEnum, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import UserRole


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    __table_args__ = (Index("uq_users_email_lower", func.lower(email), unique=True),)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            validate_strings=True,
            name="user_role",
        ),
        default=UserRole.OPERATOR,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auth_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    driven_routes: Mapped[list["Route"]] = relationship(
        back_populates="driver", foreign_keys="Route.driver_id"
    )
    created_routes: Mapped[list["Route"]] = relationship(
        back_populates="created_by", foreign_keys="Route.created_by_id"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    tracking_positions: Mapped[list["TrackingPosition"]] = relationship(
        back_populates="driver", cascade="all, delete-orphan"
    )
    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
