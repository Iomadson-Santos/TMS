from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.enums import UserRole, VehicleStatus
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate
from app.services.audit import register_audit
from app.services.auth_security import client_ip


router = APIRouter(prefix="/vehicles", tags=["Veiculos"])


@router.get("", response_model=list[VehicleRead])
def list_vehicles(
    search: str | None = Query(default=None, max_length=100),
    vehicle_status: VehicleStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> list[Vehicle]:
    statement = select(Vehicle).order_by(Vehicle.plate)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(Vehicle.plate.ilike(term), Vehicle.model.ilike(term), Vehicle.brand.ilike(term))
        )
    if vehicle_status is not None:
        statement = statement.where(Vehicle.status == vehicle_status)
    return list(db.scalars(statement).all())


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    payload: VehicleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Vehicle:
    vehicle = Vehicle(**payload.model_dump())
    db.add(vehicle)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Placa ja cadastrada") from exc

    register_audit(
        db,
        user_id=current_user.id,
        action="create",
        entity_type="vehicle",
        entity_id=vehicle.id,
        details={"plate": vehicle.plate},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/{vehicle_id}", response_model=VehicleRead)
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Veiculo nao encontrado")
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Veiculo nao encontrado")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(vehicle, field, value)

    register_audit(
        db,
        user_id=current_user.id,
        action="update",
        entity_type="vehicle",
        entity_id=vehicle.id,
        details={"fields": sorted(changes.keys())},
        ip_address=client_ip(request),
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Placa ja cadastrada") from exc

    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    vehicle_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Veiculo nao encontrado")
    if vehicle.routes:
        raise HTTPException(
            status_code=409,
            detail="Veiculo possui rotas vinculadas e nao pode ser excluido",
        )

    register_audit(
        db,
        user_id=current_user.id,
        action="delete",
        entity_type="vehicle",
        entity_id=vehicle.id,
        details={"plate": vehicle.plate},
        ip_address=client_ip(request),
    )
    db.delete(vehicle)
    db.commit()
