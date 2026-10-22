from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import DeliveryStatus

if TYPE_CHECKING:
    from app.models.route import Route


class Delivery(TimestampMixin, Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    customer_document: Mapped[str | None] = mapped_column(String(30), index=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(2), index=True, nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(12))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    volume_m3: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    invoice_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    freight_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    status: Mapped[DeliveryStatus] = mapped_column(
        SAEnum(
            DeliveryStatus,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            validate_strings=True,
            name="delivery_status",
        ),
        default=DeliveryStatus.PENDING,
        nullable=False,
        index=True,
    )
    route_id: Mapped[int | None] = mapped_column(
        ForeignKey("routes.id"), nullable=True, index=True
    )
    sequence: Mapped[int | None] = mapped_column(Integer)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    route: Mapped["Route | None"] = relationship(back_populates="deliveries")
