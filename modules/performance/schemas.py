"""Performans izleme veri modelleri."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import Field

from core.schemas import AeroVantageSchema


class PerformanceData(AeroVantageSchema):
    """Tek saatlik performans ve sapma kaydı."""

    timestamp: datetime = Field(..., description="Performans ölçüm zaman damgası (UTC)")
    forecast_mw: float = Field(..., ge=0, description="Tahmini üretim (MW)")
    actual_mw: float = Field(..., ge=0, description="Gerçekleşen üretim (MW)")
    deviation_mw: float = Field(..., description="Sapma (actual - forecast) (MW)")
    mape_percentage: float = Field(..., ge=0, description="Mutlak yüzde hata (%)")
    observed: bool = Field(
        default=True,
        description="Ground-truth saati gözlemlendi mi (pad/eksik EPİAŞ saatleri False)",
    )


class PerformanceEvaluationResponse(AeroVantageSchema):
    """Günlük saatlik performans değerlendirme seti."""

    hours: List[PerformanceData] = Field(..., min_length=1, description="Saatlik performans verileri")
