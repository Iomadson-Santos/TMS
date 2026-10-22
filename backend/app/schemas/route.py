from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.models.enums import RouteStatus
from app.schemas.base import ORMModel
from app.schemas.delivery import DeliveryRead
from app.schemas.user import UserRead
from app.schemas.vehicle import VehicleRead


class RouteCreate(ORMModel):
    name: str = Field(min_length=2, max_length=140)
    vehicle_id: int = Field(gt=0)
    driver_id: int | None = Field(default=None, gt=0)
    scheduled_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    delivery_ids: list[int] = Field(default_factory=list, max_length=500)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("notes", mode="before")
    @classmethod
    def strip_notes(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("delivery_ids")
    @classmethod
    def validate_delivery_ids(cls, values: list[int]) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("delivery_ids deve conter apenas IDs positivos")
        return values


class RouteUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=2, max_length=140)
    vehicle_id: int | None = Field(default=None, gt=0)
    driver_id: int | None = Field(default=None, gt=0)
    scheduled_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    distance_km: Decimal | None = Field(default=None, ge=0, le=9_999_999_999)
    estimated_minutes: int | None = Field(default=None, ge=0, le=10_000_000)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("notes", mode="before")
    @classmethod
    def strip_notes(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field in {"name", "vehicle_id"}.intersection(self.model_fields_set):
            if getattr(self, field) is None:
                raise ValueError(f"{field} nao pode ser nulo")
        return self


class RouteStatusUpdate(ORMModel):
    status: RouteStatus


class RouteRead(ORMModel):
    id: int
    name: str
    vehicle_id: int
    driver_id: int | None
    created_by_id: int
    status: RouteStatus
    scheduled_date: date | None
    notes: str | None
    distance_km: Decimal | None
    estimated_minutes: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    vehicle: VehicleRead
    driver: UserRead | None
    deliveries: list[DeliveryRead]


class OptimizeRequest(ORMModel):
    delivery_ids: list[int] = Field(min_length=1, max_length=500)

    @field_validator("delivery_ids")
    @classmethod
    def validate_delivery_ids(cls, values: list[int]) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("delivery_ids deve conter apenas IDs positivos")
        return values


class OptimizeResult(ORMModel):
    ordered_delivery_ids: list[int]
    distance_km: float
    missing_coordinates: list[int]
