"""Alerting & Notification Engine servisi."""

from __future__ import annotations

from typing import Any

from core.i18n import DEFAULT_LOCALE, compose_alert_message, normalize_locale
from core.logger import get_logger
from modules.alerting.schemas import Alert
from modules.data_hub.ground_truth import scada_is_proxy


class AlertingService:
    """Risk ve performans verisine göre operasyonel uyarı üretir."""

    def __init__(self) -> None:
        self._logger = get_logger("modules.alerting")

    def evaluate_conditions_and_generate_alert(
        self,
        risk_data: dict[str, Any],
        performance_data: dict[str, Any],
        asset_id: str,
        locale: str = DEFAULT_LOCALE,
    ) -> dict[str, Any]:
        """Risk ve performans koşullarına göre severity ve mesaj içeren Alert döndürür."""
        risk_score = int(risk_data.get("risk_score", 0))
        mape_percentage = float(performance_data.get("mape_percentage", 0))
        proxy = (
            scada_is_proxy(performance_data.get("scada"))
            or performance_data.get("evaluation_mode") == "simulation"
            or performance_data.get("mape_informational") is True
            or risk_data.get("ground_truth_mode") in {"simulated", "mock", "simulation"}
        )

        severity, message = compose_alert_message(
            normalize_locale(locale),
            risk_score=risk_score,
            mape_percentage=mape_percentage,
            proxy=proxy,
        )

        alert = Alert(
            asset_id=asset_id,
            severity=severity,  # type: ignore[arg-type]
            message=message,
        )

        self._logger.info(
            "Alert uretildi: asset_id=%s severity=%s risk_score=%s mape=%.2f proxy=%s",
            asset_id,
            severity,
            risk_score,
            mape_percentage,
            proxy,
        )

        return alert.model_dump(mode="json")
