"""Alerting motoru — MAPE ve risk koşul testleri."""

from __future__ import annotations

from modules.alerting.service import AlertingService


def test_mape_warning_when_risk_low() -> None:
    service = AlertingService()
    alert = service.evaluate_conditions_and_generate_alert(
        risk_data={"risk_score": 10},
        performance_data={"mape_percentage": 18.5},
        asset_id="RES-BAL-01",
    )
    assert alert["severity"] == "WARNING"
    assert "MAPE: %18.5" in alert["message"]
    assert "Model güncellemesi gerekebilir" in alert["message"]


def test_risk_warning_prioritized_with_mape() -> None:
    service = AlertingService()
    alert = service.evaluate_conditions_and_generate_alert(
        risk_data={"risk_score": 60},
        performance_data={"mape_percentage": 20.0},
        asset_id="RES-BAL-01",
    )
    assert alert["severity"] == "WARNING"
    assert "Yüksek dengesizlik riski" in alert["message"]
    assert "MAPE: %20.0" in alert["message"]


def test_info_when_risk_and_mape_normal() -> None:
    service = AlertingService()
    alert = service.evaluate_conditions_and_generate_alert(
        risk_data={"risk_score": 20},
        performance_data={"mape_percentage": 8.0},
        asset_id="RES-BAL-01",
    )
    assert alert["severity"] == "INFO"
    assert "operasyonel sınırlar içinde" in alert["message"]


if __name__ == "__main__":
    test_mape_warning_when_risk_low()
    test_risk_warning_prioritized_with_mape()
    test_info_when_risk_and_mape_normal()
    print("ALL_ALERTING_TESTS_PASSED")
