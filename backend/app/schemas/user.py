from datetime import datetime

from pydantic import EmailStr, Field, field_validator, model_validator

from app.core.security import validate_password_policy
from app.models.enums import UserRole
from app.schemas.base import ORMModel


class UserCreate(ORMModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.OPERATOR
    is_active: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_password(self):
        validate_password_policy(
            self.password,
            email=str(self.email),
            name=self.name,
        )
        return self


class UserUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().casefold() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_update(self):
        required_when_present = {"name", "email", "role", "is_active"}
        for field in required_when_present.intersection(self.model_fields_set):
            if getattr(self, field) is None:
                raise ValueError(f"{field} nao pode ser nulo")

        if self.password is not None:
            if not self.password:
                raise ValueError("password nao pode ser vazio")
            validate_password_policy(
                self.password,
                email=str(self.email) if self.email else None,
                name=self.name,
            )
        return self


class UserRead(ORMModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime


class DriverOption(ORMModel):
    """Dados minimos usados no seletor de motorista da tela de rotas."""

    id: int
    name: str
