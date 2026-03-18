from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from models.models import Vehicle
from schemas.schemas import VehicleCreate, VehicleOut, VehicleUpdate
from core.audit import registrar

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
    db.commit()
    db.refresh(v)
    registrar(db, 'criou_veiculo', 'vehicle', v.id, f'Veículo {v.placa} cadastrado')
    return v

@router.patch("/{vehicle_id}", response_model=VehicleOut)
def atualizar_veiculo(vehicle_id: int, data: VehicleUpdate, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(v, campo, valor)
    db.commit()
    db.refresh(v)
    registrar(db, 'alterou_veiculo', 'vehicle', v.id, f'Veículo {v.placa} atualizado')
    return v

@router.delete("/{vehicle_id}", status_code=204)
def deletar_veiculo(vehicle_id: int, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    registrar(db, 'excluiu_veiculo', 'vehicle', v.id, f'Veículo {v.placa} excluído')
    from models.models import Route, RouteStatus
    rota_ativa = db.query(Route).filter(
        Route.vehicle_id == vehicle_id,
        Route.status == RouteStatus.em_andamento
    ).first()
    if rota_ativa:
        raise HTTPException(status_code=400, detail=f"Veículo possui rota ativa: {rota_ativa.nome}")
    db.delete(v)
    db.commit()
