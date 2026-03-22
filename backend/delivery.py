import enum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class DeliveryStatus(str, enum.Enum):
    pendente = "pendente"
    em_rota = "em_rota"
    entregue = "entregue"
    devolvido = "devolvido"
    cancelado = "cancelado"


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    nf_numero = Column(String(20), nullable=False)
    nf_serie = Column(String(5), default="1")
    nome_fantasia = Column(String(150), nullable=False)
    cnpj_cpf = Column(String(20))
    telefone = Column(String(20))
    endereco = Column(String(255), nullable=False)
    cidade = Column(String(100))
    estado = Column(String(2))
    cep = Column(String(10))
    lat = Column(Float)
    lng = Column(Float)
    peso_kg = Column(Float, default=0)
    volume_m3 = Column(Float, default=0)
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.pendente)
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="SET NULL"), nullable=True)
    observacao = Column(Text)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now())

    rota = relationship("Route", backref="entregas")
