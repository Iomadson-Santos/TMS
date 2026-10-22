from datetime import datetime

from pydantic import Field

from app.models.enums import RouteStatus
from app.schemas.base import ORMModel


class TrackingPositionCreate(ORMModel):
    route_id: int | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=100000)
    speed_kmh: float | None = Field(default=None, ge=0, le=500)
    heading: float | None = Field(default=None, ge=0, le=360)
    altitude_m: float | None = Field(default=None, ge=-1000, le=20000)
    captured_at: datetime | None = None
    source: str = Field(default="mobile_web", min_length=2, max_length=30)


class TrackingPositionRead(ORMModel):
    id: int
    driver_id: int
    route_id: int
    vehicle_id: int
    latitude: float
    longitude: float
    accuracy_m: float | None
    speed_kmh: float | None
    heading: float | None
    altitude_m: float | None
    captured_at: datetime
    source: str
    created_at: datetime


class TrackingLiveItem(ORMModel):
    driver_id: int
    driver_name: str
    route_id: int
    route_name: str
    route_status: RouteStatus
    vehicle_id: int
    vehicle_plate: str
    latitude: float | None = None
    longitude: float | None = None
    accuracy_m: float | None = None
    speed_kmh: float | None = None
    heading: float | None = None
    captured_at: datetime | None = None
    received_at: datetime | None = None
    is_online: bool = False
    seconds_since_update: int | None = None
    deliveries_total: int = 0
    deliveries_completed: int = 0
    next_stop_id: int | None = None
    next_stop_customer: str | None = None
    next_stop_address: str | None = None
