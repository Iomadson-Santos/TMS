from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import RouteStatus

if TYPE_CHECKING:
    from app.models.delivery import Delivery
    from app.models.tracking import TrackingPosition
    from app.models.user import User
    from app.models.vehicle import Vehicle


class Route(TimestampMixin, Base):
    __tablename__ = "routes"
    __table_args__ = (
        Index(
            "uq_routes_driver_in_progress",
            "driver_id",
            unique=True,
            sqlite_where=text("status = 'em_andamento' AND driver_id IS NOT NULL"),
            postgresql_where=text("status = 'em_andamento' AND driver_id IS NOT NULL"),
        ),
        Index(
            "uq_routes_vehicle_in_progress",
            "vehicle_id",
            unique=True,
            sqlite_where=text("status = 'em_andamento'"),
            postgresql_where=text("status = 'em_andamento'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[RouteStatus] = mapped_column(
        SAEnum(
            RouteStatus,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            validate_strings=True,
            name="route_status",
        ),
        default=RouteStatus.OPEN,
        nullable=False,
        index=True,
    )
    scheduled_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    vehicle: Mapped["Vehicle"] = relationship(back_populates="routes")
    driver: Mapped["User | None"] = relationship(
        back_populates="driven_routes", foreign_keys=[driver_id]
    )
    created_by: Mapped["User"] = relationship(
        back_populates="created_routes", foreign_keys=[created_by_id]
    )
    deliveries: Mapped[list["Delivery"]] = relationship(
        back_populates="route", order_by="Delivery.sequence"
    )
    tracking_positions: Mapped[list["TrackingPosition"]] = relationship(
        back_populates="route", cascade="all, delete-orphan"
    )
