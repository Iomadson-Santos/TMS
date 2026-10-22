from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utc_now


class TrackingPosition(TimestampMixin, Base):
    """Ponto de geolocalizacao enviado pelo aplicativo do motorista."""

    __tablename__ = "tracking_positions"
    __table_args__ = (
        Index("ix_tracking_positions_route_created", "route_id", "created_at"),
        Index("ix_tracking_positions_driver_created", "driver_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    route_id: Mapped[int] = mapped_column(
        ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy_m: Mapped[float | None] = mapped_column(Float)
    speed_kmh: Mapped[float | None] = mapped_column(Float)
    heading: Mapped[float | None] = mapped_column(Float)
    altitude_m: Mapped[float | None] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(
        String(30), default="mobile_web", nullable=False
    )

    driver: Mapped["User"] = relationship(back_populates="tracking_positions")
    route: Mapped["Route"] = relationship(back_populates="tracking_positions")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="tracking_positions")
