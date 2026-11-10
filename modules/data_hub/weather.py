"""Meteoroloji servisi istemci iskeleti."""

from __future__ import annotations

import math
from datetime import date, datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import requests
from requests import Session

from core.config import Settings, get_settings
from core.logger import get_logger
from core.utils import cache_data, retry_on_failure
from modules.data_hub.freshness import check_hourly_freshness
from modules.data_hub.nasa_power import NasaPowerClient
from modules.data_hub.schemas import WeatherData, WeatherForecastResponse

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_OPEN_METEO_HOURLY = (
    "temperature_2m,wind_speed_10m,wind_direction_10m,surface_pressure"
)
_BALIKESIR_RES_LAT = 39.64
_BALIKESIR_RES_LON = 27.88
_TURKEY_TZ = ZoneInfo("Europe/Istanbul")


class WeatherClient:
    """Saatlik meteorolojik tahmin verisi sağlayan istemci."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        session: Optional[Session] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._logger = get_logger("data_hub.weather")
        self._session = session or requests.Session()
        self._nasa_client = NasaPowerClient(session=self._session)
        self._last_fetch_meta: dict[str, Any] = {
            "mode": "unknown",
            "reason": "not_fetched",
            "source": "unknown",
        }

    def ping(self) -> dict[str, str]:
        """Hava durumu istemci erişilebilirlik kontrolü."""
        mode = "mock" if self._settings.weather_use_mock else "live"
        return {
            "status": "ok",
            "client": "weather",
            "mode": mode,
            "live": "false" if self._settings.weather_use_mock else "true",
            "label": "Weather mock" if self._settings.weather_use_mock else "Open-Meteo live",
        }

    @cache_data(ttl_seconds=60)
    @retry_on_failure(max_retries=2, delay_seconds=0.3)
    def fetch_hourly_forecast(
        self,
        lat: float,
        lon: float,
        target_date: date,
    ) -> WeatherForecastResponse:
        """Belirtilen koordinat ve tarih için 24 saatlik tahmin döndürür."""
        if self._settings.weather_use_mock:
            self._logger.info(
                "Mock meteoroloji verisi döndürülüyor: lat=%s lon=%s target_date=%s",
                lat,
                lon,
                target_date,
            )
            return self._mock_hourly_forecast(lat, lon, target_date, reason="forced_mock")

        self._logger.info(
            "Open-Meteo'dan tahmin isteniyor: lat=%s lon=%s target_date=%s",
            lat,
            lon,
            target_date,
        )
        try:
            return self._fetch_hourly_forecast_live(lat, lon, target_date)
        except (requests.RequestException, ValueError) as exc:
            self._logger.warning(
                "Open-Meteo verisi alinamadi, NASA POWER deneniyor: lat=%s lon=%s target_date=%s error=%s",
                lat,
                lon,
                target_date,
                exc,
            )
            return self._fetch_from_nasa_power(lat, lon, target_date, fallback_reason="live_fetch_failed")

    def get_last_fetch_meta(self) -> dict[str, Any]:
        """Son weather fetch çağrısının source/degraded bilgisini döndürür."""
        return dict(self._last_fetch_meta)

    def _set_fetch_meta(
        self,
        *,
        mode: str,
        reason: str,
        source: str,
        freshness_ok: bool | None = None,
    ) -> None:
        self._last_fetch_meta = {
            "mode": mode,
            "reason": reason,
            "source": source,
            "provider": source.split("-", 1)[0] if "-" in source else source,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        if freshness_ok is not None:
            self._last_fetch_meta["freshness_ok"] = freshness_ok

    def _fetch_hourly_forecast_live(
        self,
        lat: float,
        lon: float,
        target_date: date,
    ) -> WeatherForecastResponse:
        """Open-Meteo API üzerinden canlı saatlik meteoroloji verisi çeker."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": _OPEN_METEO_HOURLY,
            "wind_speed_unit": "ms",
            "timezone": "Europe/Istanbul",
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        }

        try:
            response = self._session.get(
                _OPEN_METEO_URL,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        except requests.Timeout as exc:
            self._logger.error(
                "Open-Meteo zaman asimi: lat=%s lon=%s target_date=%s error=%s",
                lat,
                lon,
                target_date,
                exc,
            )
            raise
        except requests.ConnectionError as exc:
            self._logger.error(
                "Open-Meteo baglanti hatasi: lat=%s lon=%s target_date=%s error=%s",
                lat,
                lon,
                target_date,
                exc,
            )
            raise
        except requests.RequestException as exc:
            self._logger.error(
                "Open-Meteo istegi basarisiz: lat=%s lon=%s target_date=%s error=%s",
                lat,
                lon,
                target_date,
                exc,
            )
            raise

        hours = self._parse_open_meteo_response(payload, target_date)
        if not hours:
            self._logger.error(
                "Open-Meteo bos yanit: lat=%s lon=%s target_date=%s",
                lat,
                lon,
                target_date,
            )
            raise ValueError(
                f"Open-Meteo returned no hourly data for {target_date.isoformat()}"
            )

        freshness = check_hourly_freshness(hours, target_date)
        if not freshness["freshness_ok"]:
            self._logger.warning(
                "Open-Meteo verisi taze degil, NASA POWER deneniyor: lat=%s lon=%s reason=%s",
                lat,
                lon,
                freshness["reason"],
            )
            return self._fetch_from_nasa_power(lat, lon, target_date, fallback_reason=freshness["reason"])

        self._set_fetch_meta(mode="live", reason="ok", source="open-meteo", freshness_ok=True)
        return WeatherForecastResponse(
            latitude=lat,
            longitude=lon,
            target_date=target_date,
            hours=hours,
            source="open-meteo",
        )

    def _fetch_from_nasa_power(
        self,
        lat: float,
        lon: float,
        target_date: date,
        *,
        fallback_reason: str = "open_meteo_failed",
    ) -> WeatherForecastResponse:
        """Open-Meteo başarısız veya bayat olduğunda NASA POWER yedek kaynağını dener."""
        try:
            hours = self._nasa_client.fetch_hourly(lat, lon, target_date)
            freshness = check_hourly_freshness(hours, target_date)
            if not freshness["freshness_ok"]:
                raise ValueError(f"NASA POWER freshness failed: {freshness['reason']}")
            self._set_fetch_meta(mode="live", reason="ok", source="nasa-power", freshness_ok=True)
            return WeatherForecastResponse(
                latitude=lat,
                longitude=lon,
                target_date=target_date,
                hours=hours,
                source="nasa-power",
            )
        except (requests.RequestException, ValueError) as exc:
            self._logger.warning(
                "NASA POWER yedek kaynagi basarisiz, mock'a donuluyor: reason=%s error=%s",
                fallback_reason,
                exc,
            )
            return self._mock_hourly_forecast(
                lat,
                lon,
                target_date,
                reason=f"nasa_fallback_failed:{fallback_reason}",
            )

    def _parse_open_meteo_response(
        self,
        payload: dict[str, Any],
        target_date: date,
    ) -> list[WeatherData]:
        """Open-Meteo JSON yanıtını WeatherData listesine dönüştürür."""
        hourly = payload.get("hourly", {})
        times: list[str] = hourly.get("time", [])
        temperatures: list[float] = hourly.get("temperature_2m", [])
        wind_speeds: list[float] = hourly.get("wind_speed_10m", [])
        wind_directions: list[float] = hourly.get("wind_direction_10m", [])
        pressures: list[float] = hourly.get("surface_pressure", [])

        hours: list[WeatherData] = []
        for index, time_str in enumerate(times):
            parsed = datetime.fromisoformat(time_str)
            if parsed.date() != target_date:
                continue

            timestamp = parsed.replace(tzinfo=_TURKEY_TZ)
            # UTC'ye çevirirken takvim günü kaymasın diye doğrulama Istanbul gününe göre yapılır;
            # saklama formatı UTC (pipeline/freshness ile uyumlu).
            timestamp_utc = timestamp.astimezone(timezone.utc)
            hours.append(
                WeatherData(
                    timestamp=timestamp_utc,
                    temperature=float(temperatures[index]),
                    wind_speed=max(0.0, float(wind_speeds[index])),
                    wind_direction=float(wind_directions[index]),
                    air_pressure=float(pressures[index]),
                )
            )

        return hours

    def _mock_hourly_forecast(
        self,
        lat: float,
        lon: float,
        target_date: date,
        reason: str = "mock",
    ) -> WeatherForecastResponse:
        """Balıkesir RES profiline uygun deterministik saatlik sahte veri."""
        reference_lat = _BALIKESIR_RES_LAT
        reference_lon = _BALIKESIR_RES_LON
        if round(lat, 2) != reference_lat or round(lon, 2) != reference_lon:
            self._logger.debug(
                "Mock profil Balıkesir RES referans koordinatlarıyla üretiliyor "
                "(istek: lat=%s lon=%s, referans: lat=%s lon=%s)",
                lat,
                lon,
                reference_lat,
                reference_lon,
            )

        hours = [
            self._build_mock_hour(target_date, hour)
            for hour in range(24)
        ]
        source = f"weather-mock:{reason}"
        self._set_fetch_meta(mode="mock", reason=reason, source=source, freshness_ok=False)
        return WeatherForecastResponse(
            latitude=lat,
            longitude=lon,
            target_date=target_date,
            hours=hours,
            source=source,
        )

    def _build_mock_hour(self, target_date: date, hour: int) -> WeatherData:
        """Sinüs eğrisiyle gece 5–7 m/s, gündüz 8–12 m/s rüzgar profili üretir."""
        phase = (hour - 14) * 2 * math.pi / 24
        wind_speed = round(8.5 + 3.5 * math.cos(phase), 2)

        temperature = round(12.0 + 8.0 * math.sin((hour - 8) * math.pi / 12), 2)
        wind_direction = round((210.0 + 30.0 * math.sin(hour * math.pi / 12)) % 360, 2)
        air_pressure = round(1013.0 + 2.0 * math.cos((hour - 6) * math.pi / 12), 2)

        # Delivery-day hours are Europe/Istanbul; store UTC (same as live Open-Meteo path).
        # Using naive UTC 00–23 wrongly shifts hours 21–23 into the next Istanbul day.
        timestamp = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            hour,
            tzinfo=_TURKEY_TZ,
        ).astimezone(timezone.utc)
        return WeatherData(
            timestamp=timestamp,
            temperature=temperature,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            air_pressure=air_pressure,
        )
