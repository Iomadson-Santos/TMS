import asyncio
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from core.database import get_db
from models.models import Tracking, Vehicle
from schemas.schemas import TrackingCreate, TrackingOut

router = APIRouter(prefix="/tracking", tags=["Rastreamento"])


class ConnectionManager:
    def __init__(self):
        self.active: Dict[int, List[WebSocket]] = {}

    async def connect(self, ws: WebSocket, vehicle_id: int):
        await ws.accept()
        self.active.setdefault(vehicle_id, []).append(ws)

    def disconnect(self, ws: WebSocket, vehicle_id: int):
        if vehicle_id in self.active and ws in self.active[vehicle_id]:
            self.active[vehicle_id].remove(ws)
            if not self.active[vehicle_id]:
                del self.active[vehicle_id]

    async def broadcast(self, vehicle_id: int, data: dict):
        dead = []
        for ws in self.active.get(vehicle_id, []):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws, vehicle_id)


manager = ConnectionManager()


@router.get("/all/latest")
def posicoes_atuais(db: Session = Depends(get_db)):
    veiculos = db.query(Vehicle).all()
    resultado = []

    for v in veiculos:
        resultado.append(
            {
                "vehicle_id": v.id,
                "placa": v.placa,
                "modelo": v.modelo,
                "motorista": v.motorista,
                "status": v.status,
                "lat": v.lat_atual,
                "lng": v.lng_atual,
            }
        )

    return resultado


@router.get("/{vehicle_id}", response_model=List[TrackingOut])
def historico_rastreamento(vehicle_id: int, limit: int = 50, db: Session = Depends(get_db)):
    return (
        db.query(Tracking)
        .filter(Tracking.vehicle_id == vehicle_id)
        .order_by(Tracking.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.post("/", response_model=TrackingOut, status_code=201)
async def registrar_posicao(data: TrackingCreate, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")

    t = Tracking(**data.model_dump())
    db.add(t)

    v.lat_atual = data.lat
    v.lng_atual = data.lng

    db.commit()
    db.refresh(t)

    payload = {
        "vehicle_id": data.vehicle_id,
        "lat": data.lat,
        "lng": data.lng,
        "velocidade_kmh": data.velocidade_kmh,
        "timestamp": t.timestamp.isoformat(),
    }

    await manager.broadcast(data.vehicle_id, payload)
    await manager.broadcast(-1, payload)

    return t


@router.websocket("/ws/{vehicle_id}")
async def ws_rastreamento(websocket: WebSocket, vehicle_id: int):
    await manager.connect(websocket, vehicle_id)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket, vehicle_id)


@router.websocket("/ws/all/live")
async def ws_todos_veiculos(websocket: WebSocket):
    await manager.connect(websocket, -1)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket, -1)
