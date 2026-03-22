from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from models import RouteStatus, VehicleStatus


class VehicleBase(BaseModel):
    placa: str
    modelo: str
    tipo: str
    capacidade_kg: float
    motorista: Optional[str] = None
    telefone_motorista: Optional[str] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    modelo: Optional[str] = None
    tipo: Optional[str] = None
    capacidade_kg: Optional[float] = None
    status: Optional[VehicleStatus] = None
    motorista: Optional[str] = None
    telefone_motorista: Optional[str] = None
    lat_atual: Optional[float] = None
    lng_atual: Optional[float] = None


class VehicleOut(VehicleBase):
    id: int
    status: VehicleStatus
    lat_atual: float
    lng_atual: float
    criado_em: datetime

    class Config:
        from_attributes = True


class StopBase(BaseModel):
    endereco: str
    lat: float
    lng: float
    destinatario: Optional[str] = None
    carga_kg: float = 0
    observacao: Optional[str] = None


class StopCreate(StopBase):
    ordem: Optional[int] = None


class StopOut(StopBase):
    id: int
    route_id: int
    ordem: int
    concluida: bool

    class Config:
        from_attributes = True


class RouteBase(BaseModel):
    nome: str
    vehicle_id: int
    origem_lat: float
    origem_lng: float
    origem_endereco: str
    observacao: Optional[str] = None


class RouteCreate(RouteBase):
    paradas: List[StopCreate] = Field(default_factory=list)


class RouteUpdate(BaseModel):
    nome: Optional[str] = None
    status: Optional[RouteStatus] = None
    distancia_km: Optional[float] = None
    tempo_estimado_min: Optional[int] = None
    observacao: Optional[str] = None


class RouteOut(RouteBase):
    id: int
    status: RouteStatus
    distancia_km: float
    tempo_estimado_min: int
    carga_total_kg: float
    criado_em: datetime
    iniciada_em: Optional[datetime] = None
    concluida_em: Optional[datetime] = None
    paradas: List[StopOut] = Field(default_factory=list)
    veiculo: Optional[VehicleOut] = None

    class Config:
        from_attributes = True


class TrackingCreate(BaseModel):
    vehicle_id: int
    route_id: Optional[int] = None
    lat: float
    lng: float
    velocidade_kmh: float = 0


class TrackingOut(TrackingCreate):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class OtimizacaoRequest(BaseModel):
    vehicle_id: int
    origem_lat: float
    origem_lng: float
    origem_endereco: str
    paradas: List[StopCreate]
    nome_rota: str = "Rota Otimizada"


class OtimizacaoResponse(BaseModel):
    ordem_otimizada: List[StopCreate]
    distancia_total_km: float
    tempo_estimado_min: int
    economia_km: float