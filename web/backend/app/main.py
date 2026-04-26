"""TerraMoist backend - FastAPI application.

Run locally with:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth_routes import router as auth_router
from app.api.irrigation_routes import router as irrigation_router
from app.api.routes import router as api_router
from app.api.simulation_routes import router as simulation_router
from app.core.config import get_settings
from app.services.auth import AuthService
from app.services.cdse_auth import CDSETokenManager
from app.services.irrigation import IrrigationEngine, IrrigationHistoryStore
from app.services.sentinel_hub import SentinelHubClient
from simulare.service import SimulationService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("terramoist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build shared async resources once per process, tear them down cleanly.

    A single httpx.AsyncClient is reused across all requests so TCP
    connections to CDSE can be pooled.
    """
    settings = get_settings()
    http_client = httpx.AsyncClient()
    token_manager = CDSETokenManager(settings, http_client)
    sh_client = SentinelHubClient(settings, token_manager, http_client)
    auth_service = AuthService(
        db_path=settings.auth_db_path,
        secret_key=settings.auth_secret_key,
        token_ttl_seconds=settings.auth_token_ttl_seconds,
    )
    irrigation_store = IrrigationHistoryStore(settings.auth_db_path)
    irrigation_engine = IrrigationEngine(irrigation_store)

    app.state.settings = settings
    app.state.http_client = http_client
    app.state.token_manager = token_manager
    app.state.sentinel_hub = sh_client
    app.state.auth_service = auth_service
    app.state.irrigation_engine = irrigation_engine
    app.state.simulation_service = SimulationService()

    logger.info("TerraMoist backend ready")
    try:
        yield
    finally:
        await http_client.aclose()


app = FastAPI(
    title="TerraMoist API",
    description=(
        "Precision soil-moisture tiles for sustainable farming. "
        "Powered by the Copernicus Data Space Ecosystem."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - allow the React dev server to call us during development.
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(irrigation_router)
app.include_router(simulation_router)


@app.get("/")
async def root() -> dict:
    """Landing endpoint with pointers to docs and health."""
    return {
        "service": "TerraMoist API",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
