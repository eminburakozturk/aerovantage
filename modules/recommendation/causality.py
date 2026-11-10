"""Decision causality signals for recommendation outcome loops."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any, Optional

from core.storage import PipelineStorage
from modules.recommendation.quality import _has_action

CAUSALITY_VERSION = "1.0.0"
_DEFAULT_PERIOD_DAYS = 7


def _composite_improvement(prev: dict[str, Any], curr: dict[str, Any]) -> float:
    risk_delta = float(prev.get("risk_score") or 0.0) - float(curr.get("risk_score") or 0.0)
    cost_delta = float(prev.get("total_imbalance_cost_tl") or 0.0) - float(
        curr.get("total_imbalance_cost_tl") or 0.0
    )
    mape_delta = float(prev.get("mape_percentage") or 0.0) - float(curr.get("mape_percentage") or 0.0)
    return 0.5 * risk_delta + 0.3 * (cost_delta / 10000.0) + 0.2 * mape_delta


def evaluate_decision_causality(
    runs: list[dict[str, Any]],
    *,
    period_days: int = _DEFAULT_PERIOD_DAYS,
) -> dict[str, Any]:
    """Estimate causality lift between action and control transition pairs."""
    if len(runs) < 2:
        return _empty_causality(len(runs), period_days)

    ordered = list(reversed(runs))
    with_action_improvements: list[float] = []
    without_action_improvements: list[float] = []

    for prev, curr in zip(ordered, ordered[1:]):
        improvement = _composite_improvement(prev, curr)
        if _has_action(prev):
            with_action_improvements.append(improvement)
        else:
            without_action_improvements.append(improvement)

    avg_with = mean(with_action_improvements) if with_action_improvements else 0.0
    avg_without = mean(without_action_improvements) if without_action_improvements else 0.0
    causality_lift = avg_with - avg_without

    if causality_lift > 0.5:
        signal = "positive"
    elif causality_lift < -0.5:
        signal = "negative"
    else:
        signal = "neutral"

    return {
        "version": CAUSALITY_VERSION,
        "period_days": period_days,
        "samples": len(runs),
        "action_pairs": len(with_action_improvements),
        "control_pairs": len(without_action_improvements),
        "avg_improvement_with_action": round(avg_with, 4),
        "avg_improvement_without_action": round(avg_without, 4),
        "causality_lift": round(causality_lift, 4),
        "causality_signal": signal,
        "reportable": len(with_action_improvements) >= 1 and len(without_action_improvements) >= 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_causality_report(
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
    causality = evaluate_decision_causality(runs, period_days=days)
    return {"asset_id": asset_id, **causality}


def _empty_causality(samples: int, period_days: int) -> dict[str, Any]:
    return {
        "version": CAUSALITY_VERSION,
        "period_days": period_days,
        "samples": samples,
        "action_pairs": 0,
        "control_pairs": 0,
        "avg_improvement_with_action": 0.0,
        "avg_improvement_without_action": 0.0,
        "causality_lift": 0.0,
        "causality_signal": "neutral",
        "reportable": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
