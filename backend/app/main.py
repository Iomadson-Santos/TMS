from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.database.base import Base
from app.database.session import engine
from app.routers import deliveries, routes, tracking, vehicles

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(deliveries.router)
app.include_router(vehicles.router)
app.include_router(routes.router)
app.include_router(tracking.router)


@app.get("/")
def root():
    return {"ok": True, "service": "tms-api", "version": settings.app_version}


@app.get("/health")
def health():
    return {"status": "ok"}
