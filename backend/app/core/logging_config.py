from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.core.config import settings


_CONFIGURED = False


def configure_logging() -> None:
    """Configura logs sem registrar corpos, senhas, cookies ou tokens."""

    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, settings.log_level, logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    handlers: list[logging.Handler] = []
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    handlers.append(console)

    log_path = settings.resolved_log_file
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for handler in handlers:
        root.addHandler(handler)

    # Bibliotecas de rede e banco podem ser muito verbosas. Em producao isso
    # tambem reduz o risco de valores de cabecalhos aparecerem em logs de debug.
    logging.getLogger("httpx").setLevel(max(level, logging.WARNING))
    logging.getLogger("httpcore").setLevel(max(level, logging.WARNING))
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    _CONFIGURED = True
