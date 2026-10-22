from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

from sqlalchemy.engine import make_url

from app.core.config import settings


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _remove_expired(directory: Path) -> None:
    cutoff = datetime.now(timezone.utc).timestamp() - settings.backup_retention_days * 86400
    for item in directory.glob("tms_backup_*"):
        try:
            if item.is_file() and item.stat().st_mtime < cutoff:
                item.unlink()
        except OSError:
            continue


def _backup_sqlite(destination: Path) -> Path | None:
    url = make_url(settings.database_url)
    database = url.database
    if not database or database == ":memory:":
        print("Banco SQLite em memoria; nenhum arquivo para copiar.")
        return None

    source = Path(database)
    if not source.is_absolute():
        source = Path.cwd() / source
    if not source.exists():
        print(f"Banco ainda nao existe: {source}")
        return None

    target = destination / f"tms_backup_{_stamp()}.db"
    source_connection = sqlite3.connect(source)
    target_connection = sqlite3.connect(target)
    try:
        source_connection.backup(target_connection)
    finally:
        target_connection.close()
        source_connection.close()
    return target


def _backup_postgresql(destination: Path) -> Path:
    executable = shutil.which("pg_dump")
    if not executable:
        raise RuntimeError(
            "pg_dump nao foi encontrado. Instale as ferramentas do PostgreSQL "
            "ou use o backup gerenciado do provedor antes de publicar."
        )

    url = make_url(settings.database_url)
    target = destination / f"tms_backup_{_stamp()}.dump"
    args = [
        executable,
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        f"--file={target}",
    ]
    if url.host:
        args.append(f"--host={url.host}")
    if url.port:
        args.append(f"--port={url.port}")
    if url.username:
        args.append(f"--username={url.username}")
    if url.database:
        args.append(f"--dbname={url.database}")

    environment = os.environ.copy()
    if url.password:
        environment["PGPASSWORD"] = url.password
    subprocess.run(args, env=environment, check=True, timeout=3600)
    return target


def create_backup() -> Path | None:
    destination = settings.backup_path
    destination.mkdir(parents=True, exist_ok=True)
    backend = make_url(settings.database_url).get_backend_name()
    if backend == "sqlite":
        target = _backup_sqlite(destination)
    elif backend == "postgresql":
        target = _backup_postgresql(destination)
    else:
        raise RuntimeError(f"Banco sem rotina de backup suportada: {backend}")
    _remove_expired(destination)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria backup consistente do banco do TMS")
    parser.parse_args()
    try:
        target = create_backup()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Falha ao criar backup: {exc}")
        return 1
    if target:
        print(f"Backup criado: {target.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
