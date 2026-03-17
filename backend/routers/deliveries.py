from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from core.audit import registrar

from core.database import get_db
from models.delivery import Delivery, DeliveryStatus
from schemas.delivery_schema import DeliveryCreate, DeliveryUpdate, DeliveryOut

router = APIRouter(prefix="/deliveries", tags=["Entregas"])

@router.get("/", response_model=List[DeliveryOut])
def listar_entregas(
    status: Optional[str] = Query(None),
    route_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Delivery)
    if status:
        q = q.filter(Delivery.status == status)
    if route_id is not None:
        q = q.filter(Delivery.route_id == route_id)
    if search:
        like = f"%{search}%"
        q = q.filter(
            Delivery.nome_fantasia.ilike(like) |
            Delivery.nf_numero.ilike(like) |
            Delivery.cnpj_cpf.ilike(like) |
            Delivery.endereco.ilike(like)
        )
    return q.order_by(Delivery.criado_em.desc()).all()

@router.get("/pendentes", response_model=List[DeliveryOut])
def entregas_pendentes(db: Session = Depends(get_db)):
    return db.query(Delivery).filter(Delivery.route_id == None, Delivery.status == DeliveryStatus.pendente).all()

@router.get("/{delivery_id}", response_model=DeliveryOut)
def obter_entrega(delivery_id: int, db: Session = Depends(get_db)):
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    return d

@router.post("/", response_model=DeliveryOut, status_code=201)
def criar_entrega(data: DeliveryCreate, db: Session = Depends(get_db)):
    d = Delivery(**data.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    registrar(db, 'criou_entrega', 'delivery', d.id, f'NF {d.nf_numero} — {d.nome_fantasia}')
    return d

@router.patch("/{delivery_id}", response_model=DeliveryOut)
def atualizar_entrega(delivery_id: int, data: DeliveryUpdate, db: Session = Depends(get_db)):
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(d, campo, valor)
    db.commit()
    db.refresh(d)
    registrar(db, 'alterou_entrega', 'delivery', d.id, f'NF {d.nf_numero} status atualizado')
    return d

@router.patch("/{delivery_id}/atribuir-rota/{route_id}", response_model=DeliveryOut)
def atribuir_rota(delivery_id: int, route_id: int, db: Session = Depends(get_db)):
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    d.route_id = route_id
    d.status = DeliveryStatus.em_rota
    db.commit()
    db.refresh(d)
    return d

@router.patch("/{delivery_id}/concluir", response_model=DeliveryOut)
def concluir_entrega(delivery_id: int, db: Session = Depends(get_db)):
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    d.status = DeliveryStatus.entregue
    db.commit()
    db.refresh(d)
    registrar(db, 'concluiu_entrega', 'delivery', d.id, f'NF {d.nf_numero} entregue')
    return d

@router.delete("/{delivery_id}", status_code=204)
def deletar_entrega(delivery_id: int, db: Session = Depends(get_db)):
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    db.delete(d)
    db.commit()
@router.get("/rota/{route_id}", response_model=List[DeliveryOut])
def entregas_por_rota(route_id: int, db: Session = Depends(get_db)):
    return db.query(Delivery).filter(Delivery.route_id == route_id).all()