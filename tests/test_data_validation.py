"""Data Hub şema validasyon testleri."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from modules.data_hub.errors import DataValidationError
from modules.data_hub.schemas import HourlyPTF, WeatherData


def test_weather_data_rejects_none_wind_speed() -> None:
    with pytest.raises(DataValidationError):
        WeatherData(
            timestamp=datetime.now(timezone.utc),
            temperature=15.0,
            wind_speed=None,
            wind_direction=180.0,
            air_pressure=1013.0,
        )


def test_weather_data_rejects_out_of_range_temperature() -> None:
    with pytest.raises(DataValidationError):
        WeatherData(
            timestamp=datetime.now(timezone.utc),
            temperature=120.0,
            wind_speed=8.0,
            wind_direction=180.0,
            air_pressure=1013.0,
        )


def test_hourly_ptf_rejects_negative_price() -> None:
    with pytest.raises(DataValidationError):
        HourlyPTF(hour=10, ptf=-10)


def test_hourly_ptf_accepts_valid_record() -> None:
    record = HourlyPTF(hour=10, ptf=2850.0)
    assert record.hour == 10


if __name__ == "__main__":
    test_weather_data_rejects_none_wind_speed()
    test_weather_data_rejects_out_of_range_temperature()
    test_hourly_ptf_rejects_negative_price()
    test_hourly_ptf_accepts_valid_record()
    print("ALL_DATA_VALIDATION_TESTS_PASSED")
