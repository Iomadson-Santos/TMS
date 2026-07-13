from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMModel


class TrackingCreate(ORMModel):
    vehicle_id: int = Field(gt=0)
    route_id: int | None = Field(default=None, gt=0)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    velocidade_kmh: float = Field(default=0, ge=0)


class TrackingOut(TrackingCreate):
    id: int
    timestamp: datetime
