from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.dependencies import CurrentUser, require_roles
from app.core.security import decode_access_token
from app.models.base import utc_now
from app.models.enums import DeliveryStatus, RouteStatus, UserRole
from app.models.route import Route
from app.models.tracking import TrackingPosition
from app.models.user import User
from app.schemas.tracking import (
    TrackingLiveItem,
    TrackingPositionCreate,
    TrackingPositionRead,
)
from app.services.sessions import get_active_session
from app.services.tracking_hub import tracking_manager


router = APIRouter(prefix="/tracking", tags=["Rastreamento"])
ONLINE_WINDOW_SECONDS = settings.tracking_online_seconds
TERMINAL_DELIVERY_STATUSES = {
    DeliveryStatus.DELIVERED,
    DeliveryStatus.RETURNED,
    DeliveryStatus.CANCELED,
}


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return utc_now()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _route_statement():
    return select(Route).options(
        selectinload(Route.driver),
        selectinload(Route.vehicle),
        selectinload(Route.deliveries),
    )


def _load_tracking_route(db: Session, route_id: int) -> Route:
    route = db.scalar(_route_statement().where(Route.id == route_id))
    if not route:
        raise HTTPException(status_code=404, detail="Rota nao encontrada")
    return route


def _driver_active_route(db: Session, driver_id: int) -> Route | None:
    return db.scalar(
        _route_statement()
        .where(
            Route.driver_id == driver_id,
            Route.status == RouteStatus.IN_PROGRESS,
        )
        .order_by(Route.started_at.desc(), Route.id.desc())
    )


def _latest_positions_by_route(
    db: Session, route_ids: list[int]
) -> dict[int, TrackingPosition]:
    if not route_ids:
        return {}

    latest_ids = (
        select(func.max(TrackingPosition.id).label("position_id"))
        .where(TrackingPosition.route_id.in_(route_ids))
        .group_by(TrackingPosition.route_id)
    )
    positions = list(
        db.scalars(
            select(TrackingPosition).where(TrackingPosition.id.in_(latest_ids))
        ).all()
    )
    return {position.route_id: position for position in positions}


def _live_item(route: Route, position: TrackingPosition | None) -> TrackingLiveItem:
    now = utc_now()
    received_at = position.created_at if position else None
    seconds_since_update: int | None = None
    is_online = False

    if received_at is not None:
        received_utc = _as_utc(received_at)
        seconds_since_update = max(0, int((now - received_utc).total_seconds()))
        is_online = seconds_since_update <= ONLINE_WINDOW_SECONDS

    deliveries = sorted(
        route.deliveries,
        key=lambda item: (item.sequence is None, item.sequence or 0, item.id),
    )
    completed = [
        item for item in deliveries if item.status in TERMINAL_DELIVERY_STATUSES
    ]
    next_stop = next(
        (item for item in deliveries if item.status not in TERMINAL_DELIVERY_STATUSES),
        None,
    )

    next_address = None
    if next_stop:
        city_state = "/".join(filter(None, [next_stop.city, next_stop.state]))
        next_address = " - ".join(filter(None, [next_stop.address, city_state]))

    return TrackingLiveItem(
        driver_id=route.driver_id or 0,
        driver_name=route.driver.name if route.driver else "Motorista nao informado",
        route_id=route.id,
        route_name=route.name,
        route_status=route.status,
        vehicle_id=route.vehicle_id,
        vehicle_plate=route.vehicle.plate,
        latitude=position.latitude if position else None,
        longitude=position.longitude if position else None,
        accuracy_m=position.accuracy_m if position else None,
        speed_kmh=position.speed_kmh if position else None,
        heading=position.heading if position else None,
        captured_at=position.captured_at if position else None,
        received_at=received_at,
        is_online=is_online,
        seconds_since_update=seconds_since_update,
        deliveries_total=len(deliveries),
        deliveries_completed=len(completed),
        next_stop_id=next_stop.id if next_stop else None,
        next_stop_customer=next_stop.customer_name if next_stop else None,
        next_stop_address=next_address,
    )


@router.post(
    "/positions",
    response_model=TrackingPositionRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_position(
    payload: TrackingPositionCreate,
    current_user: User = Depends(require_roles(UserRole.DRIVER)),
    db: Session = Depends(get_db),
) -> TrackingPosition:
    route = (
        _load_tracking_route(db, payload.route_id)
        if payload.route_id is not None
        else _driver_active_route(db, current_user.id)
    )

    if route is None:
        raise HTTPException(
            status_code=409,
            detail="Inicie uma rota antes de compartilhar a localizacao",
        )
    if route.driver_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Esta rota nao pertence ao motorista autenticado",
        )
    if route.status != RouteStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=409,
            detail="O rastreamento e permitido apenas com a rota em andamento",
        )

    now = utc_now()
    latest_received = db.scalar(
        select(TrackingPosition.created_at)
        .where(
            TrackingPosition.driver_id == current_user.id,
            TrackingPosition.route_id == route.id,
        )
        .order_by(TrackingPosition.created_at.desc())
        .limit(1)
    )
    if latest_received is not None:
        elapsed = (now - _as_utc(latest_received)).total_seconds()
        if elapsed < settings.tracking_min_interval_seconds:
            retry_after = max(1, int(settings.tracking_min_interval_seconds - elapsed + 0.999))
            raise HTTPException(
                status_code=429,
                detail="Envio de localizacao muito frequente",
                headers={"Retry-After": str(retry_after)},
            )

    captured_at = _as_utc(payload.captured_at)
    if captured_at > now.replace(microsecond=0) and (captured_at - now).total_seconds() > 300:
        captured_at = now
    if (now - captured_at).total_seconds() > 86400:
        raise HTTPException(
            status_code=422,
            detail="A posicao capturada nao pode ter mais de 24 horas",
        )

    position = TrackingPosition(
        driver_id=current_user.id,
        route_id=route.id,
        vehicle_id=route.vehicle_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_m=payload.accuracy_m,
        speed_kmh=payload.speed_kmh,
        heading=payload.heading,
        altitude_m=payload.altitude_m,
        captured_at=captured_at,
        source=payload.source,
    )
    db.add(position)
    db.flush()

    # Limpeza gradual para impedir crescimento ilimitado do SQLite/PostgreSQL.
    # A frequencia evita executar um DELETE em todos os envios de GPS.
    if settings.tracking_retention_days > 0 and position.id % 100 == 0:
        cutoff = utc_now() - timedelta(days=settings.tracking_retention_days)
        db.execute(
            delete(TrackingPosition).where(TrackingPosition.created_at < cutoff)
        )

    db.commit()
    db.refresh(position)

    live = _live_item(route, position)
    await tracking_manager.broadcast(
        {
            "type": "tracking.position",
            "data": jsonable_encoder(live),
        }
    )
    return position


@router.get("/live", response_model=list[TrackingLiveItem])
def list_live_tracking(
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> list[TrackingLiveItem]:
    routes = list(
        db.scalars(
            _route_statement()
            .where(Route.status == RouteStatus.IN_PROGRESS)
            .order_by(Route.started_at.desc(), Route.id.desc())
        )
        .unique()
        .all()
    )
    positions = _latest_positions_by_route(db, [route.id for route in routes])
    return [_live_item(route, positions.get(route.id)) for route in routes]


@router.get(
    "/routes/{route_id}/history",
    response_model=list[TrackingPositionRead],
)
def route_tracking_history(
    route_id: int,
    current_user: CurrentUser,
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> list[TrackingPosition]:
    route = _load_tracking_route(db, route_id)
    if current_user.role == UserRole.DRIVER and route.driver_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Esta rota nao pertence ao motorista autenticado",
        )

    if current_user.role not in {
        UserRole.ADMIN,
        UserRole.OPERATOR,
        UserRole.DRIVER,
    }:
        raise HTTPException(status_code=403, detail="Acesso negado")

    latest_first = list(
        db.scalars(
            select(TrackingPosition)
            .where(TrackingPosition.route_id == route_id)
            .order_by(TrackingPosition.captured_at.desc(), TrackingPosition.id.desc())
            .limit(limit)
        ).all()
    )
    latest_first.reverse()
    return latest_first


@router.websocket("/ws")
async def tracking_websocket(websocket: WebSocket) -> None:
    origin = (websocket.headers.get("origin") or "").rstrip("/")
    host = websocket.headers.get("host", "")
    http_scheme = "https" if websocket.url.scheme == "wss" else "http"
    same_origin = f"{http_scheme}://{host}".rstrip("/")
    allowed_origins = {same_origin, *settings.cors_origin_list}
    if settings.public_base_url:
        allowed_origins.add(settings.public_base_url.rstrip("/"))

    if (settings.is_production and not origin) or (
        origin and origin not in allowed_origins
    ):
        await websocket.close(code=4403, reason="Origem nao permitida")
        return

    token = websocket.cookies.get(settings.auth_cookie_name)
    if not token:
        await websocket.close(code=4401, reason="Sessao ausente")
        return

    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", ""))
        auth_version = int(payload.get("ver", 0))
        session_id = str(payload.get("sid", ""))
        expires_at = datetime.fromtimestamp(float(payload.get("exp")), tz=timezone.utc)
    except (TypeError, ValueError):
        await websocket.close(code=4401, reason="Sessao invalida")
        return

    def session_allowed() -> bool:
        with SessionLocal() as db:
            user = db.get(User, user_id)
            browser_session = get_active_session(db, session_id) if session_id else None
            return bool(
                user
                and user.is_active
                and user.auth_version == auth_version
                and not user.must_change_password
                and user.role in {UserRole.ADMIN, UserRole.OPERATOR}
                and browser_session
                and browser_session.user_id == user_id
            )

    if not session_allowed():
        await websocket.close(code=4403, reason="Acesso negado")
        return

    await tracking_manager.connect(websocket)
    try:
        await websocket.send_json({"type": "tracking.connected"})
        while True:
            if utc_now() >= expires_at or not session_allowed():
                await websocket.close(code=4401, reason="Sessao expirada")
                return
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=35)
            except TimeoutError:
                await websocket.close(code=4408, reason="Tempo limite excedido")
                return
            if message != "ping" or len(message) > 32:
                await websocket.close(code=4400, reason="Mensagem invalida")
                return
    except WebSocketDisconnect:
        pass
    finally:
        await tracking_manager.disconnect(websocket)

