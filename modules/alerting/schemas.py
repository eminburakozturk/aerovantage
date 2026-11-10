"""Uyarı ve bildirim veri modelleri."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field

from core.schemas import AeroVantageSchema

AlertSeverity = Literal["INFO", "WARNING", "CRITICAL"]


class Alert(AeroVantageSchema):
    """Operasyonel risk uyarısı."""

    alert_id: UUID = Field(default_factory=uuid4, description="Benzersiz uyarı kimliği")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Uyarı oluşturulma zamanı (UTC)",
    )
    asset_id: str = Field(..., min_length=1, description="İlgili santral kimliği")
    severity: AlertSeverity = Field(..., description="Uyarı şiddeti")
    message: str = Field(..., min_length=1, description="Uyarı mesajı")
