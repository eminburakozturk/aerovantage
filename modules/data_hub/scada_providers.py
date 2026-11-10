"""SCADA generation providers — adapter arkası; OI katmanı değişmez.

MVP: EpiasSimulatedScadaProvider (EPİAŞ'tan türetilmiş simülasyon)
İleride: LiveRestScadaProvider (fiziksel SCADA REST)
"""

from __future__ import annotations

import hashlib
import random
from datetime import date, datetime
from typing import Any, Optional, Protocol

import requests
from requests import Session

from core.logger import get_logger
from modules.asset_registry.service import AssetRegistryService
from modules.data_hub.epias import EpiasClient
from modules.data_hub.ground_truth import enrich_scada_layer_meta

_NOISE_MIN = 0.85
_NOISE_MAX = 1.15
_TURKEY_WIND_CAPACITY_REF_MW = 12_000.0

# Operatör / UI — yalnızca operational MW; equipment telemetrisi değildir
SCADA_SIMULATED_LABEL = "Operational: EPİAŞ Derived (MW) · Equipment: Mock"


class ScadaGenerationProvider(Protocol):
    """Saatlik aktif güç (MW) sağlayıcısı — equipment telemetrisi değil."""

    def ping(self) -> dict[str, Any]:
        ...

    def fetch(self, asset_id: str, target_date: str) -> dict[str, float]:
        ...

    def get_last_meta(self) -> dict[str, Any]:
        ...


def _parse_target_date(target_date: str) -> date:
    if "T" in target_date:
        return datetime.fromisoformat(target_date.replace("Z", "+00:00")).date()
    return date.fromisoformat(target_date)


def _parse_generation_payload(payload: Any) -> dict[str, float]:
    if isinstance(payload, dict):
        if all(isinstance(key, str) and ":" in key for key in payload):
            return {key: float(value) for key, value in payload.items()}

        hours = payload.get("hours", [])
        if isinstance(hours, list):
            parsed: dict[str, float] = {}
            for item in hours:
                if not isinstance(item, dict):
                    continue
                hour_key = str(item.get("time") or item.get("hour") or "")
                mw_value = item.get("mw", item.get("actual_mw", item.get("value")))
                if hour_key and mw_value is not None:
                    if ":" not in hour_key and hour_key.isdigit():
                        hour_key = f"{int(hour_key):02d}:00"
                    parsed[hour_key] = float(mw_value)
            if parsed:
                return parsed

    raise ValueError("SCADA yanıtı saatlik üretim formatına dönüştürülemedi")


class LiveRestScadaProvider:
    """Fiziksel SCADA REST (veya Influx proxy) sağlayıcısı."""

    def __init__(self, *, api_url: str, session: Session) -> None:
        self._api_url = api_url.rstrip("/")
        self._session = session
        self._logger = get_logger("data_hub.scada.live")
        self._last_meta: dict[str, Any] = {"mode": "unknown", "reason": "not_fetched"}

    def ping(self) -> dict[str, Any]:
        return enrich_scada_layer_meta(
            {
                "status": "ok",
                "client": "scada",
                "mode": "live",
                "source": "scada-live",
                "confidence": "live",
                "live": "true",
                "label": "Live SCADA",
                "provider": "live_rest",
            }
        )

    def get_last_meta(self) -> dict[str, Any]:
        return dict(self._last_meta)

    def fetch(self, asset_id: str, target_date: str) -> dict[str, float]:
        self._logger.info(
            "SCADA live provider: asset_id=%s target_date=%s",
            asset_id,
            target_date,
        )
        if self._api_url.startswith("influx://"):
            result = self._fetch_from_influx(asset_id, target_date)
        else:
            result = self._fetch_from_rest(asset_id, target_date)
        self._last_meta = enrich_scada_layer_meta(
            {
                "mode": "live",
                "reason": "ok",
                "source": "scada-live",
                "confidence": "live",
                "live": "true",
                "label": "Live SCADA",
                "provider": "live_rest",
            }
        )
        return result

    def _fetch_from_rest(self, asset_id: str, target_date: str) -> dict[str, float]:
        response = self._session.get(
            f"{self._api_url}/generation",
            params={"asset_id": asset_id, "date": target_date},
            headers={"Accept": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return _parse_generation_payload(response.json())

    def _fetch_from_influx(self, asset_id: str, target_date: str) -> dict[str, float]:
        influx_target = self._api_url.replace("influx://", "", 1)
        if "/" in influx_target:
            host, database = influx_target.split("/", 1)
        else:
            host, database = influx_target, ""
        response = self._session.get(
            f"http://{host.rstrip('/')}/query",
            params={"asset_id": asset_id, "date": target_date, "db": database},
            headers={"Accept": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return _parse_generation_payload(response.json())


class EpiasSimulatedScadaProvider:
    """EPİAŞ ulusal rüzgar MW → santral ölçekli *operational* güç proxy.

    Yalnızca aktif güç (MW) üretir. Pitch/yaw/sıcaklık/alarm uydurmaz.
    Eksik EPİAŞ saatleri pad edilir ama observed_hours dışında bırakılır.
    """

    def __init__(
        self,
        *,
        epias_client: EpiasClient,
        asset_registry: Optional[AssetRegistryService] = None,
    ) -> None:
        self._epias = epias_client
        self._assets = asset_registry or AssetRegistryService()
        self._logger = get_logger("data_hub.scada.simulator")
        self._last_meta: dict[str, Any] = {"mode": "unknown", "reason": "not_fetched"}

    def ping(self) -> dict[str, Any]:
        return enrich_scada_layer_meta(
            {
                "status": "ok",
                "client": "scada",
                "mode": "simulated",
                "source": "simulated_from_epias",
                "confidence": "simulated",
                "live": "false",
                "label": SCADA_SIMULATED_LABEL,
                "provider": "epias_simulator",
            }
        )

    def get_last_meta(self) -> dict[str, Any]:
        return dict(self._last_meta)

    def fetch(self, asset_id: str, target_date: str) -> dict[str, float]:
        parsed_date = _parse_target_date(target_date)
        capacity_mw = self._resolve_capacity_mw(asset_id)
        national_wind = self._epias.fetch_hourly_wind_generation(parsed_date)
        if not national_wind:
            raise ValueError("EPİAŞ rüzgar üretimi boş")

        share = min(1.0, capacity_mw / _TURKEY_WIND_CAPACITY_REF_MW)
        scaled: dict[str, float] = {}
        observed: list[str] = []
        for hour_key, national_mw in national_wind.items():
            key = hour_key
            if ":" not in key and str(key).isdigit():
                key = f"{int(key):02d}:00"
            scaled[key] = round(min(capacity_mw, max(0.0, float(national_mw) * share)), 4)
            observed.append(key)

        padded: list[str] = []
        for hour in range(24):
            key = f"{hour:02d}:00"
            if key not in scaled:
                scaled[key] = 0.0
                padded.append(key)

        self._last_meta = enrich_scada_layer_meta(
            {
                "mode": "simulated",
                "reason": "epias_derived",
                "source": "simulated_from_epias",
                "confidence": "simulated",
                "live": "false",
                "label": SCADA_SIMULATED_LABEL,
                "provider": "epias_simulator",
                "observed_hours": sorted(set(observed)),
                "padded_hours": padded,
                "observed_hour_count": len(set(observed)),
                "padded_hour_count": len(padded),
            }
        )
        self._logger.info(
            "SCADA simulator (EPİAŞ): asset_id=%s capacity_mw=%s share=%.5f observed=%s padded=%s",
            asset_id,
            capacity_mw,
            share,
            len(set(observed)),
            len(padded),
        )
        return scaled

    def _resolve_capacity_mw(self, asset_id: str) -> float:
        try:
            return float(self._assets.get_asset_by_id(asset_id).capacity_mw)
        except KeyError:
            return 50.0


class DeterministicMockScadaProvider:
    """Son çare deterministik sahte üretim (EPİAŞ da kullanılamazsa)."""

    def __init__(self, reason: str = "forced_mock") -> None:
        self._reason = reason
        self._last_meta: dict[str, Any] = {"mode": "unknown", "reason": "not_fetched"}

    def ping(self) -> dict[str, Any]:
        return enrich_scada_layer_meta(
            {
                "status": "ok",
                "client": "scada",
                "mode": "mock",
                "source": f"scada-mock:{self._reason}",
                "confidence": "mock",
                "live": "false",
                "label": "Mock (fallback)",
                "provider": "deterministic_mock",
            }
        )

    def get_last_meta(self) -> dict[str, Any]:
        return dict(self._last_meta)

    def fetch(self, asset_id: str, target_date: str) -> dict[str, float]:
        seed = int(hashlib.md5(f"{asset_id}:{target_date}".encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        base_mw = 20.0 + (seed % 1500) / 100.0

        generation: dict[str, float] = {}
        for hour in range(24):
            noise_factor = rng.uniform(_NOISE_MIN, _NOISE_MAX)
            generation[f"{hour:02d}:00"] = round(max(0.0, base_mw * noise_factor), 1)

        all_hours = sorted(generation.keys())
        self._last_meta = enrich_scada_layer_meta(
            {
                "mode": "mock",
                "reason": self._reason,
                "source": f"scada-mock:{self._reason}",
                "confidence": "mock",
                "live": "false",
                "label": "Mock (fallback)",
                "provider": "deterministic_mock",
                "observed_hours": all_hours,
                "padded_hours": [],
                "observed_hour_count": len(all_hours),
                "padded_hour_count": 0,
            }
        )
        return generation


# REST parse helper — ScadaClient unit testleri için re-export
parse_generation_payload = _parse_generation_payload
