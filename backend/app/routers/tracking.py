import asyncio

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.session import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models import Tracking, User, UserRole, Vehicle
from app.schemas.tracking import TrackingCreate, TrackingOut

router = APIRouter(prefix="/tracking", tags=["Rastreamento"])


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, vehicle_id: int) -> None:
        await websocket.accept()
        self.active.setdefault(vehicle_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, vehicle_id: int) -> None:
        connections = self.active.get(vehicle_id, [])

        if websocket in connections:
            connections.remove(websocket)

        if not connections:
            self.active.pop(vehicle_id, None)

    async def broadcast(self, vehicle_id: int, payload: dict) -> None:
        for websocket in list(self.active.get(vehicle_id, [])):
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(websocket, vehicle_id)


manager = ConnectionManager()


def get_user_from_ws_token(token: str | None, db: Session) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Token não informado")

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")

    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    user = db.get(User, int(user_id))

    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuário inativo")

    return user


@router.get("/all/latest")
def posicoes_atuais(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [
        {
            "vehicle_id": v.id,
            "placa": v.placa,
            "modelo": v.modelo,
            "motorista": v.motorista,
            "status": v.status,
            "lat": v.lat_atual,
            "lng": v.lng_atual,
        }
        for v in db.query(Vehicle).all()
    ]


@router.get("/{vehicle_id}", response_model=list[TrackingOut])
def historico_rastreamento(
    vehicle_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Tracking)
        .filter(Tracking.vehicle_id == vehicle_id)
        .order_by(Tracking.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.post("/", response_model=TrackingOut, status_code=status.HTTP_201_CREATED)
async def registrar_posicao(
    data: TrackingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.admin, UserRole.operador, UserRole.motorista)
    ),
):
    vehicle = db.get(Vehicle, data.vehicle_id)

    if not vehicle:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")

    tracking = Tracking(**data.model_dump())

    db.add(tracking)

    vehicle.lat_atual = data.lat
    vehicle.lng_atual = data.lng

    db.commit()
    db.refresh(tracking)

    payload = {
        "vehicle_id": data.vehicle_id,
        "lat": data.lat,
        "lng": data.lng,
        "velocidade_kmh": data.velocidade_kmh,
        "timestamp": tracking.timestamp.isoformat(),
    }

    await manager.broadcast(data.vehicle_id, payload)
    await manager.broadcast(-1, payload)

    return tracking


@router.websocket("/ws/all/live")
async def ws_todos_veiculos(
    websocket: WebSocket,
    token: str | None = Query(None),
    db: Session = Depends(get_db),
):
    try:
        get_user_from_ws_token(token, db)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, -1)

    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket, -1)


@router.websocket("/ws/{vehicle_id}")
async def ws_rastreamento(
    websocket: WebSocket,
    vehicle_id: int,
    token: str | None = Query(None),
    db: Session = Depends(get_db),
):
    try:
        get_user_from_ws_token(token, db)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, vehicle_id)

    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket, vehicle_id)