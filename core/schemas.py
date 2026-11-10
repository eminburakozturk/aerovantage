"""Shared, extensible domain schemas for AeroVantage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AeroVantageSchema(BaseModel):
    """Base schema with strict validation defaults for all domain models."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class Timestamp(AeroVantageSchema):
    """UTC-normalized timestamp wrapper for consistent time handling."""

    value: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC-aware datetime value",
    )

    @field_validator("value", mode="before")
    @classmethod
    def ensure_utc(cls, raw: Any) -> datetime:
        if isinstance(raw, datetime):
            if raw.tzinfo is None:
                return raw.replace(tzinfo=timezone.utc)
            return raw.astimezone(timezone.utc)
        raise TypeError("Timestamp.value must be a datetime instance")


class BaseAsset(AeroVantageSchema):
    """Minimal asset identity model; extend in domain modules as needed."""

    id: UUID = Field(default_factory=uuid4, description="Unique asset identifier")
    symbol: str = Field(..., min_length=1, max_length=32, description="Trading symbol")
    name: Optional[str] = Field(default=None, description="Human-readable asset name")
    created_at: Timestamp = Field(
        default_factory=Timestamp,
        description="Asset record creation time",
    )
