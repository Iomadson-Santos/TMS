from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from models.delivery import DeliveryStatus


class DeliveryBase(BaseModel):
    nf_numero: str
    nf_serie: Optional[str] = "1"
    nome_fantasia: str
    cnpj_cpf: Optional[str] = None
    telefone: Optional[str] = None
    endereco: str
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    peso_kg: Optional[float] = 0
    volume_m3: Optional[float] = 0
    observacao: Optional[str] = None


class DeliveryCreate(DeliveryBase):
    pass


class DeliveryUpdate(BaseModel):
    nf_numero: Optional[str] = None
    nf_serie: Optional[str] = None
    nome_fantasia: Optional[str] = None
    cnpj_cpf: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    peso_kg: Optional[float] = None
    volume_m3: Optional[float] = None
    status: Optional[DeliveryStatus] = None
    route_id: Optional[int] = None
    observacao: Optional[str] = None


class DeliveryOut(DeliveryBase):
    id: int
    status: DeliveryStatus
    route_id: Optional[int] = None
    criado_em: datetime

    class Config:
        from_attributes = True
