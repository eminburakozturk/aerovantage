"""SCADA Data Hub entegrasyon testleri."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.config import Settings
from modules.data_hub.scada import ScadaClient
from modules.performance.service import PerformanceMonitoringService


def test_scada_mock_returns_hourly_dict() -> None:
    client = ScadaClient(settings=Settings(scada_use_mock=True, epias_use_mock=True))
    result = client.fetch_actual_generation("RES-BAL-01", "2026-07-06")
    assert len(result) == 24
    assert "00:00" in result
    assert "23:00" in result
    assert all(isinstance(value, float) for value in result.values())
    assert client.get_last_fetch_meta()["mode"] == "mock"
    assert client.get_last_fetch_meta()["live"] == "false"


def test_scada_rest_parse_flat_payload() -> None:
    client = ScadaClient(settings=Settings(scada_use_mock=True, epias_use_mock=True))
    parsed = client._parse_generation_payload({"08:00": 42.5, "09:00": 41.2})
    assert parsed["08:00"] == 42.5
    assert parsed["09:00"] == 41.2


def test_scada_live_fallback_to_mock_on_error() -> None:
    session = MagicMock()
    session.get.side_effect = ConnectionError("SCADA unreachable")
    client = ScadaClient(
        settings=Settings(
            scada_use_mock=False,
            scada_api_url="http://scada.local/api",
            epias_use_mock=True,
        ),
        session=session,
    )
    result = client.fetch_actual_generation("RES-BAL-01", "2026-07-06")
    assert len(result) == 24
    assert client.get_last_fetch_meta()["mode"] == "mock"
    assert client.get_last_fetch_meta()["reason"] in {"request_failed", "epias_also_mock"}


def test_scada_epias_simulator_scales_national_wind() -> None:
    epias = MagicMock()
    epias.fetch_hourly_wind_generation.return_value = {
        f"{hour:02d}:00": 6000.0 for hour in range(24)
    }
    client = ScadaClient(
        settings=Settings(scada_use_mock=True, epias_use_mock=False),
        epias_client=epias,
    )
    result = client.fetch_actual_generation("RES-BAL-01", "2026-07-06")
    meta = client.get_last_fetch_meta()
    assert len(result) == 24
    assert meta["mode"] == "simulated"
    assert meta["source"] == "simulated_from_epias"
    assert meta["confidence"] == "simulated"
    assert meta["live"] == "false"
    assert "EPİAŞ" in meta["label"] or "Operational" in meta["label"]
    assert meta.get("operational_layer") == "derived"
    assert meta.get("equipment_layer") == "mock"
    assert "observed_hours" in meta
    # 50 MW / 12000 MW * 6000 = 25 MW
    assert result["12:00"] == 25.0
    assert "12:00" in meta["observed_hours"]


def test_scada_ping_reports_simulated_provider() -> None:
    client = ScadaClient(settings=Settings(scada_use_mock=True, epias_use_mock=False))
    ping = client.ping()
    assert ping["mode"] == "simulated"
    assert ping["source"] == "simulated_from_epias"
    assert ping["live"] == "false"


def test_scada_influx_adapter_parses_payload() -> None:
    session = MagicMock()
    session.get.return_value.raise_for_status.return_value = None
    session.get.return_value.json.return_value = {"08:00": 14.2, "09:00": 13.7}
    client = ScadaClient(
        settings=Settings(scada_use_mock=False, scada_api_url="influx://influx.local:8086/scada"),
        session=session,
    )
    result = client.fetch_actual_generation("RES-BAL-01", "2026-07-06")
    assert result["08:00"] == 14.2
    assert client.get_last_fetch_meta()["mode"] == "live"
    assert client.get_last_fetch_meta()["live"] == "true"


def test_performance_uses_scada_client() -> None:
    mock_scada = MagicMock()
    mock_scada.fetch_actual_generation.return_value = {
        "08:00": 9.5,
        "09:00": 11.0,
    }
    mock_scada.get_last_fetch_meta.return_value = {"mode": "live", "reason": "ok"}
    service = PerformanceMonitoringService(scada_client=mock_scada)
    result = service.evaluate_performance(
        {
            "hours": [
                {"timestamp": "2026-07-06T08:00:00", "generated_mw": 10.0},
                {"timestamp": "2026-07-06T09:00:00", "generated_mw": 12.0},
            ]
        },
        asset_id="RES-BAL-01",
        target_date="2026-07-06",
    )
    assert mock_scada.fetch_actual_generation.called
    assert result["hours"][0]["actual_mw"] == 9.5
    assert result["hours"][0]["deviation_mw"] == -0.5
    assert result["scada"]["mode"] == "live"


if __name__ == "__main__":
    test_scada_mock_returns_hourly_dict()
    test_scada_rest_parse_flat_payload()
    test_scada_live_fallback_to_mock_on_error()
    test_scada_epias_simulator_scales_national_wind()
    test_scada_ping_reports_simulated_provider()
    test_performance_uses_scada_client()
    print("ALL_SCADA_TESTS_PASSED")
