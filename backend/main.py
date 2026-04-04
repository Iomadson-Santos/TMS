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

_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://silver-marshmallow-cfc324.netlify.app",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "*"
    ],
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
    return {"ok": True, "service": "tms-api", "allowed_origins": ALLOWED_ORIGINS}


@app.get("/health")
def health():
    return {"status": "ok", "allowed_origins": ALLOWED_ORIGINS}
