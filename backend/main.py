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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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