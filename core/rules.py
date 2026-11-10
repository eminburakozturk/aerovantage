"""Basit kural motoru — operasyonel bağlam değerlendirmesi."""

from __future__ import annotations

from typing import Any

from core.i18n import DEFAULT_LOCALE, normalize_locale, rule_texts


class RuleEngine:
    """Risk ve performans metriklerine göre kural tabanlı öneriler üretir."""

    def evaluate(self, context: dict[str, Any], locale: str | None = None) -> list[dict[str, Any]]:
        """Bağlam sözlüğüne göre tetiklenen kuralları döndürür."""
        loc = normalize_locale(locale or context.get("locale") or DEFAULT_LOCALE)
        triggered: list[dict[str, Any]] = []

        risk_score = int(context.get("risk_score", 0))
        mape_percentage = float(context.get("mape_percentage", 0))
        total_cost = float(context.get("total_imbalance_cost_tl", 0))
        simulation = context.get("ground_truth_mode") in {
            "simulated",
            "mock",
            "simulation",
        } or context.get("mape_informational") is True

        def _sev(production: str) -> str:
            if not simulation:
                return production
            if production == "CRITICAL":
                return "INFO"
            if production == "WARNING":
                return "INFO"
            return production

        def _append(rule_id: str, severity: str) -> None:
            texts = rule_texts(loc, rule_id, simulation=simulation)
            triggered.append(
                {
                    "rule_id": rule_id,
                    "severity": severity,
                    "message": texts["message"],
                    "action": texts["action"],
                }
            )

        if risk_score > 75:
            _append("critical_risk", _sev("CRITICAL"))
        elif risk_score > 50:
            _append("elevated_risk", _sev("WARNING"))

        if mape_percentage > 15.0:
            _append("high_mape", _sev("WARNING"))

        if total_cost > 5000.0:
            _append("high_imbalance_cost", _sev("WARNING"))

        if not triggered:
            _append("nominal_operations", "INFO")

        return triggered
