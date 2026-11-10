"""Senaryo analizi veri modelleri."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import Field

from core.schemas import AeroVantageSchema


class ScenarioRequest(AeroVantageSchema):
    """What-if senaryo parametreleri."""

    asset_id: str = Field(..., min_length=1)
    target_date: Optional[date] = None
    wind_adjustment_pct: float = Field(default=0.0, ge=-50, le=50, description="Rüzgar değişimi %")
    ptf_adjustment_pct: float = Field(default=0.0, ge=-30, le=30, description="PTF değişimi %")
    turbines_down: int = Field(default=0, ge=0, le=50, description="Devre dışı türbin sayısı")


class ScenarioResult(AeroVantageSchema):
    """Senaryo simülasyon sonucu."""

    scenario_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime
    asset_id: str
    target_date: date
    baseline_forecast_mw: float
    adjusted_forecast_mw: float
    baseline_cost_tl: float
    adjusted_cost_tl: float
    baseline_risk_score: int
    adjusted_risk_score: int
    capacity_impact_mw: float
    summary: str
    parameters: ScenarioRequest
