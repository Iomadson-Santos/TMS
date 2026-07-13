from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Delivery, DeliveryStatus, Route, RouteStatus
from app.schemas.delivery import DeliveryCreate, DeliveryOut, DeliveryUpdate
from app.services.audit import registrar

router = APIRouter(prefix="/deliveries", tags=["Entregas"])


@router.get("/", response_model=list[DeliveryOut])
def listar_entregas(status_filter: DeliveryStatus | None = Query(None, alias="status"), route_id: int | None = None, search: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Delivery)
    if status_filter:
        query = query.filter(Delivery.status == status_filter)
    if route_id:
        query = query.filter(Delivery.route_id == route_id)
    if search:
        term = f"%{search}%"
        query = query.filter(or_(Delivery.nome_fantasia.ilike(term), Delivery.nf_numero.ilike(term), Delivery.cnpj_cpf.ilike(term), Delivery.endereco.ilike(term)))
    return query.order_by(Delivery.criado_em.desc()).all()


@router.get("/pendentes", response_model=list[DeliveryOut])
def entregas_pendentes(db: Session = Depends(get_db)):
    return db.query(Delivery).filter(Delivery.route_id.is_(None), Delivery.status == DeliveryStatus.pendente).all()


@router.get("/rota/{route_id}", response_model=list[DeliveryOut])
def entregas_por_rota(route_id: int, db: Session = Depends(get_db)):
    return db.query(Delivery).filter(Delivery.route_id == route_id).all()


@router.get("/{delivery_id}", response_model=DeliveryOut)
def obter_entrega(delivery_id: int, db: Session = Depends(get_db)):
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    return delivery


@router.post("/", response_model=DeliveryOut, status_code=status.HTTP_201_CREATED)
def criar_entrega(data: DeliveryCreate, db: Session = Depends(get_db)):
    delivery = Delivery(**data.model_dump())
    db.add(delivery)
    db.flush()
    registrar(db, "criou_entrega", "delivery", delivery.id, f"NF {delivery.nf_numero}")
    db.commit()
    db.refresh(delivery)
    return delivery


@router.patch("/{delivery_id}", response_model=DeliveryOut)
def atualizar_entrega(delivery_id: int, data: DeliveryUpdate, db: Session = Depends(get_db)):
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(delivery, field, value)
    db.commit()
    db.refresh(delivery)
    return delivery


@router.patch("/{delivery_id}/atribuir-rota/{route_id}", response_model=DeliveryOut)
def atribuir_rota(delivery_id: int, route_id: int, db: Session = Depends(get_db)):
    delivery = db.get(Delivery, delivery_id)
    route = db.get(Route, route_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    if not route:
        raise HTTPException(status_code=404, detail="Rota não encontrada")
    if route.status in {RouteStatus.concluida, RouteStatus.cancelada}:
        raise HTTPException(status_code=409, detail="Não é possível atribuir entrega a esta rota")
    delivery.route_id = route_id
    delivery.status = DeliveryStatus.em_rota
    db.commit()
    db.refresh(delivery)
    return delivery


@router.patch("/{delivery_id}/concluir", response_model=DeliveryOut)
def concluir_entrega(delivery_id: int, db: Session = Depends(get_db)):
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    delivery.status = DeliveryStatus.entregue
    db.commit()
    db.refresh(delivery)
    return delivery


@router.delete("/{delivery_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_entrega(delivery_id: int, db: Session = Depends(get_db)):
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")
    db.delete(delivery)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
