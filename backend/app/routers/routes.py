from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_roles
from app.models.base import utc_now
from app.models.delivery import Delivery
from app.models.enums import (
    DeliveryStatus,
    RouteStatus,
    UserRole,
    VehicleStatus,
)
from app.models.route import Route
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.route import (
    OptimizeRequest,
    OptimizeResult,
    RouteCreate,
    RouteRead,
    RouteStatusUpdate,
    RouteUpdate,
)
from app.services.audit import register_audit
from app.services.auth_security import client_ip
from app.services.routing import optimize_deliveries


router = APIRouter(prefix="/routes", tags=["Rotas"])


def route_statement():
    return select(Route).options(
        selectinload(Route.vehicle),
        selectinload(Route.driver),
        selectinload(Route.created_by),
        selectinload(Route.deliveries),
    )


def load_route(db: Session, route_id: int) -> Route:
    route = db.scalar(route_statement().where(Route.id == route_id))
    if not route:
        raise HTTPException(status_code=404, detail="Rota nao encontrada")
    return route


def validate_driver(db: Session, driver_id: int | None) -> User | None:
    if driver_id is None:
        return None
    driver = db.get(User, driver_id)
    if not driver or driver.role != UserRole.DRIVER or not driver.is_active:
        raise HTTPException(status_code=400, detail="Motorista invalido ou inativo")
    return driver


def find_active_route_conflict(
    db: Session,
    *,
    driver_id: int | None = None,
    vehicle_id: int | None = None,
    exclude_route_id: int | None = None,
) -> Route | None:
    statement = select(Route).where(Route.status == RouteStatus.IN_PROGRESS)
    if exclude_route_id is not None:
        statement = statement.where(Route.id != exclude_route_id)
    if driver_id is not None:
        statement = statement.where(Route.driver_id == driver_id)
    if vehicle_id is not None:
        statement = statement.where(Route.vehicle_id == vehicle_id)
    return db.scalar(statement.order_by(Route.started_at.desc(), Route.id.desc()))


def validate_vehicle(db: Session, vehicle_id: int, current_route_id: int | None = None) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Veiculo nao encontrado")
    if vehicle.status != VehicleStatus.AVAILABLE:
        current = db.scalar(
            select(Route).where(
                Route.vehicle_id == vehicle.id,
                Route.id != current_route_id,
                Route.status == RouteStatus.IN_PROGRESS,
            )
        )
        if current:
            raise HTTPException(status_code=409, detail="Veiculo ja esta em outra rota")
        raise HTTPException(status_code=409, detail="Veiculo indisponivel")
    return vehicle


@router.get("", response_model=list[RouteRead])
def list_routes(
    current_user: CurrentUser,
    search: str | None = Query(default=None, max_length=100),
    route_status: RouteStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[Route]:
    statement = route_statement().order_by(Route.created_at.desc())
    if current_user.role == UserRole.DRIVER:
        statement = statement.where(Route.driver_id == current_user.id)

    if search:
        term = f"%{search.strip()}%"
        statement = (
            statement.join(Vehicle, Route.vehicle_id == Vehicle.id)
            .outerjoin(User, Route.driver_id == User.id)
            .where(
                or_(
                    Route.name.ilike(term),
                    Vehicle.plate.ilike(term),
                    User.name.ilike(term),
                )
            )
        )
    if route_status is not None:
        statement = statement.where(Route.status == route_status)

    return list(db.scalars(statement).unique().all())


@router.post("", response_model=RouteRead, status_code=status.HTTP_201_CREATED)
def create_route(
    payload: RouteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Route:
    validate_vehicle(db, payload.vehicle_id)
    validate_driver(db, payload.driver_id)

    ordered_ids = list(dict.fromkeys(payload.delivery_ids))
    deliveries: list[Delivery] = []
    if ordered_ids:
        found = list(db.scalars(select(Delivery).where(Delivery.id.in_(ordered_ids))).all())
        by_id = {item.id: item for item in found}
        missing = [item_id for item_id in ordered_ids if item_id not in by_id]
        if missing:
            raise HTTPException(status_code=404, detail=f"Entregas inexistentes: {missing}")
        deliveries = [by_id[item_id] for item_id in ordered_ids]
        assigned = [item.id for item in deliveries if item.route_id is not None]
        if assigned:
            raise HTTPException(
                status_code=409,
                detail=f"Entregas ja vinculadas a rota: {assigned}",
            )

    route = Route(
        name=payload.name.strip(),
        vehicle_id=payload.vehicle_id,
        driver_id=payload.driver_id,
        created_by_id=current_user.id,
        scheduled_date=payload.scheduled_date,
        notes=payload.notes,
        status=RouteStatus.OPEN,
    )
    db.add(route)
    db.flush()

    for index, delivery in enumerate(deliveries, start=1):
        delivery.route_id = route.id
        delivery.sequence = index

    register_audit(
        db,
        user_id=current_user.id,
        action="create",
        entity_type="route",
        entity_id=route.id,
        details={
            "name": route.name,
            "vehicle_id": route.vehicle_id,
            "driver_id": route.driver_id,
            "delivery_ids": ordered_ids,
        },
        ip_address=client_ip(request),
    )
    db.commit()
    return load_route(db, route.id)


@router.post("/optimize", response_model=OptimizeResult)
def optimize_new_route(
    payload: OptimizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> OptimizeResult:
    del current_user
    ids = list(dict.fromkeys(payload.delivery_ids))
    found = list(db.scalars(select(Delivery).where(Delivery.id.in_(ids))).all())
    by_id = {item.id: item for item in found}
    missing_records = [item_id for item_id in ids if item_id not in by_id]
    if missing_records:
        raise HTTPException(status_code=404, detail=f"Entregas inexistentes: {missing_records}")

    ordered, distance, missing_coordinates = optimize_deliveries(
        [by_id[item_id] for item_id in ids]
    )
    return OptimizeResult(
        ordered_delivery_ids=[item.id for item in ordered],
        distance_km=distance,
        missing_coordinates=missing_coordinates,
    )


@router.post("/otimizar", response_model=OptimizeResult, include_in_schema=False)
def optimize_legacy(
    payload: OptimizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> OptimizeResult:
    return optimize_new_route(payload, db, current_user)


@router.get("/{route_id}", response_model=RouteRead)
def get_route(
    route_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Route:
    route = load_route(db, route_id)
    if current_user.role == UserRole.DRIVER and route.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Esta rota nao pertence ao motorista")
    return route


@router.patch("/{route_id}", response_model=RouteRead)
def update_route(
    route_id: int,
    payload: RouteUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Route:
    route = load_route(db, route_id)
    if route.status != RouteStatus.OPEN:
        raise HTTPException(status_code=409, detail="Somente rotas abertas podem ser editadas")

    changes = payload.model_dump(exclude_unset=True)
    if "vehicle_id" in changes and changes["vehicle_id"] is not None:
        validate_vehicle(db, changes["vehicle_id"], current_route_id=route.id)
    if "driver_id" in changes:
        validate_driver(db, changes["driver_id"])

    for field, value in changes.items():
        setattr(route, field, value)

    register_audit(
        db,
        user_id=current_user.id,
        action="update",
        entity_type="route",
        entity_id=route.id,
        details={"fields": sorted(changes.keys())},
        ip_address=client_ip(request),
    )
    db.commit()
    return load_route(db, route.id)


@router.patch("/{route_id}/status", response_model=RouteRead)
def change_route_status(
    route_id: int,
    payload: RouteStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.DRIVER)
    ),
) -> Route:
    route = load_route(db, route_id)
    old_status = route.status

    if current_user.role == UserRole.DRIVER:
        if route.driver_id != current_user.id:
            raise HTTPException(status_code=403, detail="Esta rota nao pertence ao motorista")
        if payload.status not in {RouteStatus.IN_PROGRESS, RouteStatus.COMPLETED}:
            raise HTTPException(
                status_code=403,
                detail="O motorista pode apenas iniciar ou concluir a propria rota",
            )

    # A mesma requisicao pode chegar duas vezes por clique duplo ou rede lenta.
    # Tornar a operacao idempotente evita um 409 quando a rota ja esta no
    # status solicitado e, principalmente, nao reinicia os horarios.
    if payload.status == old_status:
        return route

    allowed: dict[RouteStatus, set[RouteStatus]] = {
        RouteStatus.OPEN: {RouteStatus.IN_PROGRESS, RouteStatus.CANCELED},
        RouteStatus.IN_PROGRESS: {RouteStatus.COMPLETED, RouteStatus.CANCELED},
        RouteStatus.COMPLETED: set(),
        RouteStatus.CANCELED: set(),
    }
    if payload.status not in allowed[old_status]:
        raise HTTPException(
            status_code=409,
            detail=f"Transicao invalida: {old_status.value} para {payload.status.value}",
        )

    if payload.status == RouteStatus.IN_PROGRESS:
        if route.driver_id is None:
            raise HTTPException(
                status_code=409,
                detail="Atribua um motorista antes de iniciar a rota",
            )

        driver_conflict = find_active_route_conflict(
            db,
            driver_id=route.driver_id,
            exclude_route_id=route.id,
        )
        if driver_conflict:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"O motorista ja possui a rota #{driver_conflict.id} "
                    f"({driver_conflict.name}) em andamento"
                ),
            )

        vehicle_conflict = find_active_route_conflict(
            db,
            vehicle_id=route.vehicle_id,
            exclude_route_id=route.id,
        )
        if vehicle_conflict:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"O veiculo ja esta na rota #{vehicle_conflict.id} "
                    f"({vehicle_conflict.name})"
                ),
            )

        if route.vehicle.status not in {VehicleStatus.AVAILABLE, VehicleStatus.IN_ROUTE}:
            raise HTTPException(status_code=409, detail="Veiculo indisponivel")
        route.started_at = utc_now()
        route.vehicle.status = VehicleStatus.IN_ROUTE
        for delivery in route.deliveries:
            if delivery.status in {
                DeliveryStatus.RECEIVED,
                DeliveryStatus.SEPARATED,
                DeliveryStatus.INVOICED,
                DeliveryStatus.PENDING,
            }:
                delivery.status = DeliveryStatus.IN_ROUTE

    elif payload.status == RouteStatus.COMPLETED:
        terminal = {
            DeliveryStatus.DELIVERED,
            DeliveryStatus.RETURNED,
            DeliveryStatus.CANCELED,
        }
        unfinished = [
            delivery.id for delivery in route.deliveries if delivery.status not in terminal
        ]
        if unfinished:
            raise HTTPException(
                status_code=409,
                detail=f"Finalize todas as entregas antes de concluir a rota: {unfinished}",
            )
        route.completed_at = utc_now()
        route.vehicle.status = VehicleStatus.AVAILABLE

    elif payload.status == RouteStatus.CANCELED:
        route.vehicle.status = VehicleStatus.AVAILABLE
        terminal = {
            DeliveryStatus.DELIVERED,
            DeliveryStatus.RETURNED,
            DeliveryStatus.CANCELED,
        }
        for delivery in route.deliveries:
            if old_status == RouteStatus.OPEN or delivery.status not in terminal:
                if delivery.status == DeliveryStatus.IN_ROUTE:
                    delivery.status = DeliveryStatus.PENDING
                delivery.route_id = None
                delivery.sequence = None

    route.status = payload.status
    register_audit(
        db,
        user_id=current_user.id,
        action="status_change",
        entity_type="route",
        entity_id=route.id,
        details={"from": old_status.value, "to": route.status.value},
        ip_address=client_ip(request),
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="O motorista ou o veiculo ja possui outra rota em andamento",
        ) from exc
    return load_route(db, route.id)


@router.post("/{route_id}/optimize", response_model=RouteRead)
def optimize_existing_route(
    route_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Route:
    route = load_route(db, route_id)
    if route.status != RouteStatus.OPEN:
        raise HTTPException(status_code=409, detail="Somente rotas abertas podem ser otimizadas")
    if not route.deliveries:
        raise HTTPException(status_code=400, detail="A rota nao possui entregas")

    ordered, distance, missing_coordinates = optimize_deliveries(list(route.deliveries))
    for index, delivery in enumerate(ordered, start=1):
        delivery.sequence = index
    route.distance_km = Decimal(str(distance))

    register_audit(
        db,
        user_id=current_user.id,
        action="optimize",
        entity_type="route",
        entity_id=route.id,
        details={
            "ordered_delivery_ids": [item.id for item in ordered],
            "missing_coordinates": missing_coordinates,
            "distance_km": distance,
        },
        ip_address=client_ip(request),
    )
    db.commit()
    return load_route(db, route.id)


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    route = load_route(db, route_id)
    if route.status not in {RouteStatus.OPEN, RouteStatus.CANCELED}:
        raise HTTPException(status_code=409, detail="A rota nao pode ser excluida neste status")
    if route.started_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Rotas que ja foram iniciadas devem permanecer no historico",
        )

    for delivery in route.deliveries:
        delivery.route_id = None
        delivery.sequence = None

    register_audit(
        db,
        user_id=current_user.id,
        action="delete",
        entity_type="route",
        entity_id=route.id,
        details={"name": route.name},
        ip_address=client_ip(request),
    )
    db.delete(route)
    db.commit()
