"""FAZ 1 — gerçek veri güvenilirliği testleri."""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from modules.data_hub.epias import EpiasClient
from modules.data_hub.freshness import check_hourly_freshness
from modules.data_hub.nasa_power import NasaPowerClient
from modules.data_hub.schemas import WeatherData
from modules.data_hub.source_telemetry import build_pipeline_telemetry, parse_source_label
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


def test_epias_live_mapping_sets_meta() -> None:
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
    meta = client.get_last_fetch_meta()
    assert meta["mode"] == "live"
    assert meta["reason"] == "ok"


def test_epias_mapping_failure_falls_back_to_mock() -> None:
    auth = MagicMock()
    auth.get_auth_headers.return_value = {"TGT": "TGT-test"}
    auth.invalidate.return_value = None
    client = EpiasClient(
        settings=SimpleNamespace(
            epias_use_mock=False,
            epias_base_url="https://seffaflik.epias.com.tr/electricity-service/v1",
            epias_api_key=SimpleNamespace(get_secret_value=lambda: ""),
        ),
        session=_FakeEpiasSession({"items": []}),
        auth=auth,
    )
    result = client.fetch_day_ahead_ptf(date(2026, 7, 6))
    assert result.source == "epias-mock:mapping_failed"
    assert client.get_last_fetch_meta()["reason"] == "mapping_failed"


def test_epias_forced_mock_only_when_configured() -> None:
    client = EpiasClient(
        settings=SimpleNamespace(epias_use_mock=True, epias_api_key=SimpleNamespace(get_secret_value=lambda: "")),
        session=_FakeEpiasSession({}),
    )
    result = client.fetch_day_ahead_ptf(date(2026, 7, 6))
    assert result.source == "epias-mock:forced_mock"
    assert client.get_last_fetch_meta()["mode"] == "mock"


def test_nasa_power_parse_response() -> None:
    payload = {
        "properties": {
            "parameter": {
                "T2M": {"2026070608": 22.5, "2026070609": 23.1},
                "WS10M": {"2026070608": 6.2, "2026070609": 7.0},
                "WD10M": {"2026070608": 180.0, "2026070609": 190.0},
                "PS": {"2026070608": 1012.0, "2026070609": 1013.0},
            }
        }
    }
    client = NasaPowerClient()
    hours = client.parse_response(payload, date(2026, 7, 6))
    assert len(hours) == 2
    assert hours[0].wind_speed == 6.2


def test_weather_open_meteo_failure_uses_nasa_power() -> None:
    nasa_hours = [
        WeatherData(
            timestamp=datetime(2026, 7, 6, hour, tzinfo=timezone.utc),
            temperature=20.0,
            wind_speed=8.0,
            wind_direction=200.0,
            air_pressure=1013.0,
        )
        for hour in range(24)
    ]
    session = MagicMock()
    session.get.side_effect = ConnectionError("open-meteo down")

    weather_client = WeatherClient(
        settings=SimpleNamespace(weather_use_mock=False),
        session=session,
    )
    weather_client._nasa_client = MagicMock()
    weather_client._nasa_client.fetch_hourly.return_value = nasa_hours

    result = weather_client.fetch_hourly_forecast(39.64, 27.88, date(2026, 7, 6))
    assert result.source == "nasa-power"
    assert weather_client.get_last_fetch_meta()["mode"] == "live"


def test_freshness_detects_stale_data() -> None:
    hours = [
        WeatherData(
            timestamp=datetime(2020, 1, 1, hour, tzinfo=timezone.utc),
            temperature=10.0,
            wind_speed=5.0,
            wind_direction=180.0,
            air_pressure=1010.0,
        )
        for hour in range(24)
    ]
    freshness = check_hourly_freshness(
        hours,
        date(2020, 1, 1),
        reference_time=datetime(2026, 7, 7, tzinfo=timezone.utc),
    )
    assert freshness["freshness_ok"] is False
    assert freshness["reason"] == "stale_data"


def test_pipeline_telemetry_mock_usage_rate() -> None:
    telemetry = build_pipeline_telemetry(
        weather_source="weather-mock:forced_mock",
        weather_meta={"mode": "mock", "reason": "forced_mock"},
        scada_source={"mode": "live", "reason": "ok", "source": "scada-live"},
        epias_source="epias-live",
        epias_meta={"mode": "live", "reason": "ok"},
        llm_meta={"mode": "live", "reason": "ok", "source": "gemini", "provider": "gemini"},
    )
    assert telemetry["mock_source_count"] == 1
    assert telemetry["live_source_count"] == 3
    assert telemetry["mock_usage_rate"] == round(1 / 4, 4)
    assert "weather" in telemetry["degraded_sources"]
    assert telemetry["sources"]["gemini"]["mode"] == "live"


def test_parse_source_label_mock_reason() -> None:
    parsed = parse_source_label("epias-mock:auth_failed")
    assert parsed["mode"] == "mock"
    assert parsed["reason"] == "auth_failed"
