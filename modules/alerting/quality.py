"""Alert quality proxy metrics — precision and false-positive tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from core.storage import PipelineStorage

ALERT_QUALITY_VERSION = "1.0.0"
_DEFAULT_PERIOD_DAYS = 7
_ELEVATED_RISK_THRESHOLD = 50
_HIGH_MAPE_THRESHOLD = 15.0
_HIGH_COST_THRESHOLD = 5000.0
_OUTCOME_RISK_DROP_THRESHOLD = 10.0


def _normalize_severity(value: str) -> str:
    return str(value or "INFO").upper()


def alert_fired(run: dict[str, Any]) -> bool:
    alert = run.get("alert_status") or {}
    severity = _normalize_severity(alert.get("severity", "INFO"))
    if severity in {"WARNING", "CRITICAL"}:
        return True

    for rule in run.get("rules") or []:
        rule_id = str(rule.get("rule_id") or "")
        if rule_id == "nominal_operations":
            continue
        rule_severity = _normalize_severity(str(rule.get("severity") or ""))
        if rule_severity in {"WARNING", "CRITICAL"}:
            return True
    return False


def metrics_support_alert(run: dict[str, Any]) -> bool:
    risk = float(run.get("risk_score") or 0.0)
    mape = float(run.get("mape_percentage") or 0.0)
    cost = float(run.get("total_imbalance_cost_tl") or 0.0)
    return (
        risk > _ELEVATED_RISK_THRESHOLD
        or mape > _HIGH_MAPE_THRESHOLD
        or cost > _HIGH_COST_THRESHOLD
    )


def evaluate_alert_quality(
    runs: list[dict[str, Any]],
    *,
    period_days: int = _DEFAULT_PERIOD_DAYS,
) -> dict[str, Any]:
    """Estimate alert precision and false-positive proxy from historical runs."""
    if not runs:
        return _empty_quality(0, period_days)

    ordered = list(reversed(runs))
    alerts_fired = 0
    justified = 0
    outcome_confirmed = 0
    false_positive_proxy = 0
    false_negative_proxy = 0
    alert_opportunities = 0

    for index, run in enumerate(ordered):
        supported = metrics_support_alert(run)
        if supported:
            alert_opportunities += 1
            if not alert_fired(run):
                false_negative_proxy += 1

        if not alert_fired(run):
            continue

        alerts_fired += 1
        if supported:
            justified += 1

        current_risk = float(run.get("risk_score") or 0.0)
        if index + 1 < len(ordered):
            next_risk = float(ordered[index + 1].get("risk_score") or 0.0)
            if next_risk >= current_risk - 5.0:
                outcome_confirmed += 1
            elif not supported and (current_risk - next_risk) >= _OUTCOME_RISK_DROP_THRESHOLD:
                false_positive_proxy += 1
        elif not supported:
            false_positive_proxy += 1

    precision_proxy = round(justified / max(1, alerts_fired), 4)
    false_positive_rate = round(false_positive_proxy / max(1, alerts_fired), 4)
    false_negative_rate = round(false_negative_proxy / max(1, alert_opportunities), 4)
    outcome_confirmed_rate = round(outcome_confirmed / max(1, alerts_fired), 4)
    quality_score = round(
        (
            precision_proxy * 0.4
            + (1.0 - false_positive_rate) * 0.25
            + (1.0 - false_negative_rate) * 0.2
            + outcome_confirmed_rate * 0.15
        )
        * 100,
        2,
    )

    return {
        "version": ALERT_QUALITY_VERSION,
        "period_days": period_days,
        "samples": len(runs),
        "alerts_fired": alerts_fired,
        "justified_alerts": justified,
        "precision_proxy": precision_proxy,
        "false_positive_proxy": false_positive_proxy,
        "false_positive_rate": false_positive_rate,
        "false_negative_proxy": false_negative_proxy,
        "false_negative_rate": false_negative_rate,
        "alert_opportunities": alert_opportunities,
        "outcome_confirmed_rate": outcome_confirmed_rate,
        "quality_score": quality_score,
        "reportable": alerts_fired >= 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_weekly_alert_report(
    asset_id: str,
    storage: Optional[PipelineStorage] = None,
    *,
    days: int = _DEFAULT_PERIOD_DAYS,
) -> dict[str, Any]:
    store = storage or PipelineStorage()
    runs = [
        run
        for run in store.get_recent_runs(limit=max(days * 3, 30))
        if run.get("asset_id") == asset_id
    ][: days * 2]
    quality = evaluate_alert_quality(runs, period_days=days)
    return {"asset_id": asset_id, **quality}


def _empty_quality(samples: int, period_days: int) -> dict[str, Any]:
    return {
        "version": ALERT_QUALITY_VERSION,
        "period_days": period_days,
        "samples": samples,
        "alerts_fired": 0,
        "justified_alerts": 0,
        "precision_proxy": 0.0,
        "false_positive_proxy": 0,
        "false_positive_rate": 0.0,
        "false_negative_proxy": 0,
        "false_negative_rate": 0.0,
        "alert_opportunities": 0,
        "outcome_confirmed_rate": 0.0,
        "quality_score": 0.0,
        "reportable": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
