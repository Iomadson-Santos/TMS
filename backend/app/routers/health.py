from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal


router = APIRouter(prefix="/health", tags=["Saude"])


@router.get("")
def health_check() -> dict[str, str]:
    """Liveness: confirma que o processo HTTP esta respondendo."""

    return {"status": "ok", "service": "tms"}


@router.get("/ready")
def readiness_check() -> dict[str, str]:
    """Readiness: confirma tambem a conectividade com o banco."""

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponivel",
        ) from exc

    return {"status": "ready", "service": "tms", "database": "ok"}
