"""Faz 2 entegrasyon smoke testi."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import requests
from pydantic import SecretStr

from core.config import Settings
from modules.data_hub.weather import WeatherClient
from modules.data_hub.epias import EpiasClient


def test_open_meteo_balikesir() -> None:
    client = WeatherClient(settings=Settings(weather_use_mock=False))
    target = date.today() + timedelta(days=1)
    result = client.fetch_hourly_forecast(39.64, 27.88, target)
    assert result.source == "open-meteo"
    assert len(result.hours) == 24
    assert result.hours[0].wind_speed >= 0
    print(
        f"OPEN_METEO_OK hours={len(result.hours)} "
        f"wind={result.hours[12].wind_speed} temp={result.hours[12].temperature}"
    )


def test_epias_auth_fallback() -> None:
    session = requests.Session()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {}
    mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
    session.post = MagicMock(return_value=mock_response)

    auth = MagicMock()
    auth.get_auth_headers.return_value = {"TGT": "TGT-test"}
    auth.invalidate.return_value = None

    client = EpiasClient(
        settings=Settings(
            epias_use_mock=False,
            epias_username=SecretStr("user"),
            epias_password=SecretStr("pass"),
        ),
        session=session,
        auth=auth,
    )
    result = client.fetch_day_ahead_ptf(date.today())
    assert result.source == "epias-mock:auth_failed"
    assert len(result.hours) == 24
    print(f"EPIAS_FALLBACK_OK source={result.source} hours={len(result.hours)}")


if __name__ == "__main__":
    test_open_meteo_balikesir()
    test_epias_auth_fallback()
    print("ALL_TESTS_PASSED")
