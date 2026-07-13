from datetime import datetime

from pydantic import Field

from app.models import RouteStatus
from app.schemas.common import ORMModel
from app.schemas.vehicle import VehicleOut


class StopBase(ORMModel):
    endereco: str = Field(min_length=3, max_length=255)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    destinatario: str | None = None
    carga_kg: float = Field(default=0, ge=0)
    observacao: str | None = None


class StopCreate(StopBase):
    ordem: int | None = Field(default=None, ge=1)


class StopOut(StopBase):
    id: int
    route_id: int
    ordem: int
    concluida: bool


class RouteBase(ORMModel):
    nome: str = Field(min_length=2, max_length=100)
    vehicle_id: int = Field(gt=0)
    origem_lat: float = Field(ge=-90, le=90)
    origem_lng: float = Field(ge=-180, le=180)
    origem_endereco: str = Field(min_length=3, max_length=255)
    observacao: str | None = None


class RouteCreate(RouteBase):
    paradas: list[StopCreate] = Field(default_factory=list)


class RouteUpdate(ORMModel):
    nome: str | None = None
    status: RouteStatus | None = None
    distancia_km: float | None = Field(default=None, ge=0)
    tempo_estimado_min: int | None = Field(default=None, ge=0)
    observacao: str | None = None


class RouteOut(RouteBase):
    id: int
    status: RouteStatus
    distancia_km: float
    tempo_estimado_min: int
    carga_total_kg: float
    criado_em: datetime
    iniciada_em: datetime | None = None
    concluida_em: datetime | None = None
    paradas: list[StopOut] = Field(default_factory=list)
    veiculo: VehicleOut | None = None


class OtimizacaoRequest(ORMModel):
    vehicle_id: int
    origem_lat: float = Field(ge=-90, le=90)
    origem_lng: float = Field(ge=-180, le=180)
    origem_endereco: str
    paradas: list[StopCreate]
    nome_rota: str = "Rota Otimizada"


class OtimizacaoResponse(ORMModel):
    ordem_otimizada: list[StopCreate]
    distancia_total_km: float
    tempo_estimado_min: int
    economia_km: float
