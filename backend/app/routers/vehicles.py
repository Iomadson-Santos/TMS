from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models import RouteStatus, User, UserRole, Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleOut, VehicleUpdate
from app.services.audit import registrar

router = APIRouter(prefix="/vehicles", tags=["Veículos"])


@router.get("/", response_model=list[VehicleOut])
def listar_veiculos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Vehicle).order_by(Vehicle.placa).all()


@router.get("/{vehicle_id}", response_model=VehicleOut)
def obter_veiculo(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vehicle = db.get(Vehicle, vehicle_id)

    if not vehicle:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")

    return vehicle


@router.post("/", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def criar_veiculo(
    data: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.operador)),
):
    if db.query(Vehicle).filter(Vehicle.placa == data.placa).first():
        raise HTTPException(status_code=409, detail="Placa já cadastrada")

    vehicle = Vehicle(**data.model_dump())

    db.add(vehicle)
    db.flush()

    registrar(
        db,
        "criou_veiculo",
        "vehicle",
        vehicle.id,
        f"Veículo {vehicle.placa} cadastrado",
    )

    db.commit()
    db.refresh(vehicle)

    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleOut)
def atualizar_veiculo(
    vehicle_id: int,
    data: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.operador)),
):
    vehicle = db.get(Vehicle, vehicle_id)

    if not vehicle:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)

    registrar(
        db,
        "alterou_veiculo",
        "vehicle",
        vehicle.id,
        f"Veículo {vehicle.placa} atualizado",
    )

    db.commit()
    db.refresh(vehicle)

    return vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_veiculo(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin)),
):
    vehicle = db.get(Vehicle, vehicle_id)

    if not vehicle:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")

    if any(route.status == RouteStatus.em_andamento for route in vehicle.rotas):
        raise HTTPException(
            status_code=409,
            detail="Não é possível excluir veículo com rota em andamento",
        )

    registrar(
        db,
        "excluiu_veiculo",
        "vehicle",
        vehicle.id,
        f"Veículo {vehicle.placa} excluído",
    )

    db.delete(vehicle)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)