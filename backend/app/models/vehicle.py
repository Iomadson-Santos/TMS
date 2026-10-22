from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Enum as SAEnum, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import VehicleStatus


class Vehicle(TimestampMixin, Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    brand: Mapped[str | None] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer)
    capacity_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    capacity_m3: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    current_km: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[VehicleStatus] = mapped_column(
        SAEnum(
            VehicleStatus,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            validate_strings=True,
            name="vehicle_status",
        ),
        default=VehicleStatus.AVAILABLE,
        nullable=False,
        index=True,
    )

    routes: Mapped[list["Route"]] = relationship(back_populates="vehicle")
    tracking_positions: Mapped[list["TrackingPosition"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
