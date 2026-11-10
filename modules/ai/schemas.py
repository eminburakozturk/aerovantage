"""AI karar destek yanıt modelleri."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from core.schemas import AeroVantageSchema


class AIResponse(AeroVantageSchema):
    """LLM veya playbook tabanlı operasyonel öneri yanıtı."""

    insight: str = Field(..., min_length=1, description="Tek paragraflık analiz ve tavsiye")
    action_plan: str = Field(
        ...,
        min_length=1,
        description="Eyleme dönüştürülebilir operasyonel aksiyon",
    )
    source: str = Field(
        default="unknown",
        min_length=1,
        description="Yanıt kaynağı (mock, openai, gemini, fallback)",
    )


class DecisionHistory(AeroVantageSchema):
    """AI karar geçmişi kaydı."""

    recorded_at: datetime = Field(..., description="Kayıt zamanı (UTC)")
    source: str = Field(..., min_length=1, description="Yanıt kaynağı (mock, openai, gemini)")
    asset_id: Optional[str] = Field(default=None, description="İlgili santral kimliği")
    risk_score: Optional[int] = Field(default=None, ge=0, le=100)
    insight: str = Field(..., min_length=1)
    action_plan: str = Field(..., min_length=1)
