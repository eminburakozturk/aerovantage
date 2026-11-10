"""NASA POWER meteoroloji API istemcisi — Open-Meteo yedek kaynağı."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import requests
from requests import Session

from core.logger import get_logger
from modules.data_hub.schemas import WeatherData

_NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
_NASA_PARAMETERS = "T2M,WS10M,WD10M,PS"
_TURKEY_TZ = ZoneInfo("Europe/Istanbul")


class NasaPowerClient:
    """NASA POWER API üzerinden saatlik meteoroloji verisi çeker."""

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session or requests.Session()
        self._logger = get_logger("data_hub.nasa_power")

    def fetch_hourly(
        self,
        lat: float,
        lon: float,
        target_date: date,
    ) -> list[WeatherData]:
        """Belirtilen koordinat ve tarih için saatlik veri döndürür."""
        params = {
            "parameters": _NASA_PARAMETERS,
            "community": "RE",
            "latitude": lat,
            "longitude": lon,
            "start": target_date.strftime("%Y%m%d"),
            "end": target_date.strftime("%Y%m%d"),
            "format": "JSON",
        }
        self._logger.info(
            "NASA POWER verisi isteniyor: lat=%s lon=%s target_date=%s",
            lat,
            lon,
            target_date,
        )
        response = self._session.get(_NASA_POWER_URL, params=params, timeout=30)
        response.raise_for_status()
        return self.parse_response(response.json(), target_date)

    def parse_response(self, payload: dict[str, Any], target_date: date) -> list[WeatherData]:
        """NASA POWER JSON yanıtını WeatherData listesine dönüştürür."""
        parameters = (
            payload.get("properties", {}).get("parameter")
            or payload.get("parameters")
            or {}
        )
        if not parameters:
            raise ValueError("NASA POWER payload'ında parameter bloğu bulunamadı")

        temp_series = parameters.get("T2M", {})
        wind_speed_series = parameters.get("WS10M", {})
        wind_dir_series = parameters.get("WD10M", {})
        pressure_series = parameters.get("PS", {})

        if not isinstance(temp_series, dict) or not temp_series:
            raise ValueError("NASA POWER T2M serisi boş")

        hours: list[WeatherData] = []
        for key in sorted(temp_series.keys()):
            if len(key) < 10:
                continue
            year = int(key[0:4])
            month = int(key[4:6])
            day = int(key[6:8])
            hour = int(key[8:10])
            if date(year, month, day) != target_date:
                continue

            timestamp = datetime(year, month, day, hour, tzinfo=_TURKEY_TZ).astimezone(timezone.utc)
            temp_value = temp_series.get(key)
            if temp_value is None or float(temp_value) < -900:
                continue

            wind_speed = float(wind_speed_series.get(key, 0.0))
            wind_direction = float(wind_dir_series.get(key, 0.0))
            pressure = float(pressure_series.get(key, 1013.0))

            hours.append(
                WeatherData(
                    timestamp=timestamp,
                    temperature=float(temp_value),
                    wind_speed=max(0.0, wind_speed),
                    wind_direction=wind_direction % 360.0,
                    air_pressure=pressure,
                )
            )

        if not hours:
            raise ValueError("NASA POWER yanıtı hedef tarih için saatlik kayıt içermiyor")

        return hours
