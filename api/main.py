"""AeroVantage FastAPI uygulaması."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import verify_api_key
from api.routes.admin import router as admin_router
from api.routes.ai_routes import router as ai_router
from api.routes.assets import router as assets_router
from api.routes.market import router as market_router
from api.routes.monitoring import router as monitoring_router
from api.routes.pipeline import router as pipeline_router
from api.routes.reporting import router as reporting_router
from api.routes.risk import router as risk_router
from api.routes.scenarios import router as scenarios_router
from api.routes.weather import router as weather_router
from core.health import HealthMonitor
from core.logger import get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = get_logger("api")
    logger.info("AeroVantage API başlatıldı")
    yield


app = FastAPI(title="AeroVantage API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_api_auth = [Depends(verify_api_key)]

app.include_router(risk_router, prefix="/api/v1/risk", tags=["risk"], dependencies=_api_auth)
app.include_router(assets_router, prefix="/api/v1/assets", tags=["assets"], dependencies=_api_auth)
app.include_router(
    pipeline_router,
    prefix="/api/v1/pipeline",
    tags=["pipeline"],
    dependencies=_api_auth,
)
app.include_router(
    reporting_router,
    prefix="/api/v1/reporting",
    tags=["reporting"],
    dependencies=_api_auth,
)
app.include_router(
    market_router,
    prefix="/api/v1/market",
    tags=["market"],
    dependencies=_api_auth,
)
app.include_router(
    weather_router,
    prefix="/api/v1/weather",
    tags=["weather"],
    dependencies=_api_auth,
)
app.include_router(
    scenarios_router,
    prefix="/api/v1/scenarios",
    tags=["scenarios"],
    dependencies=_api_auth,
)
app.include_router(
    monitoring_router,
    prefix="/api/v1/monitoring",
    tags=["monitoring"],
    dependencies=_api_auth,
)
app.include_router(
    ai_router,
    prefix="/api/v1/ai",
    tags=["ai"],
    dependencies=_api_auth,
)
app.include_router(
    admin_router,
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=_api_auth,
)


@app.get("/health")
def health() -> dict[str, object]:
    """Servis ve Data Hub sağlık durumu."""
    return HealthMonitor().get_overall_status()
