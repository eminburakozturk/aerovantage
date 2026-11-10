"""Raporlama ve uyum veri modelleri."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from core.schemas import AeroVantageSchema


class ExecutiveReportResponse(AeroVantageSchema):
    """Yönetici özeti raporu — finansal ve operasyonel KPI özeti (+ R1 Intelligence Pack)."""

    report_id: UUID = Field(default_factory=uuid4, description="Benzersiz rapor kimliği")
    generated_at: datetime = Field(..., description="Rapor üretim zamanı (UTC)")
    asset_id: str = Field(..., min_length=1, description="Santral kimliği")
    period_days: int = Field(..., ge=1, description="Analiz edilen gün aralığı")
    total_imbalance_cost_tl: float = Field(..., ge=0, description="Toplam dengesizlik maliyeti (TL)")
    average_mape: float = Field(..., ge=0, description="Ortalama tahmin hata payı (%)")
    critical_alerts_count: int = Field(..., ge=0, description="Kritik uyarı sayısı")
    executive_summary: str = Field(..., min_length=1, description="Yönetici durum özeti")

    # R1 Intelligence Pack (additive — eski istemciler yok sayabilir)
    run_count: int = Field(default=0, ge=0, description="Analiz edilen benzersiz kayıt sayısı")
    scorecards: list[dict[str, Any]] = Field(default_factory=list)
    ai_brief: dict[str, Any] = Field(default_factory=dict)
    financial: dict[str, Any] = Field(default_factory=dict)
    forecast: dict[str, Any] = Field(default_factory=dict)
    operational: dict[str, Any] = Field(default_factory=dict)
    risk: dict[str, Any] = Field(default_factory=dict)
    data_intelligence: dict[str, Any] = Field(default_factory=dict)
    model_intelligence: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    trends: dict[str, Any] = Field(default_factory=dict)
    benchmark: dict[str, Any] = Field(default_factory=dict)
    conclusion: str = Field(default="", description="Yönetici sonuç paragrafı")
    mape_informational: bool = Field(default=False, description="MAPE simülasyon/bilgi bayrağı")
    report_type: str = Field(default="executive", description="Rapor görünüm tipi")
    changes_since_last: dict[str, Any] = Field(default_factory=dict)
    visible_sections: list[str] = Field(default_factory=list)
    adaptive_hint: str = Field(default="", description="Önerilen rapor tipi açıklaması")
