"""Piyasa verisi API rotaları."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Query

from modules.data_hub.epias import EpiasClient

router = APIRouter()
_epias = EpiasClient()


@router.get("/ptf")
def get_ptf(
    delivery_date: Optional[date] = Query(default=None, description="Teslimat tarihi"),
) -> dict[str, Any]:
    """Gün öncesi PTF verisini döndürür."""
    target = delivery_date or date.today()
    response = _epias.fetch_day_ahead_ptf(target)
    return response.model_dump(mode="json")


@router.get("/smf")
def get_smf(
    delivery_date: Optional[date] = Query(default=None, description="Teslimat tarihi"),
) -> dict[str, Any]:
    """Sistem Marjinal Fiyat (SMF) verisini döndürür."""
    target = delivery_date or date.today()
    response = _epias.fetch_system_marginal_price(target)
    return response.model_dump(mode="json")
