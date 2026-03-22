from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.audit import registrar
from core.database import get_db
from models.models import RouteStatus, Vehicle
from schemas.schemas import VehicleCreate, VehicleOut, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["Veículos"])


@router.get("/", response_model=List[VehicleOut])
def listar_veiculos(db: Session = Depends(get_db)):
    return db.query(Vehicle).all()


@router.get("/{vehicle_id}", response_model=VehicleOut)
def obter_veiculo(vehicle_id: int, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    return v


@router.post("/", response_model=VehicleOut, status_code=201)
def criar_veiculo(data: VehicleCreate, db: Session = Depends(get_db)):
    existente = db.query(Vehicle).filter(Vehicle.placa == data.placa).first()
    if existente:
        raise HTTPException(status_code=400, detail="Placa já cadastrada")

    v = Vehicle(**data.model_dump())
    db.add(v)
    db.flush()

    registrar(db, "criou_veiculo", "vehicle", v.id, f"Veículo {v.placa} cadastrado")

    db.commit()
    db.refresh(v)
    return v


@router.patch("/{vehicle_id}", response_model=VehicleOut)
def atualizar_veiculo(vehicle_id: int, data: VehicleUpdate, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(v, campo, valor)

    registrar(db, "alterou_veiculo", "vehicle", v.id, f"Veículo {v.placa} atualizado")

    db.commit()
    db.refresh(v)
    return v


@router.delete("/{vehicle_id}", status_code=204)
def deletar_veiculo(vehicle_id: int, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")

    rota_ativa = any(r.status == RouteStatus.em_andamento for r in v.rotas)
    if rota_ativa:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir veículo com rota em andamento",
        )

    registrar(db, "excluiu_veiculo", "vehicle", v.id, f"Veículo {v.placa} excluído")

    db.delete(v)
    db.commit()
