from datetime import datetime

from pydantic import Field

from app.models import DeliveryStatus
from app.schemas.common import ORMModel


class DeliveryBase(ORMModel):
    nf_numero: str = Field(min_length=1, max_length=20)
    nf_serie: str = "1"
    nome_fantasia: str = Field(min_length=2, max_length=150)
    cnpj_cpf: str | None = None
    telefone: str | None = None
    endereco: str = Field(min_length=3, max_length=255)
    cidade: str | None = None
    estado: str | None = Field(default=None, min_length=2, max_length=2)
    cep: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    peso_kg: float = Field(default=0, ge=0)
    volume_m3: float = Field(default=0, ge=0)
    observacao: str | None = None


class DeliveryCreate(DeliveryBase):
    pass


class DeliveryUpdate(ORMModel):
    nf_numero: str | None = None
    nf_serie: str | None = None
    nome_fantasia: str | None = None
    cnpj_cpf: str | None = None
    telefone: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = None
    cep: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    peso_kg: float | None = Field(default=None, ge=0)
    volume_m3: float | None = Field(default=None, ge=0)
    status: DeliveryStatus | None = None
    route_id: int | None = None
    observacao: str | None = None


class DeliveryOut(DeliveryBase):
    id: int
    status: DeliveryStatus
    route_id: int | None = None
    criado_em: datetime
    atualizado_em: datetime | None = None
