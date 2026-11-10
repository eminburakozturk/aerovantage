"""Açıklanabilir rüzgar türbini güç eğrisi modeli."""

from __future__ import annotations

from modules.data_hub.schemas import WeatherData


class WindPowerModel:
    """Deterministik power-curve motoru; ileride ML modelleri bu arayüze bağlanabilir."""

    def __init__(
        self,
        capacity_mw: float = 50.0,
        cut_in_speed: float = 3.0,
        rated_speed: float = 12.0,
        cut_out_speed: float = 25.0,
    ) -> None:
        self.capacity_mw = capacity_mw
        self.cut_in_speed = cut_in_speed
        self.rated_speed = rated_speed
        self.cut_out_speed = cut_out_speed

    def predict(self, weather: WeatherData) -> float:
        """Rüzgar hızına göre saatlik üretim gücünü (MW) hesaplar."""
        wind_speed = weather.wind_speed

        if wind_speed < self.cut_in_speed or wind_speed >= self.cut_out_speed:
            return 0.0

        if wind_speed >= self.rated_speed:
            return self.capacity_mw

        normalized = (wind_speed - self.cut_in_speed) / (self.rated_speed - self.cut_in_speed)
        return round(self.capacity_mw * (normalized ** 3), 4)
