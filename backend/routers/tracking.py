from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict
import json, asyncio

from core.database import get_db, SessionLocal
from models.models import Tracking, Vehicle
from schemas.schemas import TrackingCreate, TrackingOut

router = APIRouter(prefix="/tracking", tags=["Rastreamento"])

# ── WebSocket Manager ─────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: Dict[int, List[WebSocket]] = {}  # vehicle_id -> [ws]

    async def connect(self, ws: WebSocket, vehicle_id: int):
        await ws.accept()
        self.active.setdefault(vehicle_id, []).append(ws)

    def disconnect(self, ws: WebSocket, vehicle_id: int):
        if vehicle_id in self.active:
            self.active[vehicle_id].remove(ws)

    async def broadcast(self, vehicle_id: int, data: dict):
        for ws in self.active.get(vehicle_id, []):
            try:
                await ws.send_json(data)
            except Exception:
                pass

    async def broadcast_all(self, data: dict):
        # Envia para quem assina "todos" (-1)
        for ws in self.active.get(-1, []):
            try:
                await ws.send_json(data)
            except Exception:
                pass
        # Envia para quem assina o veículo específico
        vid = data.get("vehicle_id")
        if vid:
            for ws in self.active.get(vid, []):
                try:
                    await ws.send_json(data)
                except Exception:
                    pass

manager = ConnectionManager()

# ── HTTP Endpoints ────────────────────────────────────────
@router.get("/{vehicle_id}", response_model=List[TrackingOut])
def historico_rastreamento(vehicle_id: int, limit: int = 50, db: Session = Depends(get_db)):
    return (
        db.query(Tracking)
        .filter(Tracking.vehicle_id == vehicle_id)
        .order_by(Tracking.timestamp.desc())
        .limit(limit)
        .all()
    )

@router.get("/all/latest")
def posicoes_atuais(db: Session = Depends(get_db)):
    """Retorna a última posição conhecida de todos os veículos."""
    veiculos = db.query(Vehicle).all()
    resultado = []
    for v in veiculos:
        resultado.append({
            "vehicle_id": v.id,
            "placa": v.placa,
            "modelo": v.modelo,
            "motorista": v.motorista,
            "status": v.status,
            "lat": v.lat_atual,
            "lng": v.lng_atual,
        })
    return resultado

@router.post("/", response_model=TrackingOut, status_code=201)
async def registrar_posicao(data: TrackingCreate, db: Session = Depends(get_db)):
    t = Tracking(**data.model_dump())
    db.add(t)

    # Atualiza posição atual do veículo
    v = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if v:
        v.lat_atual = data.lat
        v.lng_atual = data.lng

    db.commit()
    db.refresh(t)

    # Broadcast para clientes conectados via WS
    payload = {
        "vehicle_id": data.vehicle_id,
        "lat": data.lat,
        "lng": data.lng,
        "velocidade_kmh": data.velocidade_kmh,
        "timestamp": t.timestamp.isoformat(),
    }
    await manager.broadcast_all(payload)

    return t

# ── WebSocket ─────────────────────────────────────────────
@router.websocket("/ws/{vehicle_id}")
async def ws_rastreamento(websocket: WebSocket, vehicle_id: int):
    """
    Conecte-se a este WebSocket para receber atualizações em tempo real
    da posição de um veículo específico.
    """
    await manager.connect(websocket, vehicle_id)
    try:
        while True:
            await asyncio.sleep(1)  # Mantém conexão viva
    except WebSocketDisconnect:
        manager.disconnect(websocket, vehicle_id)

@router.websocket("/ws/all/live")
async def ws_todos_veiculos(websocket: WebSocket):
    """Recebe atualizações de todos os veículos em tempo real."""
    await manager.connect(websocket, -1)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket, -1)
