"""SCADA adapter — Operational Intelligence her zaman bu istemciyi kullanır.

Provider seçimi (mimari değişmez, yalnızca sağlayıcı):
  1. LiveRestScadaProvider     — SCADA_API_URL + SCADA_USE_MOCK=false
  2. EpiasSimulatedScadaProvider — fiziksel SCADA yok; EPİAŞ'tan türetilmiş simülasyon
  3. DeterministicMockScadaProvider — son çare

İleride gerçek bir SCADA API geldiğinde yalnızca (1) etkinleştirilir.
"""

from __future__ import annotations

from typing import Any, Optional

import requests
from requests import Session

from core.config import Settings, get_settings
from core.logger import get_logger
from core.utils import cache_data, retry_on_failure
from modules.asset_registry.service import AssetRegistryService
from modules.data_hub.epias import EpiasClient
from modules.data_hub.epias_auth import EpiasAuthError
from modules.data_hub.scada_providers import (
    DeterministicMockScadaProvider,
    EpiasSimulatedScadaProvider,
    LiveRestScadaProvider,
    parse_generation_payload,
)


class ScadaClient:
    """SCADA katmanı adapter'ı — veri kaynağı provider arkasındadır."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        session: Optional[Session] = None,
        epias_client: Optional[EpiasClient] = None,
        asset_registry: Optional[AssetRegistryService] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._logger = get_logger("data_hub.scada")
        self._session = session or requests.Session()
        self._epias = epias_client or EpiasClient(settings=self._settings, session=self._session)
        self._assets = asset_registry or AssetRegistryService()
        self._last_fetch_meta: dict[str, Any] = {"mode": "unknown", "reason": "not_fetched"}

        self._live: Optional[LiveRestScadaProvider] = None
        if self._settings.scada_api_url:
            self._live = LiveRestScadaProvider(
                api_url=self._settings.scada_api_url,
                session=self._session,
            )
        self._simulator = EpiasSimulatedScadaProvider(
            epias_client=self._epias,
            asset_registry=self._assets,
        )
        self._mock = DeterministicMockScadaProvider(reason="fallback")

    def ping(self) -> dict[str, Any]:
        """Aktif provider sağlık özeti."""
        if self._use_live():
            assert self._live is not None
            return self._live.ping()
        if not self._settings.epias_use_mock:
            return self._simulator.ping()
        return DeterministicMockScadaProvider(reason="epias_also_mock").ping()

    @cache_data(ttl_seconds=60)
    @retry_on_failure(max_retries=2, delay_seconds=0.3)
    def fetch_actual_generation(self, asset_id: str, target_date: str) -> dict[str, float]:
        """Belirtilen santral ve gün için saatlik gerçekleşen üretimi (MW) döndürür."""
        if self._use_live():
            return self._fetch_via_live_with_fallback(asset_id, target_date)

        if self._settings.epias_use_mock:
            return self._fetch_via_mock(asset_id, target_date, reason="epias_also_mock")

        try:
            return self._fetch_via_simulator(asset_id, target_date)
        except (EpiasAuthError, ValueError, requests.RequestException) as exc:
            reason = getattr(exc, "reason", None) or "epias_simulator_failed"
            self._logger.warning(
                "SCADA EPİAŞ simulator başarısız, deterministik mock: reason=%s asset_id=%s error=%s",
                reason,
                asset_id,
                exc,
            )
            return self._fetch_via_mock(asset_id, target_date, reason=str(reason))

    def get_last_fetch_meta(self) -> dict[str, Any]:
        """Son fetch metadata (source / confidence / live + operational/equipment katmanı)."""
        from modules.data_hub.ground_truth import enrich_scada_layer_meta

        return enrich_scada_layer_meta(self._last_fetch_meta)

    def _use_live(self) -> bool:
        return bool(self._live) and not self._settings.scada_use_mock

    def _fetch_via_live_with_fallback(self, asset_id: str, target_date: str) -> dict[str, float]:
        assert self._live is not None
        try:
            result = self._live.fetch(asset_id, target_date)
            self._last_fetch_meta = self._live.get_last_meta()
            return result
        except (requests.RequestException, ConnectionError, OSError) as exc:
            self._logger.warning(
                "SCADA live provider başarısız, simulator deneniyor: %s",
                exc,
            )
            try:
                if self._settings.epias_use_mock:
                    return self._fetch_via_mock(asset_id, target_date, reason="request_failed")
                return self._fetch_via_simulator(asset_id, target_date)
            except Exception:
                return self._fetch_via_mock(asset_id, target_date, reason="request_failed")
        except (NotImplementedError, ValueError) as exc:
            self._logger.warning("SCADA live payload/provider sorunu: %s", exc)
            try:
                if self._settings.epias_use_mock:
                    return self._fetch_via_mock(asset_id, target_date, reason="live_parse_failed")
                return self._fetch_via_simulator(asset_id, target_date)
            except Exception:
                return self._fetch_via_mock(asset_id, target_date, reason="live_parse_failed")

    def _fetch_via_simulator(self, asset_id: str, target_date: str) -> dict[str, float]:
        result = self._simulator.fetch(asset_id, target_date)
        self._last_fetch_meta = self._simulator.get_last_meta()
        return result

    def _fetch_via_mock(self, asset_id: str, target_date: str, reason: str) -> dict[str, float]:
        provider = DeterministicMockScadaProvider(reason=reason)
        result = provider.fetch(asset_id, target_date)
        self._last_fetch_meta = provider.get_last_meta()
        return result

    # Test / geriye uyumluluk: payload parse
    _parse_generation_payload = staticmethod(parse_generation_payload)
