from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_roles
from app.models.base import utc_now
from app.models.delivery import Delivery
from app.models.enums import DeliveryStatus, RouteStatus, UserRole
from app.models.route import Route
from app.models.user import User
from app.schemas.delivery import DeliveryCreate, DeliveryRead, DeliveryUpdate
from app.services.audit import register_audit
from app.services.auth_security import client_ip


router = APIRouter(prefix="/deliveries", tags=["Entregas"])


@router.get("", response_model=list[DeliveryRead])
def list_deliveries(
    current_user: CurrentUser,
    search: str | None = Query(default=None, max_length=100),
    delivery_status: DeliveryStatus | None = Query(default=None, alias="status"),
    route_id: int | None = Query(default=None),
    unassigned: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Delivery]:
    statement = select(Delivery).order_by(Delivery.created_at.desc())
    if current_user.role == UserRole.DRIVER:
        statement = statement.where(Delivery.route.has(Route.driver_id == current_user.id))

    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Delivery.invoice_number.ilike(term),
                Delivery.customer_name.ilike(term),
                Delivery.city.ilike(term),
                Delivery.customer_document.ilike(term),
            )
        )
    if delivery_status is not None:
        statement = statement.where(Delivery.status == delivery_status)
    if route_id is not None:
        statement = statement.where(Delivery.route_id == route_id)
    if unassigned is True:
        statement = statement.where(Delivery.route_id.is_(None))
    elif unassigned is False:
        statement = statement.where(Delivery.route_id.is_not(None))

    return list(db.scalars(statement).all())


@router.post("", response_model=DeliveryRead, status_code=status.HTTP_201_CREATED)
def create_delivery(
    payload: DeliveryCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Delivery:
    delivery = Delivery(**payload.model_dump())
    if delivery.status == DeliveryStatus.DELIVERED:
        delivery.delivered_at = utc_now()

    db.add(delivery)
    db.flush()
    register_audit(
        db,
        user_id=current_user.id,
        action="create",
        entity_type="delivery",
        entity_id=delivery.id,
        details={
            "invoice_number": delivery.invoice_number,
            "customer_name": delivery.customer_name,
        },
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(delivery)
    return delivery


@router.get("/{delivery_id}", response_model=DeliveryRead)
def get_delivery(
    delivery_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Delivery:
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega nao encontrada")
    if current_user.role == UserRole.DRIVER:
        route = db.get(Route, delivery.route_id) if delivery.route_id else None
        if not route or route.driver_id != current_user.id:
            raise HTTPException(status_code=403, detail="Entrega nao pertence ao motorista")
    return delivery


@router.patch("/{delivery_id}", response_model=DeliveryRead)
def update_delivery(
    delivery_id: int,
    payload: DeliveryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.DRIVER)
    ),
) -> Delivery:
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega nao encontrada")

    changes = payload.model_dump(exclude_unset=True)
    if current_user.role == UserRole.DRIVER:
        route = db.get(Route, delivery.route_id) if delivery.route_id else None
        if not route or route.driver_id != current_user.id:
            raise HTTPException(status_code=403, detail="Entrega nao pertence ao motorista")
        if route.status != RouteStatus.IN_PROGRESS:
            raise HTTPException(status_code=409, detail="A rota precisa estar em andamento")
        if set(changes) != {"status"} or changes.get("status") not in {
            DeliveryStatus.DELIVERED,
            DeliveryStatus.RETURNED,
        }:
            raise HTTPException(
                status_code=403,
                detail="Motoristas podem informar apenas entrega concluida ou devolvida",
            )

    for field, value in changes.items():
        setattr(delivery, field, value)

    if changes.get("status") == DeliveryStatus.DELIVERED:
        delivery.delivered_at = utc_now()

    register_audit(
        db,
        user_id=current_user.id,
        action="update",
        entity_type="delivery",
        entity_id=delivery.id,
        details={"fields": sorted(changes.keys())},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(delivery)
    return delivery


@router.patch("/{delivery_id}/atribuir-rota/{route_id}", response_model=DeliveryRead)
def assign_route(
    delivery_id: int,
    route_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Delivery:
    delivery = db.get(Delivery, delivery_id)
    route = db.scalar(
        select(Route)
        .options(selectinload(Route.deliveries))
        .where(Route.id == route_id)
    )

    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega nao encontrada")
    if not route:
        raise HTTPException(status_code=404, detail="Rota nao encontrada")
    if route.status != RouteStatus.OPEN:
        raise HTTPException(status_code=409, detail="Somente rotas abertas aceitam entregas")
    if delivery.route_id and delivery.route_id != route.id:
        raise HTTPException(status_code=409, detail="Entrega ja vinculada a outra rota")

    next_sequence = max((item.sequence or 0 for item in route.deliveries), default=0) + 1
    delivery.route_id = route.id
    delivery.sequence = delivery.sequence or next_sequence

    register_audit(
        db,
        user_id=current_user.id,
        action="assign_route",
        entity_type="delivery",
        entity_id=delivery.id,
        details={"route_id": route.id, "sequence": delivery.sequence},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(delivery)
    return delivery


@router.patch("/{delivery_id}/remover-rota", response_model=DeliveryRead)
def remove_route(
    delivery_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Delivery:
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega nao encontrada")

    old_route_id = delivery.route_id
    if old_route_id:
        route = db.get(Route, old_route_id)
        if route and route.status != RouteStatus.OPEN:
            raise HTTPException(status_code=409, detail="A rota precisa estar aberta")

    delivery.route_id = None
    delivery.sequence = None
    register_audit(
        db,
        user_id=current_user.id,
        action="remove_route",
        entity_type="delivery",
        entity_id=delivery.id,
        details={"old_route_id": old_route_id},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(delivery)
    return delivery


@router.delete("/{delivery_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery(
    delivery_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega nao encontrada")
    if delivery.route_id is not None:
        raise HTTPException(status_code=409, detail="Remova a entrega da rota antes de excluir")

    register_audit(
        db,
        user_id=current_user.id,
        action="delete",
        entity_type="delivery",
        entity_id=delivery.id,
        details={"invoice_number": delivery.invoice_number},
        ip_address=client_ip(request),
    )
    db.delete(delivery)
    db.commit()
