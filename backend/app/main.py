from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import models  # noqa: F401 - registra os modelos no metadata
from app.core.config import settings
from app.core.database import SessionLocal, create_database_tables
from app.core.logging_config import configure_logging
from app.core.middleware import (
    BrowserRequestProtectionMiddleware,
    RequestBodyLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.routers import audit, auth, dashboard, deliveries, health, routes, tracking, users, vehicles
from app.services.bootstrap import ensure_bootstrap_admin


configure_logging()
logger = logging.getLogger("tms")


@asynccontextmanager
async def lifespan(_: FastAPI):
    security_errors = settings.production_security_errors()
    if security_errors:
        formatted = "\n - ".join(security_errors)
        raise RuntimeError(
            "Configuracao insegura para producao. Corrija antes de iniciar:\n - "
            f"{formatted}"
        )

    if settings.auto_create_tables:
        create_database_tables()
    if settings.bootstrap_admin_enabled:
        with SessionLocal() as db:
            ensure_bootstrap_admin(db)
    yield


docs_url = "/docs" if settings.enable_api_docs else None
redoc_url = "/redoc" if settings.enable_api_docs else None
openapi_url = "/openapi.json" if settings.enable_api_docs else None

app = FastAPI(
    title=settings.app_name,
    version="1.0.0-rc1",
    description="API do TMS para gestao de entregas, veiculos, rotas e rastreamento.",
    lifespan=lifespan,
    debug=settings.debug and not settings.is_production,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

app.add_middleware(
    RequestBodyLimitMiddleware,
    max_bytes=settings.max_request_body_bytes,
)
app.add_middleware(BrowserRequestProtectionMiddleware)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["Retry-After", "X-Request-ID"],
        max_age=600,
    )

if settings.force_https:
    app.add_middleware(HTTPSRedirectMiddleware)

if settings.allowed_host_list and "*" not in settings.allowed_host_list:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_host_list,
        www_redirect=False,
    )

# Deve ser a camada externa para adicionar cabecalhos inclusive em respostas
# produzidas pelos outros middlewares.
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Retorna erros de validacao sem ecoar senhas ou outros valores recebidos."""

    request_id = getattr(request.state, "request_id", "unknown")
    sanitized = [
        {
            "loc": list(error.get("loc", ())),
            "msg": str(error.get("msg", "Valor invalido")),
            "type": str(error.get("type", "value_error")),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"detail": sanitized, "request_id": request_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Erro interno request_id=%s path=%s", request_id, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno do servidor",
            "request_id": request_id,
        },
    )


prefix = settings.api_v1_prefix
app.include_router(health.router, prefix=prefix)
app.include_router(auth.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)
app.include_router(vehicles.router, prefix=prefix)
app.include_router(deliveries.router, prefix=prefix)
app.include_router(routes.router, prefix=prefix)
app.include_router(tracking.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)
app.include_router(audit.router, prefix=prefix)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


def frontend_response(filename: str):
    file_path = FRONTEND_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)
    return JSONResponse(
        status_code=404,
        content={"detail": f"Arquivo de frontend ausente: {filename}"},
    )


@app.get("/", include_in_schema=False)
@app.get("/login.html", include_in_schema=False)
def login_page():
    return frontend_response("login.html")


@app.get("/login", include_in_schema=False)
def login_alias():
    return frontend_response("login.html")


@app.get("/change-password", include_in_schema=False)
@app.get("/change-password.html", include_in_schema=False)
def change_password_page():
    return frontend_response("change-password.html")


@app.get("/dashboard", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
def dashboard_page():
    return frontend_response("index.html")


@app.get("/vehicles", include_in_schema=False)
@app.get("/vehicles.html", include_in_schema=False)
def vehicles_page():
    return frontend_response("vehicles.html")


@app.get("/deliveries", include_in_schema=False)
@app.get("/deliveries.html", include_in_schema=False)
def deliveries_page():
    return frontend_response("deliveries.html")


@app.get("/routes", include_in_schema=False)
@app.get("/routes.html", include_in_schema=False)
@app.get("/routers", include_in_schema=False)
@app.get("/routers.html", include_in_schema=False)
def routes_page():
    return frontend_response("routes.html")


@app.get("/tracking", include_in_schema=False)
@app.get("/tracking.html", include_in_schema=False)
@app.get("/rastreamento", include_in_schema=False)
def tracking_page():
    return frontend_response("tracking.html")


@app.get("/users", include_in_schema=False)
@app.get("/users.html", include_in_schema=False)
def users_page():
    return frontend_response("users.html")


@app.get("/audit", include_in_schema=False)
@app.get("/audit.html", include_in_schema=False)
def audit_page():
    return frontend_response("audit.html")


@app.get("/motorista", include_in_schema=False)
@app.get("/motorista.html", include_in_schema=False)
@app.get("/driver", include_in_schema=False)
@app.get("/mobile-driver", include_in_schema=False)
def driver_mobile_page():
    return frontend_response("driver.html")
