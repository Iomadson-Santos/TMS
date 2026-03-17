from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, index=True)
    acao        = Column(String(100), nullable=False)
    entidade    = Column(String(50), nullable=False)
    entidade_id = Column(Integer)
    descricao   = Column(Text)
    usuario     = Column(String(100), default="sistema")
    criado_em   = Column(DateTime(timezone=True), server_default=func.now())