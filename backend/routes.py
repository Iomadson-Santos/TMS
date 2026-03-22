import math
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from audit import registrar
from database import get_db
from models import Route, RouteStatus, Stop, Vehicle, VehicleStatus
from schemas import (
    OtimizacaoRequest,
    OtimizacaoResponse,
    RouteCreate,
    RouteOut,
    RouteUpdate,
    StopCreate,
)

router = APIRouter(prefix="/routes", tags=["Rotas"])


def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def nearest_neighbor(origem_lat, origem_lng, paradas: List[StopCreate]):
    restantes = list(enumerate(paradas))
    ordem = []
    lat, lng = origem_lat, origem_lng

    while restantes:
        idx_mais_proximo = min(
            restantes,
            key=lambda x: haversine(lat, lng, x[1].lat, x[1].lng),
        )
        restantes.remove(idx_mais_proximo)
        ordem.append(idx_mais_proximo[1])
        lat, lng = idx_mais_proximo[1].lat, idx_mais_proximo[1].lng

    return ordem


def calcular_distancia_total(origem_lat, origem_lng, paradas) -> float:
    dist = 0
    lat, lng = origem_lat, origem_lng

    for p in paradas:
        dist += haversine(lat, lng, p.lat, p.lng)
        lat, lng = p.lat, p.lng

    return round(dist, 2)


@router.get("/", response_model=List[RouteOut])
def listar_rotas(db: Session = Depends(get_db)):
    return db.query(Route).order_by(Route.criado_em.desc()).all()


@router.get("/{route_id}", response_model=RouteOut)
def obter_rota(route_id: int, db: Session = Depends(get_db)):
    r = db.query(Route).filter(Route.id == route_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rota não encontrada")
    return r


@router.post("/", response_model=RouteOut, status_code=201)
def criar_rota(data: RouteCreate, db: Session = Depends(get_db)):
    veiculo = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")

    if veiculo.status != VehicleStatus.disponivel:
        raise HTTPException(
            status_code=400,
            detail="Veículo não está disponível para nova rota",
        )

    carga_total = sum(p.carga_kg for p in data.paradas)
    if carga_total > veiculo.capacidade_kg:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Carga total ({carga_total}kg) excede capacidade do veículo "
                f"({veiculo.capacidade_kg}kg)"
            ),
        )

    distancia = calcular_distancia_total(data.origem_lat, data.origem_lng, data.paradas)
    tempo_est = int(distancia / 40 * 60)

    rota = Route(
        nome=data.nome,
        vehicle_id=data.vehicle_id,
        origem_lat=data.origem_lat,
        origem_lng=data.origem_lng,
        origem_endereco=data.origem_endereco,
        observacao=data.observacao,
        distancia_km=distancia,
        tempo_estimado_min=tempo_est,
        carga_total_kg=carga_total,
    )
    db.add(rota)
    db.flush()

    for i, parada_data in enumerate(data.paradas, start=1):
        payload = parada_data.model_dump(exclude={"ordem"})
        parada = Stop(route_id=rota.id, ordem=i, **payload)
        db.add(parada)

    registrar(
        db,
        "criou_rota",
        "route",
        rota.id,
        f"Rota {rota.nome} criada com {len(data.paradas)} paradas",
    )

    db.commit()
    db.refresh(rota)
    return rota


@router.patch("/{route_id}", response_model=RouteOut)
def atualizar_rota(route_id: int, data: RouteUpdate, db: Session = Depends(get_db)):
    rota = db.query(Route).filter(Route.id == route_id).first()
    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    payload = data.model_dump(exclude_unset=True)

    for campo, valor in payload.items():
        setattr(rota, campo, valor)

    if data.status == RouteStatus.em_andamento and not rota.iniciada_em:
        rota.iniciada_em = datetime.now(timezone.utc)
        veiculo = db.query(Vehicle).filter(Vehicle.id == rota.vehicle_id).first()
        if veiculo:
            veiculo.status = VehicleStatus.em_rota

    if data.status == RouteStatus.concluida and not rota.concluida_em:
        rota.concluida_em = datetime.now(timezone.utc)

        veiculo = db.query(Vehicle).filter(Vehicle.id == rota.vehicle_id).first()
        if veiculo:
            veiculo.status = VehicleStatus.disponivel

        from delivery import Delivery, DeliveryStatus

        db.query(Delivery).filter(
            Delivery.route_id == rota.id,
            Delivery.status == DeliveryStatus.em_rota,
        ).update({Delivery.status: DeliveryStatus.entregue}, synchronize_session=False)

    registrar(
        db,
        "alterou_status_rota",
        "route",
        rota.id,
        f"Rota {rota.nome} -> {rota.status}",
    )

    db.commit()
    db.refresh(rota)
    return rota


@router.delete("/{route_id}", status_code=204)
def deletar_rota(route_id: int, db: Session = Depends(get_db)):
    rota = db.query(Route).filter(Route.id == route_id).first()
    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    if rota.status == RouteStatus.em_andamento:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir uma rota em andamento",
        )

    registrar(
        db,
        "excluiu_rota",
        "route",
        rota.id,
        f"Rota {rota.nome} removida",
    )

    db.delete(rota)
    db.commit()


@router.patch("/{route_id}/stops/{stop_id}/concluir")
def concluir_parada(route_id: int, stop_id: int, db: Session = Depends(get_db)):
    parada = db.query(Stop).filter(Stop.id == stop_id, Stop.route_id == route_id).first()
    if not parada:
        raise HTTPException(status_code=404, detail="Parada não encontrada")

    parada.concluida = True
    db.commit()

    return {"ok": True, "stop_id": stop_id}


@router.post("/otimizar", response_model=OtimizacaoResponse)
def otimizar_rota(data: OtimizacaoRequest, db: Session = Depends(get_db)):
    if not data.paradas:
        raise HTTPException(status_code=400, detail="Informe ao menos uma parada")

    ordem_original = calcular_distancia_total(data.origem_lat, data.origem_lng, data.paradas)
    ordem_otimizada = nearest_neighbor(data.origem_lat, data.origem_lng, data.paradas)
    dist_otimizada = calcular_distancia_total(
        data.origem_lat,
        data.origem_lng,
        ordem_otimizada,
    )

    for i, p in enumerate(ordem_otimizada, start=1):
        p.ordem = i

    return OtimizacaoResponse(
        ordem_otimizada=ordem_otimizada,
        distancia_total_km=dist_otimizada,
        tempo_estimado_min=int(dist_otimizada / 40 * 60),
        economia_km=round(ordem_original - dist_otimizada, 2),
    )