from __future__ import annotations

from pathlib import Path
import secrets
import shutil
import sys


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_DIR / ".env"
EXAMPLE_PATH = BACKEND_DIR / ".env.example"
BACKUP_PATH = BACKEND_DIR / ".env.backup-v0.1.4"

LEGACY_SECRETS = {
    "troque-esta-chave-por-uma-chave-longa-e-aleatoria",
    "troque-esta-chave-secreta-por-uma-chave-com-mais-de-48-caracteres",
}

# Valores adicionados apenas quando a chave ainda nao existe. Sao valores de
# desenvolvimento; a publicacao usa .env.production.example e o preflight.
SAFE_DEVELOPMENT_DEFAULTS: dict[str, str] = {
    "PUBLIC_BASE_URL": "http://127.0.0.1:8000",
    "ENABLE_API_DOCS": "true",
    "ENABLE_API_TOKEN_ENDPOINT": "true",
    "API_TOKEN_EXPIRE_MINUTES": "30",
    "REFRESH_TOKEN_EXPIRE_DAYS": "7",
    "REFRESH_ROTATION_GRACE_SECONDS": "30",
    "SESSION_IDLE_MINUTES": "720",
    "SESSION_RETENTION_DAYS": "30",
    "MAX_ACTIVE_SESSIONS_PER_USER": "5",
    "JWT_ALGORITHM": "HS256",
    "JWT_ISSUER": "tms-ciranda",
    "JWT_AUDIENCE": "tms-web",
    "AUTH_COOKIE_NAME": "tms_session",
    "REFRESH_COOKIE_NAME": "tms_refresh",
    "CSRF_COOKIE_NAME": "tms_csrf",
    "COOKIE_SECURE": "false",
    "COOKIE_SAMESITE": "lax",
    "COOKIE_DOMAIN": "",
    "LOGIN_MAX_ATTEMPTS": "3",
    "LOGIN_IP_MAX_ATTEMPTS": "20",
    "LOGIN_LOCK_SECONDS": "30",
    "LOGIN_LOCK_MAX_SECONDS": "300",
    "LOGIN_ATTEMPT_WINDOW_SECONDS": "900",
    "LOGIN_THROTTLE_RETENTION_DAYS": "7",
    "PASSWORD_MIN_LENGTH": "12",
    "BOOTSTRAP_ADMIN_ENABLED": "true",
    "DEMO_SEED_ENABLED": "true",
    "CORS_ORIGINS": "http://127.0.0.1:8000,http://localhost:8000",
    "ALLOWED_HOSTS": "*",
    "FORCE_HTTPS": "false",
    "HSTS_ENABLED": "false",
    "HSTS_MAX_AGE_SECONDS": "31536000",
    "HSTS_INCLUDE_SUBDOMAINS": "true",
    "MAX_REQUEST_BODY_BYTES": "1048576",
    "LOG_LEVEL": "INFO",
    "LOG_FILE": "",
    "LOG_MAX_BYTES": "10485760",
    "LOG_BACKUP_COUNT": "14",
    "BACKUP_DIRECTORY": "../backups",
    "BACKUP_RETENTION_DAYS": "30",
}


def _parse_values(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip().upper()] = value.strip()
    return values


def upgrade_environment() -> tuple[bool, list[str]]:
    if not ENV_PATH.exists():
        if not EXAMPLE_PATH.exists():
            raise RuntimeError("Arquivos .env e .env.example ausentes")
        shutil.copy2(EXAMPLE_PATH, ENV_PATH)
        return True, ["backend/.env criado a partir do modelo seguro de desenvolvimento"]

    original = ENV_PATH.read_text(encoding="utf-8")
    lines = original.splitlines()
    values = _parse_values(lines)
    environment = values.get("ENVIRONMENT", "development").strip().lower()
    if environment in {"production", "producao", "prod"}:
        return False, [
            "ENVIRONMENT=production detectado: o arquivo nao foi alterado automaticamente",
            "valide-o com app.scripts.security_check antes de iniciar",
        ]

    changes: list[str] = []
    replacements: dict[str, str] = {}

    current_secret = values.get("SECRET_KEY", "")
    if not current_secret or current_secret in LEGACY_SECRETS or current_secret.startswith("troque-"):
        replacements["SECRET_KEY"] = secrets.token_urlsafe(64)
        changes.append("SECRET_KEY de desenvolvimento substituida por valor aleatorio")

    if values.get("ACCESS_TOKEN_EXPIRE_MINUTES") == "480":
        replacements["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
        changes.append("duracao do access token reduzida de 480 para 15 minutos")

    output: list[str] = []
    seen: set[str] = set()
    for raw in lines:
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip().upper()
            seen.add(key)
            if key in replacements:
                output.append(f"{key}={replacements[key]}")
                continue
        output.append(raw)

    missing = [key for key in SAFE_DEVELOPMENT_DEFAULTS if key not in seen]
    if missing:
        if output and output[-1].strip():
            output.append("")
        output.append("# Controles adicionados pela atualizacao de seguranca 0.1.4")
        for key in missing:
            output.append(f"{key}={SAFE_DEVELOPMENT_DEFAULTS[key]}")
        changes.append(f"{len(missing)} configuracao(oes) de seguranca adicionada(s)")

    updated = "\n".join(output).rstrip() + "\n"
    if updated == original:
        return False, ["backend/.env ja estava atualizado"]

    if not BACKUP_PATH.exists():
        shutil.copy2(ENV_PATH, BACKUP_PATH)
    ENV_PATH.write_text(updated, encoding="utf-8")
    return True, changes


def main() -> int:
    try:
        changed, messages = upgrade_environment()
    except (OSError, RuntimeError) as exc:
        print(f"Falha ao atualizar o .env: {exc}")
        return 1

    prefix = "[ATUALIZADO]" if changed else "[INFO]"
    for message in messages:
        print(f"{prefix} {message}")
    if changed and BACKUP_PATH.exists():
        print(f"[INFO] Copia anterior preservada em {BACKUP_PATH.name}")
        print("[INFO] Sessoes antigas serao encerradas; usuarios e dados nao foram alterados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
