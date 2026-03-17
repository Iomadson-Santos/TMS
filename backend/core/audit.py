from sqlalchemy.orm import Session
from models.audit import AuditLog

def registrar(db: Session, acao: str, entidade: str, entidade_id: int = None, descricao: str = None, usuario: str = "sistema"):
    log = AuditLog(
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        descricao=descricao,
        usuario=usuario,
    )
    db.add(log)
    db.commit()