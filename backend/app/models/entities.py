import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


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


class DeliveryStatus(str, enum.Enum):
    pendente = "pendente"
    em_rota = "em_rota"
    entregue = "entregue"
    devolvido = "devolvido"
    cancelado = "cancelado"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(10), unique=True, nullable=False, index=True)
    modelo = Column(String(100), nullable=False)
    tipo = Column(String(50), nullable=False)
    capacidade_kg = Column(Float, nullable=False)
    status = Column(Enum(VehicleStatus), nullable=False, default=VehicleStatus.disponivel)
    motorista = Column(String(100))
    telefone_motorista = Column(String(20))
    lat_atual = Column(Float, nullable=False, default=-23.5505)
    lng_atual = Column(Float, nullable=False, default=-46.6333)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    rotas = relationship("Route", back_populates="veiculo")
    rastreamentos = relationship("Tracking", back_populates="veiculo", cascade="all, delete-orphan")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    status = Column(Enum(RouteStatus), nullable=False, default=RouteStatus.planejada)
    distancia_km = Column(Float, nullable=False, default=0)
    tempo_estimado_min = Column(Integer, nullable=False, default=0)
    carga_total_kg = Column(Float, nullable=False, default=0)
    origem_lat = Column(Float, nullable=False)
    origem_lng = Column(Float, nullable=False)
    origem_endereco = Column(String(255), nullable=False)
    observacao = Column(Text)
    iniciada_em = Column(DateTime(timezone=True))
    concluida_em = Column(DateTime(timezone=True))
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    veiculo = relationship("Vehicle", back_populates="rotas")
    paradas = relationship("Stop", back_populates="rota", order_by="Stop.ordem", cascade="all, delete-orphan", passive_deletes=True)
    entregas = relationship("Delivery", back_populates="rota")


class Stop(Base):
    __tablename__ = "stops"
    __table_args__ = (UniqueConstraint("route_id", "ordem", name="uq_stop_route_ordem"),)

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True)
    ordem = Column(Integer, nullable=False)
    endereco = Column(String(255), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    destinatario = Column(String(100))
    carga_kg = Column(Float, nullable=False, default=0)
    concluida = Column(Boolean, nullable=False, default=False)
    observacao = Column(Text)

    rota = relationship("Route", back_populates="paradas")


class Tracking(Base):
    __tablename__ = "tracking"
    __table_args__ = (Index("ix_tracking_vehicle_timestamp", "vehicle_id", "timestamp"),)

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    velocidade_kmh = Column(Float, nullable=False, default=0)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    veiculo = relationship("Vehicle", back_populates="rastreamentos")


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    nf_numero = Column(String(20), nullable=False, index=True)
    nf_serie = Column(String(5), nullable=False, default="1")
    nome_fantasia = Column(String(150), nullable=False)
    cnpj_cpf = Column(String(20), index=True)
    telefone = Column(String(20))
    endereco = Column(String(255), nullable=False)
    cidade = Column(String(100))
    estado = Column(String(2))
    cep = Column(String(10))
    lat = Column(Float)
    lng = Column(Float)
    peso_kg = Column(Float, nullable=False, default=0)
    volume_m3 = Column(Float, nullable=False, default=0)
    status = Column(Enum(DeliveryStatus), nullable=False, default=DeliveryStatus.pendente)
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="SET NULL"), nullable=True, index=True)
    observacao = Column(Text)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    rota = relationship("Route", back_populates="entregas")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    acao = Column(String(100), nullable=False)
    entidade = Column(String(100), nullable=False)
    entidade_id = Column(Integer)
    descricao = Column(Text)
    usuario = Column(String(100), nullable=False, default="sistema")
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
