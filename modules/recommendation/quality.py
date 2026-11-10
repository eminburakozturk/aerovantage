"""Recommendation quality proxy metrics — single source for operational intelligence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from core.storage import PipelineStorage

RECOMMENDATION_QUALITY_VERSION = "1.0.0"
_DEFAULT_PERIOD_DAYS = 7
_MIN_REPORTABLE_SAMPLES = 2


def _has_action(run: dict[str, Any]) -> bool:
    action = str(run.get("action_plan") or "").strip()
    return bool(action and action.lower() != "standart izleme prosedürüne devam et")


def evaluate_recommendation_quality(
    runs: list[dict[str, Any]],
    *,
    period_days: int = _DEFAULT_PERIOD_DAYS,
) -> dict[str, Any]:
    """Compute proxy metrics for recommendation -> outcome linkage."""
    if len(runs) < _MIN_REPORTABLE_SAMPLES:
        return _empty_quality(len(runs), period_days)

    ordered = list(reversed(runs))
    evaluated = 0
    with_action = 0
    risk_improved = 0
    cost_improved = 0
    mape_improved = 0

    for prev, curr in zip(ordered, ordered[1:]):
        if _has_action(prev):
            with_action += 1
            evaluated += 1
            prev_risk = float(prev.get("risk_score") or 0.0)
            curr_risk = float(curr.get("risk_score") or 0.0)
            prev_cost = float(prev.get("total_imbalance_cost_tl") or 0.0)
            curr_cost = float(curr.get("total_imbalance_cost_tl") or 0.0)
            prev_mape = float(prev.get("mape_percentage") or 0.0)
            curr_mape = float(curr.get("mape_percentage") or 0.0)

            if curr_risk < prev_risk:
                risk_improved += 1
            if curr_cost < prev_cost:
                cost_improved += 1
            if curr_mape < prev_mape:
                mape_improved += 1

    action_coverage = round(with_action / max(1, len(runs)), 4)
    improved_after_action_ratio = round(risk_improved / max(1, evaluated), 4)
    cost_improved_after_action_ratio = round(cost_improved / max(1, evaluated), 4)
    mape_improved_after_action_ratio = round(mape_improved / max(1, evaluated), 4)
    quality_score = round(
        (
            action_coverage * 0.35
            + improved_after_action_ratio * 0.35
            + cost_improved_after_action_ratio * 0.15
            + mape_improved_after_action_ratio * 0.15
        )
        * 100,
        2,
    )

    return {
        "version": RECOMMENDATION_QUALITY_VERSION,
        "period_days": period_days,
        "samples": len(runs),
        "evaluated_actions": evaluated,
        "action_coverage": action_coverage,
        "improved_after_action_ratio": improved_after_action_ratio,
        "cost_improved_after_action_ratio": cost_improved_after_action_ratio,
        "mape_improved_after_action_ratio": mape_improved_after_action_ratio,
        "quality_score": quality_score,
        "reportable": evaluated >= 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_weekly_report(
    asset_id: str,
    storage: Optional[PipelineStorage] = None,
    *,
    days: int = _DEFAULT_PERIOD_DAYS,
) -> dict[str, Any]:
    """Build a weekly recommendation quality report for an asset."""
    store = storage or PipelineStorage()
    runs = [
        run
        for run in store.get_recent_runs(limit=max(days * 3, 30))
        if run.get("asset_id") == asset_id
    ][: days * 2]
    quality = evaluate_recommendation_quality(runs, period_days=days)
    return {
        "asset_id": asset_id,
        **quality,
    }


def _empty_quality(samples: int, period_days: int) -> dict[str, Any]:
    return {
        "version": RECOMMENDATION_QUALITY_VERSION,
        "period_days": period_days,
        "samples": samples,
        "evaluated_actions": 0,
        "action_coverage": 0.0,
        "improved_after_action_ratio": 0.0,
        "cost_improved_after_action_ratio": 0.0,
        "mape_improved_after_action_ratio": 0.0,
        "quality_score": 0.0,
        "reportable": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
