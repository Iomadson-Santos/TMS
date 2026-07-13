from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Delivery, DeliveryStatus, Route, RouteStatus, Stop, Vehicle, VehicleStatus
from app.schemas.route import OtimizacaoRequest, OtimizacaoResponse, RouteCreate, RouteOut, RouteUpdate
from app.services.audit import registrar
from app.services.route_optimizer import calcular_distancia_total, nearest_neighbor

router = APIRouter(prefix="/routes", tags=["Rotas"])


@router.get("/", response_model=list[RouteOut])
def listar_rotas(db: Session = Depends(get_db)):
    return db.query(Route).order_by(Route.criado_em.desc()).all()


@router.post("/otimizar", response_model=OtimizacaoResponse)
def otimizar_rota(data: OtimizacaoRequest):
    if not data.paradas:
        raise HTTPException(status_code=400, detail="Informe ao menos uma parada")
    original = calcular_distancia_total(data.origem_lat, data.origem_lng, data.paradas)
    otimizada = nearest_neighbor(data.origem_lat, data.origem_lng, data.paradas)
    distancia = calcular_distancia_total(data.origem_lat, data.origem_lng, otimizada)
    ordem = [parada.model_copy(update={"ordem": i}) for i, parada in enumerate(otimizada, 1)]
    return OtimizacaoResponse(ordem_otimizada=ordem, distancia_total_km=distancia, tempo_estimado_min=int(distancia / 40 * 60), economia_km=round(original - distancia, 2))


@router.get("/{route_id}", response_model=RouteOut)
def obter_rota(route_id: int, db: Session = Depends(get_db)):
    route = db.get(Route, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Rota não encontrada")
    return route


@router.post("/", response_model=RouteOut, status_code=status.HTTP_201_CREATED)
def criar_rota(data: RouteCreate, db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, data.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    if vehicle.status != VehicleStatus.disponivel:
        raise HTTPException(status_code=409, detail="Veículo não está disponível para nova rota")
    carga_total = sum(stop.carga_kg for stop in data.paradas)
    if carga_total > vehicle.capacidade_kg:
        raise HTTPException(status_code=400, detail=f"Carga total ({carga_total}kg) excede capacidade do veículo ({vehicle.capacidade_kg}kg)")
    distancia = calcular_distancia_total(data.origem_lat, data.origem_lng, data.paradas)
    route = Route(**data.model_dump(exclude={"paradas"}), distancia_km=distancia, tempo_estimado_min=int(distancia / 40 * 60), carga_total_kg=carga_total)
    db.add(route)
    db.flush()
    for index, stop in enumerate(data.paradas, 1):
        db.add(Stop(route_id=route.id, ordem=index, **stop.model_dump(exclude={"ordem"})))
    registrar(db, "criou_rota", "route", route.id, f"Rota {route.nome} criada")
    db.commit()
    db.refresh(route)
    return route


@router.patch("/{route_id}", response_model=RouteOut)
def atualizar_rota(route_id: int, data: RouteUpdate, db: Session = Depends(get_db)):
    route = db.get(Route, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Rota não encontrada")
    allowed = {
        RouteStatus.planejada: {RouteStatus.em_andamento, RouteStatus.cancelada},
        RouteStatus.em_andamento: {RouteStatus.concluida, RouteStatus.cancelada},
        RouteStatus.concluida: set(),
        RouteStatus.cancelada: set(),
    }
    new_status = data.status
    if new_status and new_status != route.status and new_status not in allowed[route.status]:
        raise HTTPException(status_code=409, detail=f"Transição inválida: {route.status.value} -> {new_status.value}")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(route, field, value)
    vehicle = db.get(Vehicle, route.vehicle_id)
    if new_status == RouteStatus.em_andamento:
        route.iniciada_em = route.iniciada_em or datetime.now(timezone.utc)
        if vehicle:
            vehicle.status = VehicleStatus.em_rota
    elif new_status in {RouteStatus.concluida, RouteStatus.cancelada}:
        if new_status == RouteStatus.concluida:
            route.concluida_em = route.concluida_em or datetime.now(timezone.utc)
            db.query(Delivery).filter(Delivery.route_id == route.id, Delivery.status == DeliveryStatus.em_rota).update({Delivery.status: DeliveryStatus.entregue}, synchronize_session=False)
        if vehicle:
            vehicle.status = VehicleStatus.disponivel
    registrar(db, "alterou_rota", "route", route.id, f"Rota {route.nome} atualizada")
    db.commit()
    db.refresh(route)
    return route


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_rota(route_id: int, db: Session = Depends(get_db)):
    route = db.get(Route, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Rota não encontrada")
    if route.status == RouteStatus.em_andamento:
        raise HTTPException(status_code=409, detail="Não é possível excluir uma rota em andamento")
    db.delete(route)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{route_id}/stops/{stop_id}/concluir")
def concluir_parada(route_id: int, stop_id: int, db: Session = Depends(get_db)):
    stop = db.query(Stop).filter(Stop.id == stop_id, Stop.route_id == route_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Parada não encontrada")
    stop.concluida = True
    db.commit()
    return {"ok": True, "stop_id": stop_id}
