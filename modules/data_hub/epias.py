"""EPİAŞ şeffaflık platformu istemci iskeleti."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

import requests
from requests import Response, Session

from core.config import Settings, get_settings
from core.logger import get_logger
from core.utils import cache_data, retry_on_failure
from modules.data_hub.epias_auth import EpiasAuthError, EpiasCasAuth
from modules.data_hub.schemas import DayAheadPTFResponse, HourlyPTF, HourlySMF, SystemMarginalPriceResponse

_LEGACY_DAY_AHEAD_PTF_URL = (
    "https://seffaflik.epias.com.tr/transparency/service/market/day-ahead-mcp"
)
_TURKEY_OFFSET = "+03:00"


class EpiasClient:
    """EPİAŞ'tan gün öncesi piyasa (PTF) verisi çeken istemci."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        session: Optional[Session] = None,
        auth: Optional[EpiasCasAuth] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._logger = get_logger("data_hub.epias")
        self._session = session or requests.Session()
        self._auth = auth or EpiasCasAuth(settings=self._settings, session=self._session)
        self._last_fetch_meta: dict[str, Any] = {
            "mode": "unknown",
            "reason": "not_fetched",
            "source": "unknown",
        }

    def ping(self) -> dict[str, str]:
        """EPİAŞ istemci erişilebilirlik kontrolü."""
        mode = "mock" if self._settings.epias_use_mock else "live"
        return {
            "status": "ok",
            "client": "epias",
            "mode": mode,
            "live": "false" if self._settings.epias_use_mock else "true",
            "label": "EPİAŞ mock" if self._settings.epias_use_mock else "EPİAŞ live",
        }

    @cache_data(ttl_seconds=60)
    @retry_on_failure(max_retries=2, delay_seconds=0.3)
    def fetch_day_ahead_ptf(self, delivery_date: date) -> DayAheadPTFResponse:
        """Belirtilen teslimat günü için saatlik PTF verisini döndürür."""
        if self._settings.epias_use_mock:
            self._logger.info("Mock PTF verisi döndürülüyor: delivery_date=%s", delivery_date)
            return self._mock_day_ahead_ptf(delivery_date, reason="forced_mock")

        self._logger.info("EPİAŞ'tan PTF verisi isteniyor: delivery_date=%s", delivery_date)
        return self._fetch_day_ahead_ptf_live(delivery_date)

    def get_last_fetch_meta(self) -> dict[str, Any]:
        """Son EPİAŞ fetch çağrısının source/degraded bilgisini döndürür."""
        return dict(self._last_fetch_meta)

    def _set_fetch_meta(self, *, mode: str, reason: str, source: str) -> None:
        self._last_fetch_meta = {
            "mode": mode,
            "reason": reason,
            "source": source,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def _fetch_day_ahead_ptf_live(self, delivery_date: date) -> DayAheadPTFResponse:
        """Canlı EPİAŞ endpoint'i; TGT auth ile resmi MCP servisini çağırır."""
        try:
            return self._request_day_ahead_ptf(delivery_date, allow_tgt_retry=True)
        except EpiasAuthError as exc:
            self._logger.warning(
                "EPİAŞ kimlik doğrulama başarısız, mock veriye dönülüyor: reason=%s",
                exc.reason,
            )
            return self._mock_day_ahead_ptf(delivery_date, reason=exc.reason)
        except ValueError as exc:
            self._logger.warning(
                "EPİAŞ payload eşlemesi başarısız, mock veriye dönülüyor: delivery_date=%s error=%s",
                delivery_date,
                exc,
            )
            return self._mock_day_ahead_ptf(delivery_date, reason="mapping_failed")

    def _request_day_ahead_ptf(
        self,
        delivery_date: date,
        *,
        allow_tgt_retry: bool,
    ) -> DayAheadPTFResponse:
        try:
            auth_headers = self._auth.get_auth_headers()
        except EpiasAuthError:
            raise

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **auth_headers,
        }
        use_v1_api = "TGT" in auth_headers
        payload = (
            self._build_mcp_request_payload(delivery_date)
            if use_v1_api
            else {"date": delivery_date.isoformat()}
        )
        endpoint = self._resolve_mcp_endpoint(auth_headers)

        response = self._post_ptf_request(
            endpoint=endpoint,
            headers=headers,
            payload=payload,
            delivery_date=delivery_date,
        )

        if response.status_code in (401, 403) and "TGT" in auth_headers and allow_tgt_retry:
            self._logger.warning("EPİAŞ TGT reddedildi, yenilenip tekrar deneniyor")
            self._auth.invalidate()
            return self._request_day_ahead_ptf(delivery_date, allow_tgt_retry=False)

        if response.status_code in (401, 403):
            raise EpiasAuthError("auth_failed")

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in (401, 403):
                raise EpiasAuthError("auth_failed") from exc
            self._logger.error(
                "EPİAŞ isteği başarısız: delivery_date=%s error=%s",
                delivery_date,
                exc,
            )
            raise

        live_result = self._parse_live_day_ahead_ptf(
            response_payload=response.json(),
            delivery_date=delivery_date,
        )
        self._set_fetch_meta(mode="live", reason="ok", source=live_result.source)
        self._logger.info(
            "Canlı EPİAŞ yanıtı eşlendi: delivery_date=%s source=%s",
            delivery_date,
            live_result.source,
        )
        return live_result

    def _post_ptf_request(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        delivery_date: date,
    ) -> Response:
        try:
            return self._session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30,
            )
        except requests.RequestException as exc:
            self._logger.warning(
                "EPİAŞ isteği başarısız, mock veriye dönülüyor: delivery_date=%s error=%s",
                delivery_date,
                exc,
            )
            raise EpiasAuthError("request_failed", str(exc)) from exc

    def _resolve_mcp_endpoint(self, auth_headers: dict[str, str]) -> str:
        if "TGT" in auth_headers:
            return f"{self._settings.epias_base_url.rstrip('/')}/markets/dam/data/mcp"
        return _LEGACY_DAY_AHEAD_PTF_URL

    @staticmethod
    def _build_mcp_request_payload(delivery_date: date) -> dict[str, Any]:
        day_start = f"{delivery_date.isoformat()}T00:00:00{_TURKEY_OFFSET}"
        return {
            "startDate": day_start,
            "endDate": day_start,
        }

    @staticmethod
    def _parse_hour_value(hour_value: Any) -> Optional[int]:
        if hour_value is None:
            return None
        if isinstance(hour_value, int):
            return hour_value
        text = str(hour_value).strip()
        if ":" in text:
            return int(text.split(":", 1)[0])
        if text.isdigit():
            return int(text)
        return None

    def _parse_live_day_ahead_ptf(
        self,
        response_payload: dict[str, Any],
        delivery_date: date,
    ) -> DayAheadPTFResponse:
        """EPİAŞ canlı payload'unu DayAheadPTFResponse modeline eşler."""
        items = response_payload.get("items")
        if isinstance(items, list) and items:
            return self._parse_v1_mcp_items(items, delivery_date)

        body = response_payload.get("body", response_payload)
        rows = body.get("dayAheadMCPList") or body.get("dayAheadMarketList") or body.get("items") or []
        if not isinstance(rows, list) or not rows:
            raise ValueError("EPİAŞ payload'ında saatlik PTF satırı bulunamadı")

        hours: list[HourlyPTF] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            hour_value = self._parse_hour_value(
                row.get("hour")
                if row.get("hour") is not None
                else row.get("hourNo")
                if row.get("hourNo") is not None
                else row.get("period")
            )
            price_value = (
                row.get("price")
                if row.get("price") is not None
                else row.get("mcpTr")
                if row.get("mcpTr") is not None
                else row.get("mcp")
                if row.get("mcp") is not None
                else row.get("ptf")
                if row.get("ptf") is not None
                else row.get("marketClearingPrice")
            )
            if hour_value is None or price_value is None:
                continue
            hours.append(HourlyPTF(hour=hour_value, ptf=Decimal(str(price_value))))

        if not hours:
            raise ValueError("EPİAŞ payload'ı map edildi ancak geçerli saatlik kayıt bulunamadı")

        return DayAheadPTFResponse(
            delivery_date=delivery_date,
            hours=hours,
            source="epias-live",
        )

    def _parse_v1_mcp_items(
        self,
        items: list[Any],
        delivery_date: date,
    ) -> DayAheadPTFResponse:
        hours: list[HourlyPTF] = []
        for row in items:
            if not isinstance(row, dict):
                continue
            hour_value = self._parse_hour_value(row.get("hour"))
            price_value = row.get("price") or row.get("mcpTr")
            if hour_value is None or price_value is None:
                continue
            hours.append(HourlyPTF(hour=hour_value, ptf=Decimal(str(price_value))))

        if not hours:
            raise ValueError("EPİAŞ v1 MCP yanıtında geçerli saatlik kayıt bulunamadı")

        return DayAheadPTFResponse(
            delivery_date=delivery_date,
            hours=hours,
            source="epias-live",
        )

    def _mock_day_ahead_ptf(self, delivery_date: date, reason: str = "mock") -> DayAheadPTFResponse:
        """Geliştirme için deterministik sahte saatlik PTF verisi."""
        base_price = Decimal("2850.00")
        hours = [
            HourlyPTF(
                hour=hour,
                ptf=(base_price + Decimal(hour * 12)).quantize(Decimal("0.01")),
            )
            for hour in range(24)
        ]
        source = f"epias-mock:{reason}"
        self._set_fetch_meta(mode="mock", reason=reason, source=source)
        return DayAheadPTFResponse(
            delivery_date=delivery_date,
            hours=hours,
            source=source,
        )

    def fetch_hourly_wind_generation(self, delivery_date: date) -> dict[str, float]:
        """Türkiye rüzgar gerçek zamanlı üretimini saatlik MW olarak döndürür (SCADA simulator kaynağı)."""
        if self._settings.epias_use_mock:
            return self._mock_wind_generation(delivery_date, reason="forced_mock")

        try:
            return self._request_hourly_wind_generation(delivery_date, allow_tgt_retry=True)
        except EpiasAuthError as exc:
            self._logger.warning(
                "EPİAŞ rüzgar üretimi auth başarısız: reason=%s",
                exc.reason,
            )
            raise
        except (ValueError, requests.RequestException) as exc:
            self._logger.warning(
                "EPİAŞ rüzgar üretimi alınamadı: delivery_date=%s error=%s",
                delivery_date,
                exc,
            )
            raise

    def _request_hourly_wind_generation(
        self,
        delivery_date: date,
        *,
        allow_tgt_retry: bool,
    ) -> dict[str, float]:
        auth_headers = self._auth.get_auth_headers()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **auth_headers,
        }
        endpoint = f"{self._settings.epias_base_url.rstrip('/')}/generation/data/realtime-generation"
        payload = self._build_mcp_request_payload(delivery_date)

        try:
            response = self._session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise EpiasAuthError("request_failed", str(exc)) from exc

        if response.status_code in (401, 403) and "TGT" in auth_headers and allow_tgt_retry:
            self._auth.invalidate()
            return self._request_hourly_wind_generation(delivery_date, allow_tgt_retry=False)

        if response.status_code in (401, 403):
            raise EpiasAuthError("auth_failed")

        response.raise_for_status()
        parsed = self._parse_realtime_wind_generation(response.json())
        if not parsed:
            raise ValueError("EPİAŞ realtime-generation yanıtında rüzgar saati bulunamadı")
        self._set_fetch_meta(mode="live", reason="ok", source="epias-realtime-generation")
        self._logger.info(
            "EPİAŞ rüzgar üretimi eşlendi: delivery_date=%s hours=%s",
            delivery_date,
            len(parsed),
        )
        return parsed

    def _parse_realtime_wind_generation(self, payload: dict[str, Any]) -> dict[str, float]:
        """Kaynak bazlı realtime üretim yanıtından rüzgar MW saatlerini çıkarır."""
        items = payload.get("items")
        if not isinstance(items, list):
            body = payload.get("body", payload)
            items = body.get("items") or body.get("hourlyGenerations") or body.get("generationList") or []
        if not isinstance(items, list):
            return {}

        wind_keys = (
            "wind",
            "windOnshore",
            "windOffshore",
            "ruzgar",
            "windPower",
            "totalWind",
        )
        result: dict[str, float] = {}
        for row in items:
            if not isinstance(row, dict):
                continue
            hour_value = self._parse_hour_value(
                row.get("hour") or row.get("time") or row.get("date")
            )
            if hour_value is None and isinstance(row.get("date"), str) and "T" in row["date"]:
                try:
                    hour_value = datetime.fromisoformat(row["date"].replace("Z", "+00:00")).hour
                except ValueError:
                    hour_value = None
            if hour_value is None:
                continue

            wind_mw = None
            for key in wind_keys:
                if row.get(key) is not None:
                    wind_mw = float(row[key])
                    break
            if wind_mw is None and isinstance(row.get("total"), (int, float)):
                # Bazı yanıtlarda yalnızca toplam gelir; rüzgar yoksa atla
                continue
            if wind_mw is None:
                continue
            result[f"{int(hour_value):02d}:00"] = round(max(0.0, wind_mw), 4)

        return result

    def _mock_wind_generation(self, delivery_date: date, reason: str) -> dict[str, float]:
        base = 4500.0 + (delivery_date.toordinal() % 17) * 35.0
        return {f"{hour:02d}:00": round(base + hour * 12.0, 1) for hour in range(24)}

    @cache_data(ttl_seconds=60)
    @retry_on_failure(max_retries=2, delay_seconds=0.3)
    def fetch_system_marginal_price(self, delivery_date: date) -> SystemMarginalPriceResponse:
        """Belirtilen teslimat günü için saatlik SMF verisini döndürür."""
        ptf_response = self.fetch_day_ahead_ptf(delivery_date)
        hours = [
            HourlySMF(
                hour=hourly_ptf.hour,
                smf=(hourly_ptf.ptf * Decimal("0.97") + Decimal(hourly_ptf.hour * 3)).quantize(
                    Decimal("0.01")
                ),
            )
            for hourly_ptf in ptf_response.hours
        ]
        return SystemMarginalPriceResponse(
            delivery_date=delivery_date,
            hours=hours,
            source=ptf_response.source,
        )
