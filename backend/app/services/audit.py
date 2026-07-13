from sqlalchemy.orm import Session

from app.models import AuditLog


def registrar(db: Session, acao: str, entidade: str, entidade_id: int | None = None, descricao: str | None = None, usuario: str = "sistema") -> None:
    db.add(AuditLog(acao=acao, entidade=entidade, entidade_id=entidade_id, descricao=descricao, usuario=usuario))
