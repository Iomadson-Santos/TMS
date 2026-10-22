from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_SECRET_KEY = "troque-esta-chave-secreta-por-uma-chave-com-mais-de-48-caracteres"
DEFAULT_BOOTSTRAP_PASSWORD = "Admin123!"


class Settings(BaseSettings):
    app_name: str = "TMS Ciranda"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    public_base_url: str = ""
    enable_api_docs: bool = True
    enable_api_token_endpoint: bool = True

    secret_key: str = DEFAULT_SECRET_KEY
    access_token_expire_minutes: int = Field(default=15, ge=5, le=480)
    api_token_expire_minutes: int = Field(default=30, ge=5, le=480)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)
    refresh_rotation_grace_seconds: int = Field(default=30, ge=0, le=300)
    session_idle_minutes: int = Field(default=720, ge=15, le=43_200)
    session_retention_days: int = Field(default=30, ge=1, le=3650)
    max_active_sessions_per_user: int = Field(default=5, ge=1, le=50)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "tms-ciranda"
    jwt_audience: str = "tms-web"

    auth_cookie_name: str = "tms_session"
    refresh_cookie_name: str = "tms_refresh"
    csrf_cookie_name: str = "tms_csrf"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None

    # A terceira falha bloqueia o identificador por 30 segundos. Novas sequencias
    # dentro da janela dobram o bloqueio ate LOGIN_LOCK_MAX_SECONDS.
    login_max_attempts: int = Field(default=3, ge=2, le=20)
    login_ip_max_attempts: int = Field(default=20, ge=3, le=500)
    login_lock_seconds: int = Field(default=30, ge=5, le=3600)
    login_lock_max_seconds: int = Field(default=300, ge=5, le=86_400)
    login_attempt_window_seconds: int = Field(default=900, ge=30, le=86_400)
    login_throttle_retention_days: int = Field(default=7, ge=1, le=365)
    password_min_length: int = Field(default=12, ge=8, le=64)

    database_url: str = "sqlite:///./tms.db"
    auto_create_tables: bool = True

    tracking_online_seconds: int = Field(default=120, ge=10, le=3600)
    tracking_retention_days: int = Field(default=90, ge=0, le=3650)
    tracking_min_interval_seconds: int = Field(default=2, ge=1, le=60)

    bootstrap_admin_enabled: bool = True
    bootstrap_admin_name: str = "Administrador TMS"
    bootstrap_admin_email: str = "admin@tmsciranda.com.br"
    bootstrap_admin_password: str = DEFAULT_BOOTSTRAP_PASSWORD
    demo_seed_enabled: bool = True

    cors_origins: str = Field(
        default=(
            "http://127.0.0.1:5500,http://localhost:5500,"
            "http://127.0.0.1:8000,http://localhost:8000"
        )
    )
    allowed_hosts: str = "*"
    force_https: bool = False
    platform_https_enforced: bool = False
    hsts_enabled: bool = False
    hsts_max_age_seconds: int = Field(default=31_536_000, ge=0, le=63_072_000)
    hsts_include_subdomains: bool = True
    max_request_body_bytes: int = Field(default=1_048_576, ge=65_536, le=52_428_800)

    default_page_size: int = Field(default=200, ge=10, le=1000)
    max_page_size: int = Field(default=1000, ge=50, le=5000)

    log_level: str = "INFO"
    log_to_stdout: bool = True
    log_file: str = ""
    log_max_bytes: int = Field(default=10_485_760, ge=1_048_576, le=1_073_741_824)
    log_backup_count: int = Field(default=14, ge=1, le=365)

    backup_directory: str = "../backups"
    backup_retention_days: int = Field(default=30, ge=1, le=3650)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("cookie_samesite")
    @classmethod
    def validate_samesite(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE deve ser lax, strict ou none")
        return normalized

    @field_validator("auth_cookie_name", "refresh_cookie_name", "csrf_cookie_name")
    @classmethod
    def validate_cookie_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or any(character in normalized for character in " ;,\r\n\t"):
            raise ValueError("Nome de cookie invalido")
        return normalized

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("LOG_LEVEL invalido")
        return normalized

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Normaliza URLs PostgreSQL de provedores para o driver psycopg 3."""

        normalized = value.strip()
        if normalized.startswith("postgres://"):
            return "postgresql+psycopg://" + normalized[len("postgres://") :]
        if normalized.startswith("postgresql://"):
            return "postgresql+psycopg://" + normalized[len("postgresql://") :]
        return normalized

    @property
    def is_production(self) -> bool:
        return self.environment in {"production", "producao", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            item.strip().rstrip("/")
            for item in self.cors_origins.split(",")
            if item.strip()
        ]

    @property
    def allowed_host_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_hosts.split(",") if item.strip()]

    @property
    def access_token_max_age_seconds(self) -> int:
        return self.access_token_expire_minutes * 60

    @property
    def refresh_token_max_age_seconds(self) -> int:
        return self.refresh_token_expire_days * 86_400

    @property
    def resolved_log_file(self) -> Path | None:
        value = self.log_file.strip()
        return Path(value).expanduser() if value else None

    @property
    def backup_path(self) -> Path:
        return Path(self.backup_directory).expanduser()

    def production_security_errors(self) -> list[str]:
        """Retorna configuracoes que tornam uma publicacao insegura.

        O servidor recusa iniciar em ENVIRONMENT=production enquanto houver erros.
        Isso evita publicar acidentalmente chaves, credenciais ou banco de teste.
        """

        if not self.is_production:
            return []

        errors: list[str] = []
        weak_secret = (
            self.secret_key == DEFAULT_SECRET_KEY
            or self.secret_key.startswith("troque-")
            or len(self.secret_key) < 40
            or len(set(self.secret_key)) < 16
        )
        if weak_secret:
            errors.append("SECRET_KEY deve ser aleatoria, diversa e ter pelo menos 40 caracteres")
        if self.jwt_algorithm != "HS256":
            errors.append("JWT_ALGORITHM deve permanecer HS256 nesta versao")
        if self.database_url.lower().startswith("sqlite"):
            errors.append("DATABASE_URL deve usar PostgreSQL em producao")
        if self.auto_create_tables:
            errors.append("AUTO_CREATE_TABLES deve ser false em producao")
        if self.bootstrap_admin_enabled:
            errors.append("BOOTSTRAP_ADMIN_ENABLED deve ser false em producao")
        if self.demo_seed_enabled:
            errors.append("DEMO_SEED_ENABLED deve ser false em producao")
        if self.bootstrap_admin_enabled and self.bootstrap_admin_password == DEFAULT_BOOTSTRAP_PASSWORD:
            errors.append("BOOTSTRAP_ADMIN_PASSWORD nao pode usar a senha de demonstracao")
        if not self.cookie_secure:
            errors.append("COOKIE_SECURE deve ser true em producao")

        cookie_names = {
            "AUTH_COOKIE_NAME": self.auth_cookie_name,
            "REFRESH_COOKIE_NAME": self.refresh_cookie_name,
            "CSRF_COOKIE_NAME": self.csrf_cookie_name,
        }
        if len(set(cookie_names.values())) != len(cookie_names):
            errors.append("Os nomes dos cookies de sessao, refresh e CSRF devem ser diferentes")
        for setting_name, cookie_name in cookie_names.items():
            if not cookie_name.startswith("__Host-"):
                errors.append(f"{setting_name} deve usar o prefixo __Host- em producao")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            errors.append("COOKIE_SAMESITE=none exige COOKIE_SECURE=true")
        if self.cookie_domain:
            errors.append("COOKIE_DOMAIN deve ficar vazio para limitar o cookie ao host")

        if self.enable_api_docs:
            errors.append("ENABLE_API_DOCS deve ser false em producao")
        if self.enable_api_token_endpoint:
            errors.append("ENABLE_API_TOKEN_ENDPOINT deve ser false, salvo integracao aprovada")

        parsed_public_url = urlparse(self.public_base_url)
        if parsed_public_url.scheme != "https" or not parsed_public_url.netloc:
            errors.append("PUBLIC_BASE_URL deve ser uma URL https valida em producao")
        if parsed_public_url.username or parsed_public_url.password:
            errors.append("PUBLIC_BASE_URL nao pode conter credenciais")

        if not self.allowed_host_list or "*" in self.allowed_host_list:
            errors.append("ALLOWED_HOSTS deve conter apenas os dominios/IPs publicados")
        if "*" in self.cors_origin_list:
            errors.append("CORS_ORIGINS nao pode conter * em producao")
        if any(urlparse(item).scheme != "https" or not urlparse(item).netloc for item in self.cors_origin_list):
            errors.append("Todas as CORS_ORIGINS devem ser URLs https validas")

        if self.password_min_length < 15:
            errors.append("PASSWORD_MIN_LENGTH deve ser pelo menos 15 sem MFA")
        if self.login_max_attempts > 3:
            errors.append("LOGIN_MAX_ATTEMPTS deve ser no maximo 3 em producao")
        if self.login_lock_seconds < 30:
            errors.append("LOGIN_LOCK_SECONDS deve ser pelo menos 30 em producao")
        if self.login_lock_max_seconds < self.login_lock_seconds:
            errors.append("LOGIN_LOCK_MAX_SECONDS nao pode ser menor que LOGIN_LOCK_SECONDS")
        if self.access_token_expire_minutes > 15:
            errors.append("ACCESS_TOKEN_EXPIRE_MINUTES deve ser no maximo 15 em producao")
        if self.api_token_expire_minutes > 30:
            errors.append("API_TOKEN_EXPIRE_MINUTES deve ser no maximo 30 em producao")
        if self.refresh_token_expire_days > 7:
            errors.append("REFRESH_TOKEN_EXPIRE_DAYS deve ser no maximo 7 em producao")
        if self.refresh_rotation_grace_seconds > 60:
            errors.append("REFRESH_ROTATION_GRACE_SECONDS deve ser no maximo 60")
        if self.session_idle_minutes > 1440:
            errors.append("SESSION_IDLE_MINUTES deve ser no maximo 1440 em producao")
        if self.max_active_sessions_per_user > 5:
            errors.append("MAX_ACTIVE_SESSIONS_PER_USER deve ser no maximo 5")

        if not self.hsts_enabled:
            errors.append("HSTS_ENABLED deve ser true depois que HTTPS estiver validado")
        if not self.force_https and not self.platform_https_enforced:
            errors.append(
                "Ative FORCE_HTTPS ou PLATFORM_HTTPS_ENFORCED quando o proxy da plataforma "
                "redirecionar todo HTTP para HTTPS"
            )
        if not self.log_to_stdout and not self.resolved_log_file:
            errors.append("Ative LOG_TO_STDOUT ou configure LOG_FILE em producao")
        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
