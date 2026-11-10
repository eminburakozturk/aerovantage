"""Risk API rotaları."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from modules.forecast.production.services import ProductionForecastService
from modules.performance.service import PerformanceMonitoringService
from modules.risk.schemas import DailyRiskScoreResponse
from modules.risk.scoring import RiskScoringService

router = APIRouter()
_production_service = ProductionForecastService()
_performance_service = PerformanceMonitoringService()
_risk_service = RiskScoringService()


@router.get("/daily", response_model=DailyRiskScoreResponse)
def get_daily_risk(
    lat: float,
    lon: float,
    target_date: date,
) -> DailyRiskScoreResponse:
    """Günlük risk skorunu forecast, performans ve PTF verilerinden hesaplar."""
    forecast = _production_service.forecast_daily_production(lat, lon, target_date)
    performance = _performance_service.evaluate_performance(
        forecast.model_dump(mode="json"),
        target_date=target_date.isoformat(),
        asset_id=f"GEO-{lat:.2f}-{lon:.2f}",
    )
    return _risk_service.calculate_daily_risk(target_date, performance)
