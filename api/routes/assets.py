"""Varlık kaydı API rotaları."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modules.asset_registry.service import AssetRegistryService

router = APIRouter()
_registry = AssetRegistryService()


class AssetResponse(BaseModel):
    """API varlık yanıt modeli."""

    id: str
    name: str
    type: str
    lat: float
    lon: float
    capacity_mw: float


@router.get("", response_model=list[AssetResponse])
def list_assets() -> list[AssetResponse]:
    """Portföydeki tüm santralleri listeler."""
    return [
        AssetResponse(
            id=asset.id,
            name=asset.name,
            type=asset.type,
            lat=asset.lat,
            lon=asset.lon,
            capacity_mw=asset.capacity_mw,
        )
        for asset in _registry.get_all_assets()
    ]


class TurbineResponse(BaseModel):
    """Türbin envanter yanıt modeli."""

    id: str
    model: str
    capacity_mw: float
    status: str
    health_score: int


@router.get("/{asset_id}/turbines", response_model=list[TurbineResponse])
def list_turbines(asset_id: str) -> list[TurbineResponse]:
    """Santrale ait türbin envanterini döndürür."""
    try:
        _registry.get_asset_by_id(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [TurbineResponse(**turbine) for turbine in _registry.get_turbines(asset_id)]
