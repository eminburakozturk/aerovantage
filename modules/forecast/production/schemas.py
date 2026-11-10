"""Üretim tahmini veri modelleri."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from core.schemas import AeroVantageSchema


class ProductionData(AeroVantageSchema):
    """Tek saatlik üretim tahmin kaydı."""

    timestamp: datetime = Field(..., description="Üretim zaman damgası (UTC)")
    generated_mw: float = Field(..., ge=0, description="Tahmini üretim gücü (MW)")


class ProductionForecastResponse(AeroVantageSchema):
    """Günlük saatlik üretim tahmin seti."""

    hours: List[ProductionData] = Field(..., min_length=1, description="Saatlik üretim verileri")
    total_daily_mw: float = Field(..., ge=0, description="Günlük toplam üretim (MW·saat)")
    source: str = Field(default="forecast", description="Tahminin beslendiği veri kaynağı")
    attribution: Optional[dict] = Field(default=None, description="Model feature attribution raporu")
