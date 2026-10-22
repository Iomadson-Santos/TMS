from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.models.enums import DeliveryStatus
from app.schemas.base import ORMModel


class DeliveryBase(ORMModel):
    invoice_number: str = Field(min_length=1, max_length=60)
    customer_name: str = Field(min_length=2, max_length=180)
    customer_document: str | None = Field(default=None, max_length=30)
    address: str = Field(min_length=4, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=2)
    postal_code: str | None = Field(default=None, max_length=12)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    weight_kg: Decimal | None = Field(default=None, ge=0, le=9_999_999_999)
    volume_m3: Decimal | None = Field(default=None, ge=0, le=9_999_999)
    invoice_value: Decimal | None = Field(default=None, ge=0, le=999_999_999_999)
    freight_value: Decimal | None = Field(default=None, ge=0, le=999_999_999_999)
    status: DeliveryStatus = DeliveryStatus.PENDING

    @field_validator("invoice_number", "customer_name", "address", "city", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("customer_document", "postal_code", mode="before")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("state", mode="before")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        return value.strip().upper() if isinstance(value, str) else value


class DeliveryCreate(DeliveryBase):
    pass


class DeliveryUpdate(ORMModel):
    invoice_number: str | None = Field(default=None, min_length=1, max_length=60)
    customer_name: str | None = Field(default=None, min_length=2, max_length=180)
    customer_document: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, min_length=4, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    postal_code: str | None = Field(default=None, max_length=12)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    weight_kg: Decimal | None = Field(default=None, ge=0, le=9_999_999_999)
    volume_m3: Decimal | None = Field(default=None, ge=0, le=9_999_999)
    invoice_value: Decimal | None = Field(default=None, ge=0, le=999_999_999_999)
    freight_value: Decimal | None = Field(default=None, ge=0, le=999_999_999_999)
    status: DeliveryStatus | None = None

    @field_validator("invoice_number", "customer_name", "address", "city", mode="before")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("customer_document", "postal_code", mode="before")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("state", mode="before")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required = {
            "invoice_number",
            "customer_name",
            "address",
            "city",
            "state",
            "status",
        }
        for field in required.intersection(self.model_fields_set):
            if getattr(self, field) is None:
                raise ValueError(f"{field} nao pode ser nulo")
        return self


class DeliveryRead(DeliveryBase):
    id: int
    route_id: int | None
    sequence: int | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime
