from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.models.enums import VehicleStatus
from app.schemas.base import ORMModel


class VehicleBase(ORMModel):
    plate: str = Field(min_length=7, max_length=10)
    brand: str | None = Field(default=None, max_length=80)
    model: str = Field(min_length=2, max_length=120)
    year: int | None = Field(default=None, ge=1950, le=2100)
    capacity_kg: Decimal | None = Field(default=None, ge=0, le=9_999_999_999)
    capacity_m3: Decimal | None = Field(default=None, ge=0, le=9_999_999)
    current_km: int = Field(default=0, ge=0, le=2_000_000_000)
    status: VehicleStatus = VehicleStatus.AVAILABLE

    @field_validator("plate", mode="before")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        return value.strip().upper().replace("-", "") if isinstance(value, str) else value

    @field_validator("brand", "model", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(ORMModel):
    plate: str | None = Field(default=None, min_length=7, max_length=10)
    brand: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, min_length=2, max_length=120)
    year: int | None = Field(default=None, ge=1950, le=2100)
    capacity_kg: Decimal | None = Field(default=None, ge=0, le=9_999_999_999)
    capacity_m3: Decimal | None = Field(default=None, ge=0, le=9_999_999)
    current_km: int | None = Field(default=None, ge=0, le=2_000_000_000)
    status: VehicleStatus | None = None

    @field_validator("plate", mode="before")
    @classmethod
    def normalize_plate(cls, value: str | None) -> str | None:
        return value.strip().upper().replace("-", "") if isinstance(value, str) else value

    @field_validator("brand", "model", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required = {"plate", "model", "current_km", "status"}
        for field in required.intersection(self.model_fields_set):
            if getattr(self, field) is None:
                raise ValueError(f"{field} nao pode ser nulo")
        return self


class VehicleRead(VehicleBase):
    id: int
    created_at: datetime
    updated_at: datetime
