"""Meteoroloji API rotaları."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from modules.asset_registry.service import AssetRegistryService
from modules.data_hub.weather import WeatherClient

router = APIRouter()
_weather = WeatherClient()
_registry = AssetRegistryService()


@router.get("/forecast")
def get_weather_forecast(
    asset_id: str = Query(..., description="Santral kimliği"),
    target_date: Optional[date] = Query(default=None, description="Hedef tarih"),
) -> dict[str, Any]:
    """Santral koordinatları için saatlik hava tahmini döndürür."""
    try:
        asset = _registry.get_asset_by_id(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    target = target_date or date.today()
    response = _weather.fetch_hourly_forecast(asset.lat, asset.lon, target)
    payload = response.model_dump(mode="json")
    payload["asset_id"] = asset.id
    payload["asset_name"] = asset.name
    return payload
