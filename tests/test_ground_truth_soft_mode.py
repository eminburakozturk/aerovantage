"""Ground-truth / simulated MAPE & alert soft-mode tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.rules import RuleEngine
from modules.alerting.service import AlertingService
from modules.data_hub.ground_truth import enrich_scada_layer_meta, scada_is_proxy
from modules.performance.mape import aggregate_mape
from modules.performance.service import PerformanceMonitoringService


def test_scada_is_proxy_for_simulated() -> None:
    assert scada_is_proxy({"mode": "simulated", "live": "false"})
    assert scada_is_proxy({"mode": "mock", "live": "false"})
    assert not scada_is_proxy({"mode": "live", "live": "true"})


def test_enrich_layers_for_simulated() -> None:
    meta = enrich_scada_layer_meta({"mode": "simulated", "live": "false"})
    assert meta["operational_layer"] == "derived"
    assert meta["equipment_layer"] == "mock"


def test_mape_skips_padded_hours_via_observed_pairs() -> None:
    # Only observed night hours with match → low mape; pad excluded by service pairs
    pairs = [(20.0, 20.5), (21.0, 20.8)]
    assert aggregate_mape(pairs) < 5.0


def test_performance_marks_unobserved_and_informational() -> None:
    mock_scada = MagicMock()
    mock_scada.fetch_actual_generation.return_value = {
        "00:00": 20.0,
        "01:00": 20.0,
        "08:00": 0.0,
        "09:00": 0.0,
    }
    mock_scada.get_last_fetch_meta.return_value = {
        "mode": "simulated",
        "source": "simulated_from_epias",
        "live": "false",
        "observed_hours": ["00:00", "01:00"],
        "padded_hours": ["08:00", "09:00"],
    }
    service = PerformanceMonitoringService(scada_client=mock_scada)
    result = service.evaluate_performance(
        {
            "hours": [
                {"timestamp": "2026-07-12T00:00:00", "generated_mw": 19.5},
                {"timestamp": "2026-07-12T01:00:00", "generated_mw": 20.2},
                {"timestamp": "2026-07-12T08:00:00", "generated_mw": 5.0},
                {"timestamp": "2026-07-12T09:00:00", "generated_mw": 6.0},
            ]
        },
        asset_id="RES-BAL-01",
        target_date="2026-07-12",
    )
    assert result["evaluation_mode"] == "simulation"
    assert result["mape_informational"] is True
    assert result["padded_hour_count"] == 2
    assert result["observed_hour_count"] == 2
    assert result["mape_percentage"] < 10.0
    by_ts = {h["timestamp"][:13]: h for h in result["hours"]}
    assert by_ts["2026-07-12T08"]["observed"] is False
    assert by_ts["2026-07-12T00"]["observed"] is True


def test_alert_softened_in_simulation() -> None:
    alert = AlertingService().evaluate_conditions_and_generate_alert(
        risk_data={"risk_score": 100},
        performance_data={
            "mape_percentage": 100.0,
            "evaluation_mode": "simulation",
            "mape_informational": True,
            "scada": {"mode": "simulated", "live": "false"},
        },
        asset_id="RES-BAL-01",
    )
    assert alert["severity"] == "WARNING"
    assert alert["message"].startswith("[Simülasyon]")


def test_rules_informational_in_simulation() -> None:
    rules = RuleEngine().evaluate(
        {
            "risk_score": 100,
            "mape_percentage": 100.0,
            "total_imbalance_cost_tl": 20000,
            "ground_truth_mode": "simulated",
            "mape_informational": True,
        }
    )
    assert all(rule["severity"] == "INFO" for rule in rules)
    assert any(rule["rule_id"] == "high_mape" for rule in rules)
