"""Data Integration Hub import ve pipeline smoke testleri."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.main import app
from modules.data_hub.epias import EpiasClient
from modules.data_hub.schemas import DayAheadPTFResponse, WeatherForecastResponse
from modules.data_hub.weather import WeatherClient


class _FakeEpiasResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _FakeEpiasSession:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def post(self, *args, **kwargs) -> _FakeEpiasResponse:
        return _FakeEpiasResponse(self._payload)


def test_data_hub_weather_import() -> None:
    client = WeatherClient()
    result = client.fetch_hourly_forecast(39.64, 27.88, date(2026, 7, 6))
    assert isinstance(result, WeatherForecastResponse)
    assert len(result.hours) == 24


def test_data_hub_epias_import() -> None:
    client = EpiasClient()
    result = client.fetch_day_ahead_ptf(date(2026, 7, 6))
    assert isinstance(result, DayAheadPTFResponse)
    assert len(result.hours) == 24


def test_data_hub_epias_live_mapping() -> None:
    payload = {
        "items": [{"hour": hour, "price": 3000 + hour} for hour in range(24)],
    }
    auth = MagicMock()
    auth.get_auth_headers.return_value = {"TGT": "TGT-test"}
    auth.invalidate.return_value = None
    client = EpiasClient(
        settings=SimpleNamespace(
            epias_use_mock=False,
            epias_base_url="https://seffaflik.epias.com.tr/electricity-service/v1",
            epias_api_key=SimpleNamespace(get_secret_value=lambda: ""),
        ),
        session=_FakeEpiasSession(payload),
        auth=auth,
    )
    result = client.fetch_day_ahead_ptf(date(2026, 7, 6))
    assert result.source == "epias-live"
    assert len(result.hours) == 24
    assert result.hours[0].ptf == 3000
    assert client.get_last_fetch_meta()["mode"] == "live"


def test_pipeline_no_import_errors(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/pipeline/trigger-pipeline",
        json={"asset_id": "RES-BAL-01", "target_date": "2026-07-06"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["steps_completed"]) == 6


if __name__ == "__main__":
    test_data_hub_weather_import()
    test_data_hub_epias_import()
    test_pipeline_no_import_errors()
    print("ALL_DATA_HUB_TESTS_PASSED")
