"""Portföy varlık kaydı servisi."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

_ASSETS_PATH = Path(__file__).resolve().parent / "data" / "assets.json"
_TURBINES_PATH = Path(__file__).resolve().parent / "data" / "turbines.json"


@dataclass(frozen=True)
class Asset:
    """Santral / portföy varlığı."""

    id: str
    name: str
    type: str
    lat: float
    lon: float
    capacity_mw: float


class AssetRegistryService:
    """JSON tabanlı varlık kaydı okuyucusu."""

    def __init__(self, assets_path: Path | None = None) -> None:
        self._assets_path = assets_path or _ASSETS_PATH
        self._assets = self._load_assets()
        self._turbines = self._load_turbines()

    def _load_turbines(self) -> dict[str, list[dict[str, object]]]:
        if not _TURBINES_PATH.exists():
            return {}
        with _TURBINES_PATH.open(encoding="utf-8") as handle:
            return json.load(handle)

    def _load_assets(self) -> list[Asset]:
        with self._assets_path.open(encoding="utf-8") as handle:
            raw_assets = json.load(handle)
        return [Asset(**entry) for entry in raw_assets]

    def get_all_assets(self) -> List[Asset]:
        """Tüm kayıtlı varlıkları döndürür."""
        return list(self._assets)

    def get_asset_by_id(self, asset_id: str) -> Asset:
        """ID ile tek varlık döndürür."""
        for asset in self._assets:
            if asset.id == asset_id:
                return asset
        raise KeyError(f"Asset not found: {asset_id}")

    def get_turbines(self, asset_id: str) -> list[dict[str, object]]:
        """Santrale ait türbin envanterini döndürür."""
        return list(self._turbines.get(asset_id, []))
