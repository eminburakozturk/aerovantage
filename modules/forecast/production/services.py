"""Üretim tahmini servis katmanı."""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.logger import get_logger
from modules.forecast.production.models.wind_model import WindPowerModel
from modules.forecast.production.models.xgb_hybrid_model import HybridWindPowerModel
from modules.forecast.production.schemas import ProductionData, ProductionForecastResponse
from modules.data_hub.weather import WeatherClient


class ProductionForecastService:
    """Meteoroloji verisini hibrit guc modeliyle saatlik uretime donusturur."""

    def __init__(
        self,
        weather_client: Optional[WeatherClient] = None,
        wind_model: Optional[WindPowerModel] = None,
        capacity_mw: float = 50.0,
        asset_id: Optional[str] = None,
    ) -> None:
        self._weather_client = weather_client or WeatherClient()
        if wind_model is not None:
            self._wind_model = wind_model
        elif asset_id:
            self._wind_model = HybridWindPowerModel(
                capacity_mw=capacity_mw,
                asset_id=asset_id,
            )
        else:
            self._wind_model = WindPowerModel(capacity_mw=capacity_mw)
        self._logger = get_logger("forecast.production")
        self._last_peak_wind_speed_mps: float | None = None

    def forecast_daily_production(
        self,
        lat: float,
        lon: float,
        target_date: date,
    ) -> ProductionForecastResponse:
        """24 saatlik hava verisini alır, saatlik MW tahmini ve günlük toplamı döndürür."""
        self._logger.info(
            "Günlük üretim tahmini başlatıldı: lat=%s lon=%s target_date=%s",
            lat,
            lon,
            target_date,
        )

        weather_forecast = self._weather_client.fetch_hourly_forecast(lat, lon, target_date)

        hours: list[ProductionData] = []
        total_daily_mw = 0.0
        peak_weather = None
        peak_mw = -1.0

        for weather_hour in weather_forecast.hours:
            generated_mw = self._wind_model.predict(weather_hour)
            if generated_mw > peak_mw:
                peak_mw = generated_mw
                peak_weather = weather_hour
            hours.append(
                ProductionData(
                    timestamp=weather_hour.timestamp,
                    generated_mw=generated_mw,
                )
            )
            total_daily_mw += generated_mw

        attribution = None
        if peak_weather is not None and hasattr(self._wind_model, "explain"):
            try:
                attribution = self._wind_model.explain(peak_weather)
            except Exception as exc:
                self._logger.warning("Attribution atlandı: %s", exc)
                attribution = None

        self._last_peak_wind_speed_mps = (
            float(peak_weather.wind_speed) if peak_weather is not None else None
        )

        total_daily_mw = round(total_daily_mw, 4)

        self._logger.info(
            "Günlük üretim tahmini tamamlandı: target_date=%s total_daily_mw=%s peak_wind=%s",
            target_date,
            total_daily_mw,
            self._last_peak_wind_speed_mps,
        )

        return ProductionForecastResponse(
            hours=hours,
            total_daily_mw=total_daily_mw,
            source=weather_forecast.source,
            attribution=attribution,
        )
