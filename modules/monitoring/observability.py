"""FAZ 5 — observability özet metrikleri ve pipeline telemetry."""

from __future__ import annotations

from typing import Any

from modules.forecast.production.confidence_stack import CONFIDENCE_STACK_VERSION

OBSERVABILITY_VERSION = "1.0.0"
_EXPECTED_PIPELINE_STEPS = frozenset(
    {
        "0800_forecast",
        "0801_performance_monitoring",
        "0802_risk_calculation",
        "0803_alert_generation",
        "0804_ai_explanation",
        "0805_dashboard_update",
    }
)


def compute_source_success_rates(source_mode_counts: dict[str, dict[str, int]]) -> dict[str, float]:
    """Kaynak bazında live / (live+mock+fallback+simulated) başarı oranını hesaplar."""
    rates: dict[str, float] = {}
    for source_name, counts in source_mode_counts.items():
        live = int(counts.get("live", 0))
        mock = int(counts.get("mock", 0))
        fallback = int(counts.get("fallback", 0))
        simulated = int(counts.get("simulated", 0))
        total = live + mock + fallback + simulated
        rates[source_name] = round(live / total, 4) if total else 0.0
    return rates


def compute_pipeline_success_rate(audit_entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit trail üzerinden pipeline tamamlanma (API başarı) oranını hesaplar."""
    grouped: dict[tuple[str, str], set[str]] = {}
    for entry in audit_entries:
        if entry.get("status") != "completed":
            continue
        key = (str(entry.get("asset_id") or ""), str(entry.get("target_date") or ""))
        step = str(entry.get("step") or "")
        grouped.setdefault(key, set()).add(step)

    total_runs = len(grouped)
    successful_runs = sum(
        1 for steps in grouped.values() if _EXPECTED_PIPELINE_STEPS.issubset(steps)
    )
    success_rate = round(successful_runs / total_runs, 4) if total_runs else 1.0
    return {
        "pipeline_runs": total_runs,
        "successful_runs": successful_runs,
        "success_rate": success_rate,
        "expected_steps": len(_EXPECTED_PIPELINE_STEPS),
    }


def aggregate_coverage_metrics(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Confidence stack coverage metriklerinin ortalamasını döndürür."""
    rates: list[float] = []
    meets_target_count = 0
    for item in metrics:
        coverage = (item.get("confidence_stack") or {}).get("coverage") or item.get("coverage") or {}
        if coverage.get("coverage_rate") is None:
            continue
        rates.append(float(coverage["coverage_rate"]))
        if coverage.get("meets_target"):
            meets_target_count += 1

    avg_rate = round(sum(rates) / len(rates), 4) if rates else 0.0
    return {
        "version": CONFIDENCE_STACK_VERSION,
        "sample_size": len(rates),
        "avg_coverage_rate": avg_rate,
        "meets_target_runs": meets_target_count,
        "meets_target_ratio": round(meets_target_count / len(rates), 4) if rates else 0.0,
    }


def aggregate_pipeline_latency(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Pipeline step latency özetini hesaplar."""
    totals: list[float] = []
    step_samples: dict[str, list[float]] = {}

    for item in metrics:
        observability = item.get("observability") or {}
        step_timings = observability.get("step_timings_ms") or {}
        total_ms = observability.get("pipeline_total_ms")
        if total_ms is not None:
            totals.append(float(total_ms))
        for step, duration in step_timings.items():
            if step == "pipeline_total_ms":
                continue
            step_samples.setdefault(step, []).append(float(duration))

    avg_by_step = {
        step: round(sum(values) / len(values), 2)
        for step, values in step_samples.items()
        if values
    }
    return {
        "sample_size": len(totals),
        "avg_pipeline_total_ms": round(sum(totals) / len(totals), 2) if totals else 0.0,
        "avg_step_timings_ms": avg_by_step,
    }


def build_pipeline_observability_snapshot(
    *,
    step_timings_ms: dict[str, float],
    telemetry: dict[str, Any],
    confidence_stack: dict[str, Any],
    gates_passed: dict[str, bool],
) -> dict[str, Any]:
    """Tek pipeline run için observability snapshot üretir."""
    source_mode_counts = {
        name: {
            "live": 1 if (telemetry.get("sources", {}).get(name, {}) or {}).get("mode") == "live" else 0,
            "mock": 1 if (telemetry.get("sources", {}).get(name, {}) or {}).get("mode") == "mock" else 0,
        }
        for name in ("weather", "scada", "epias")
    }
    degraded_reasons = {
        name: (telemetry.get("sources", {}).get(name, {}) or {}).get("reason")
        for name in ("weather", "scada", "epias")
        if (telemetry.get("sources", {}).get(name, {}) or {}).get("reason") not in (None, "ok", "unknown")
    }
    coverage = confidence_stack.get("coverage") or {}
    return {
        "version": OBSERVABILITY_VERSION,
        "step_timings_ms": step_timings_ms,
        "pipeline_total_ms": step_timings_ms.get("pipeline_total_ms", 0.0),
        "is_degraded": bool(telemetry.get("is_degraded")),
        "degraded_sources": telemetry.get("degraded_sources", []),
        "fallback_reasons": degraded_reasons,
        "source_success_rates": compute_source_success_rates(source_mode_counts),
        "coverage_rate": coverage.get("coverage_rate"),
        "coverage_meets_target": coverage.get("meets_target"),
        "gates_passed": gates_passed,
        "api_success": all(gates_passed.values()) if gates_passed else True,
    }


def build_observability_summary(
    *,
    metrics: list[dict[str, Any]],
    audit_entries: list[dict[str, Any]],
    degraded_summary: dict[str, Any],
) -> dict[str, Any]:
    """Monitoring API için birleşik observability özeti üretir."""
    source_success_rates = compute_source_success_rates(degraded_summary.get("source_mode_counts", {}))
    api_success = compute_pipeline_success_rate(audit_entries)
    coverage = aggregate_coverage_metrics(metrics)
    latency = aggregate_pipeline_latency(metrics)

    return {
        "version": OBSERVABILITY_VERSION,
        "sample_size": len(metrics),
        "fallback_reasons": degraded_summary.get("degraded_reason_counts", {}),
        "degraded_ratio_pct": degraded_summary.get("degraded_ratio_pct", 0.0),
        "avg_mock_usage_rate": degraded_summary.get("avg_mock_usage_rate", 0.0),
        "source_success_rates": source_success_rates,
        "api_success": api_success,
        "latency": latency,
        "coverage": coverage,
        "endpoints": {
            "degraded_summary": True,
            "drift_summary": True,
            "recommendation_quality": True,
            "alert_quality": True,
            "confidence_stack": True,
            "model_attribution": True,
            "decision_causality": True,
            "model_registry": True,
            "experiments": True,
            "observability_summary": True,
        },
    }
