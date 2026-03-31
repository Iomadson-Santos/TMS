import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from deliveries import router as deliveries_router
from vehicles import router as vehicles_router
from routes import router as routes_router
from tracking import router as tracking_router

app = FastAPI(
    title="TMS API",
    version="1.0.0",
)

# FIX: allow_origins=["*"] com allow_credentials=True é inválido pela spec CORS —
# navegadores rejeitam a resposta quando credentials estão habilitadas e a origem
# é um wildcard. Origens permitidas devem ser listadas explicitamente.
# Configure a variável ALLOWED_ORIGINS no ambiente (vírgula-separado).
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deliveries_router)
app.include_router(vehicles_router)
app.include_router(routes_router)
app.include_router(tracking_router)


@app.get("/")
def root():
    return {"ok": True, "service": "tms-api"}


@app.get("/health")
def health():
    return {"status": "ok"}
