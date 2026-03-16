from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import Base, engine
from models import models
from models import delivery as delivery_model
from routers import vehicles, routes, tracking, deliveries

# Cria tabelas no banco (incluindo deliveries)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TMS – Sistema de Gestão de Frota",
    description="API para gerenciamento de frota própria com roteirização e rastreamento em tempo real.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vehicles.router)
app.include_router(routes.router)
app.include_router(tracking.router)
app.include_router(deliveries.router)

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "sistema": "TMS - Gestão de Frota"}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
