from datetime import datetime

from pydantic import Field, field_validator

from app.models import VehicleStatus
from app.schemas.common import ORMModel


class VehicleBase(ORMModel):
    placa: str = Field(min_length=7, max_length=10)
    modelo: str = Field(min_length=2, max_length=100)
    tipo: str = Field(min_length=2, max_length=50)
    capacidade_kg: float = Field(gt=0)
    motorista: str | None = None
    telefone_motorista: str | None = None

    @field_validator("placa")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        return value.strip().upper().replace("-", "")


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(ORMModel):
    modelo: str | None = None
    tipo: str | None = None
    capacidade_kg: float | None = Field(default=None, gt=0)
    status: VehicleStatus | None = None
    motorista: str | None = None
    telefone_motorista: str | None = None
    lat_atual: float | None = Field(default=None, ge=-90, le=90)
    lng_atual: float | None = Field(default=None, ge=-180, le=180)


class VehicleOut(VehicleBase):
    id: int
    status: VehicleStatus
    lat_atual: float
    lng_atual: float
    criado_em: datetime
