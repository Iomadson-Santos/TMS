import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class VehicleStatus(str, enum.Enum):
    disponivel = "disponivel"
    em_rota = "em_rota"
    manutencao = "manutencao"
    inativo = "inativo"


class RouteStatus(str, enum.Enum):
    planejada = "planejada"
    em_andamento = "em_andamento"
    concluida = "concluida"
    cancelada = "cancelada"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(10), unique=True, nullable=False)
    modelo = Column(String(100), nullable=False)
    tipo = Column(String(50), nullable=False)
    capacidade_kg = Column(Float, nullable=False)
    status = Column(Enum(VehicleStatus), default=VehicleStatus.disponivel)
    motorista = Column(String(100))
    telefone_motorista = Column(String(20))
    lat_atual = Column(Float, default=-23.5505)
    lng_atual = Column(Float, default=-46.6333)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    rotas = relationship("Route", back_populates="veiculo")
    rastreamentos = relationship(
        "Tracking",
        back_populates="veiculo",
        cascade="all, delete-orphan",
    )


class Stop(Base):
    __tablename__ = "stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    ordem = Column(Integer, nullable=False)
    endereco = Column(String(255), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    destinatario = Column(String(100))
    carga_kg = Column(Float, default=0)
    concluida = Column(Boolean, default=False)
    observacao = Column(Text)

    rota = relationship("Route", back_populates="paradas")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    status = Column(Enum(RouteStatus), default=RouteStatus.planejada)
    distancia_km = Column(Float, default=0)
    tempo_estimado_min = Column(Integer, default=0)
    carga_total_kg = Column(Float, default=0)
    origem_lat = Column(Float, nullable=False)
    origem_lng = Column(Float, nullable=False)
    origem_endereco = Column(String(255), nullable=False)
    observacao = Column(Text)
    iniciada_em = Column(DateTime(timezone=True))
    concluida_em = Column(DateTime(timezone=True))
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    veiculo = relationship("Vehicle", back_populates="rotas")
    paradas = relationship(
        "Stop",
        back_populates="rota",
        order_by="Stop.ordem",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Tracking(Base):
    __tablename__ = "tracking"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    velocidade_kmh = Column(Float, default=0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    veiculo = relationship("Vehicle", back_populates="rastreamentos")
