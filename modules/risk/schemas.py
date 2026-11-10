"""Risk değerlendirme veri modelleri."""

from __future__ import annotations

from datetime import date as DateType
from datetime import datetime
from typing import List

from pydantic import ConfigDict, Field

from core.schemas import AeroVantageSchema


class HourlyRiskData(AeroVantageSchema):
    """Tek saatlik dengesizlik ve maliyet kaydı."""

    timestamp: datetime = Field(..., description="Risk hesaplama zaman damgası (UTC)")
    forecast_mw: float = Field(..., ge=0, description="Tahmini üretim (MW)")
    actual_mw: float = Field(..., ge=0, description="Gerçekleşen üretim (MW)")
    ptf_price: float = Field(..., ge=0, description="Saatlik PTF (TL/MWh)")
    imbalance_cost_tl: float = Field(..., ge=0, description="Saatlik dengesizlik maliyeti (TL)")


class DailyRiskScoreResponse(AeroVantageSchema):
    """Günlük risk skoru ve saatlik detay seti."""

    model_config = ConfigDict(serialize_by_alias=True)

    target_date: DateType = Field(
        ...,
        serialization_alias="date",
        description="Değerlendirme tarihi",
    )
    total_imbalance_cost_tl: float = Field(..., ge=0, description="Toplam dengesizlik maliyeti (TL)")
    risk_score: int = Field(..., ge=0, le=100, description="Normalize risk skoru (0–100)")
    hours: List[HourlyRiskData] = Field(..., min_length=1, description="Saatlik risk verileri")
    market_source: str = Field(default="epias", description="Risk hesabında kullanılan piyasa veri kaynağı")
