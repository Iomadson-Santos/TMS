from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from audit import registrar
from database import get_db
from delivery import Delivery, DeliveryStatus
from models import Route
from delivery_schema import DeliveryCreate, DeliveryOut, DeliveryUpdate

router = APIRouter(prefix="/deliveries", tags=["Entregas"])


@router.get("/", response_model=List[DeliveryOut])
def listar_entregas(
    status: Optional[DeliveryStatus] = Query(None),
    route_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Delivery)

    if status is not None:
        q = q.filter(Delivery.status == status)

    if route_id is not None:
        q = q.filter(Delivery.route_id == route_id)

    if search:
        like = f"%{search}%"
        q = q.filter(
            Delivery.nome_fantasia.ilike(like)
            | Delivery.nf_numero.ilike(like)
            | Delivery.cnpj_cpf.ilike(like)
            | Delivery.endereco.ilike(like)
        )

    return q.order_by(Delivery.criado_em.desc()).all()


@router.get("/pendentes", response_model=List[DeliveryOut])
def entregas_pendentes(db: Session = Depends(get_db)):
    return (
        db.query(Delivery)
        .filter(
            Delivery.route_id.is_(None),
            Delivery.status == DeliveryStatus.pendente,
        )
        .all()
    )


@router.get("/rota/{route_id}", response_model=List[DeliveryOut])
def entregas_por_rota(route_id: int, db: Session = Depends(get_db)):
    return db.query(Delivery).filter(Delivery.route_id == route_id).all()


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
    db.flush()

    registrar(
        db,
        "criou_entrega",
        "delivery",
        d.id,
        f"NF {d.nf_numero} - {d.nome_fantasia}",
    )

    db.commit()
    db.refresh(d)
    return d


@router.patch("/{delivery_id}", response_model=DeliveryOut)
def atualizar_entrega(delivery_id: int, data: DeliveryUpdate, db: Session = Depends(get_db)):
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(d, campo, valor)

    registrar(
        db,
        "alterou_entrega",
        "delivery",
        d.id,
        f"NF {d.nf_numero} atualizada",
    )

    db.commit()
    db.refresh(d)
    return d


@router.patch("/{delivery_id}/atribuir-rota/{route_id}", response_model=DeliveryOut)
def atribuir_rota(delivery_id: int, route_id: int, db: Session = Depends(get_db)):
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")

    rota = db.query(Route).filter(Route.id == route_id).first()
    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    d.route_id = route_id
    d.status = DeliveryStatus.em_rota

    registrar(
        db,
        "atribuiu_rota_entrega",
        "delivery",
        d.id,
        f"Entrega {d.id} vinculada à rota {route_id}",
    )

    db.commit()
    db.refresh(d)
    return d


@router.patch("/{delivery_id}/concluir", response_model=DeliveryOut)
def concluir_entrega(delivery_id: int, db: Session = Depends(get_db)):
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")

    d.status = DeliveryStatus.entregue

    registrar(
        db,
        "concluiu_entrega",
        "delivery",
        d.id,
        f"NF {d.nf_numero} entregue",
    )

    db.commit()
    db.refresh(d)
    return d


@router.delete("/{delivery_id}", status_code=204)
def deletar_entrega(delivery_id: int, db: Session = Depends(get_db)):
    d = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")

    registrar(
        db,
        "excluiu_entrega",
        "delivery",
        d.id,
        f"NF {d.nf_numero} removida",
    )

    db.delete(d)
    db.commit()