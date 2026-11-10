"""Sistem izleme API rotaları."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from core.config import get_settings
from core.i18n import normalize_locale, translate
from core.logger import get_logger
from core.storage import PipelineStorage
from modules.alerting.quality import build_weekly_alert_report
from modules.forecast.production.explainability import EXPLAINABILITY_VERSION
from modules.forecast.production.confidence_stack import CONFIDENCE_STACK_VERSION
from modules.ml_registry.registry import (
    MODEL_REGISTRY_VERSION,
    get_latest_registry_entry,
    list_registry_entries,
    load_experiment_bundle,
)
from modules.monitoring.drift import summarize_drift_metrics
from modules.monitoring.observability import (
    OBSERVABILITY_VERSION,
    build_observability_summary,
)
from modules.recommendation.causality import build_causality_report
from modules.recommendation.quality import build_weekly_report

router = APIRouter()
_storage = PipelineStorage()
_logger = get_logger("api.monitoring")
_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@router.get("/audit")
def get_audit_trail(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
    """Pipeline adım adım audit kayıtlarını döndürür."""
    return _storage.get_audit_trail(limit=limit)


@router.get("/jobs")
def get_background_jobs(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
    """Son pipeline çalıştırmalarını arka plan işi olarak listeler."""
    runs = _storage.get_recent_runs(limit=limit)
    jobs = []
    for run in runs:
        jobs.append(
            {
                "job_id": run.get("saved_at", ""),
                "type": "daily_pipeline",
                "asset_id": run.get("asset_id"),
                "target_date": run.get("target_date"),
                "status": "completed",
                "risk_score": run.get("risk_score"),
                "mape_percentage": run.get("mape_percentage"),
            }
        )
    return jobs


@router.get("/scheduler")
def get_scheduler_status(
    locale: str = Query(default="tr", description="Cikti dili: tr, en, de"),
) -> dict[str, Any]:
    """Zamanlanmış görev durumunu döndürür."""
    loc = normalize_locale(locale)
    runs = _storage.get_recent_runs(limit=1)
    last_run = runs[0] if runs else None
    now = datetime.now(timezone.utc)
    next_run = (now + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)

    return {
        "timezone": "Europe/Istanbul",
        "jobs": [
            {
                "id": "daily_pipeline",
                "name": translate(loc, "monitoring.daily_pipeline"),
                "schedule": "08:00 Europe/Istanbul",
                "status": "active",
                "last_run": last_run.get("saved_at") if last_run else None,
                "last_asset_id": last_run.get("asset_id") if last_run else None,
                "next_run": next_run.isoformat(),
            },
            {
                "id": "kpi_refresh",
                "name": translate(loc, "monitoring.kpi_refresh"),
                "schedule": translate(loc, "monitoring.kpi_schedule"),
                "status": "active",
                "last_run": last_run.get("saved_at") if last_run else None,
                "next_run": (now + timedelta(minutes=30)).isoformat(),
            },
        ],
    }


@router.get("/logs")
def get_application_logs(
    limit: int = Query(default=100, ge=1, le=500),
    locale: str = Query(default="tr", description="Cikti dili: tr, en, de"),
) -> list[dict[str, str]]:
    """Uygulama log dosyasından son kayıtları döndürür."""
    log_file = _LOG_DIR / "app.log"
    if not log_file.exists():
        return [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "message": translate(normalize_locale(locale), "monitoring.log_empty"),
            }
        ]

    lines: list[str] = []
    with log_file.open(encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()

    entries = []
    for line in reversed(lines[-limit:]):
        line = line.strip()
        if not line:
            continue
        parts = line.split(" | ", 3)
        if len(parts) >= 4:
            entries.append(
                {
                    "timestamp": parts[0],
                    "level": parts[1].strip(),
                    "source": parts[2].strip(),
                    "message": parts[3].strip(),
                }
            )
        else:
            entries.append({"timestamp": "", "level": "INFO", "source": "app", "message": line})
    return entries


@router.get("/metrics")
def get_model_metrics(
    asset_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=300),
) -> list[dict[str, Any]]:
    """Model değerlendirme ve drift metriklerini döndürür."""
    return _storage.get_recent_metrics(asset_id=asset_id, limit=limit)


@router.get("/degraded-summary")
def get_degraded_summary(
    asset_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    """Fallback/degraded telemetry özetini döndürür."""
    metrics = _storage.get_recent_metrics(asset_id=asset_id, limit=limit)
    total = len(metrics)
    degraded_count = 0
    source_counts: dict[str, dict[str, int]] = {
        "weather": {"mock": 0, "live": 0, "simulated": 0, "fallback": 0},
        "scada": {"mock": 0, "live": 0, "simulated": 0, "fallback": 0},
        "epias": {"mock": 0, "live": 0, "simulated": 0, "fallback": 0},
        "gemini": {"mock": 0, "live": 0, "simulated": 0, "fallback": 0},
    }
    reason_counts: dict[str, int] = {}
    mock_usage_rates: list[float] = []

    for item in metrics:
        telemetry = item.get("telemetry", {})
        if telemetry.get("is_degraded"):
            degraded_count += 1
        if telemetry.get("mock_usage_rate") is not None:
            mock_usage_rates.append(float(telemetry["mock_usage_rate"]))
        sources = telemetry.get("sources", {})
        for source_name in ("weather", "scada", "epias", "gemini"):
            mode = (sources.get(source_name, {}) or {}).get("mode", "unknown")
            bucket = source_counts[source_name]
            if mode in bucket:
                bucket[mode] += 1
            reason = (sources.get(source_name, {}) or {}).get("reason")
            if reason and reason not in ("ok", "unknown"):
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

    degraded_ratio = round((degraded_count / total) * 100, 2) if total else 0.0
    avg_mock_usage_rate = (
        round(sum(mock_usage_rates) / len(mock_usage_rates), 4) if mock_usage_rates else 0.0
    )
    return {
        "version": OBSERVABILITY_VERSION,
        "sample_size": total,
        "degraded_runs": degraded_count,
        "degraded_ratio_pct": degraded_ratio,
        "avg_mock_usage_rate": avg_mock_usage_rate,
        "source_mode_counts": source_counts,
        "degraded_reason_counts": reason_counts,
    }


@router.get("/observability-summary")
def get_observability_summary(
    asset_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    """Birleşik observability özeti — fallback, başarı oranı, latency, coverage."""
    metrics = _storage.get_recent_metrics(asset_id=asset_id, limit=limit)
    audit_entries = _storage.get_audit_trail(limit=limit)
    degraded = get_degraded_summary(asset_id=asset_id, limit=limit)
    summary = build_observability_summary(
        metrics=metrics,
        audit_entries=audit_entries,
        degraded_summary=degraded,
    )
    if asset_id:
        summary["asset_id"] = asset_id
    _logger.info(
        "Observability summary: asset_id=%s sample_size=%s api_success_rate=%s",
        asset_id,
        summary.get("sample_size"),
        (summary.get("api_success") or {}).get("success_rate"),
    )
    return summary


@router.get("/recommendation-quality")
def get_recommendation_quality(
    asset_id: str = Query(..., min_length=1),
    days: int = Query(default=7, ge=1, le=30),
) -> dict[str, Any]:
    """Haftalık recommendation quality proxy raporu döndürür."""
    report = build_weekly_report(asset_id=asset_id, storage=_storage, days=days)
    _logger.info(
        "Recommendation quality raporu: asset_id=%s days=%s reportable=%s score=%s",
        asset_id,
        days,
        report.get("reportable"),
        report.get("quality_score"),
    )
    return report


@router.get("/drift-summary")
def get_drift_summary(
    asset_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    """Statistical drift ve residual sinyal özetini döndürür."""
    metrics = _storage.get_recent_metrics(asset_id=asset_id, limit=limit)
    summary = summarize_drift_metrics(metrics)
    _logger.info(
        "Drift summary: asset_id=%s sample_size=%s mape_drift_runs=%s cost_drift_runs=%s",
        asset_id,
        summary.get("sample_size"),
        summary.get("mape_drift_runs"),
        summary.get("cost_drift_runs"),
    )
    return summary


@router.get("/alert-quality")
def get_alert_quality(
    asset_id: str = Query(..., min_length=1),
    days: int = Query(default=7, ge=1, le=30),
) -> dict[str, Any]:
    """Haftalık alert quality (precision / false-positive proxy) raporu döndürür."""
    report = build_weekly_alert_report(asset_id=asset_id, storage=_storage, days=days)
    _logger.info(
        "Alert quality raporu: asset_id=%s days=%s precision=%s false_positive_rate=%s",
        asset_id,
        days,
        report.get("precision_proxy"),
        report.get("false_positive_rate"),
    )
    return report


@router.get("/confidence-stack")
def get_confidence_stack(
    asset_id: str = Query(..., min_length=1),
) -> dict[str, Any]:
    """Son pipeline run confidence stack (interval + coverage) döndürür."""
    runs = _storage.get_recent_runs(limit=20)
    latest = next((run for run in runs if run.get("asset_id") == asset_id), None)
    if not latest:
        return {
            "asset_id": asset_id,
            "version": CONFIDENCE_STACK_VERSION,
            "found": False,
        }

    stack = latest.get("confidence_stack") or {}
    return {
        "asset_id": asset_id,
        "target_date": latest.get("target_date"),
        "found": True,
        "version": stack.get("version", CONFIDENCE_STACK_VERSION),
        "base_confidence": stack.get("base_confidence"),
        "confidence_calibrated": stack.get("confidence_calibrated"),
        "prediction_interval": stack.get("prediction_interval"),
        "coverage": stack.get("coverage"),
    }


@router.get("/model-attribution")
def get_model_attribution(
    asset_id: str = Query(..., min_length=1),
) -> dict[str, Any]:
    """Son pipeline run model attribution (tree SHAP) raporunu döndürür."""
    runs = _storage.get_recent_runs(limit=20)
    latest = next((run for run in runs if run.get("asset_id") == asset_id), None)
    if not latest:
        return {"asset_id": asset_id, "version": EXPLAINABILITY_VERSION, "found": False}

    attribution = latest.get("model_attribution") or {}
    return {
        "asset_id": asset_id,
        "target_date": latest.get("target_date"),
        "found": bool(attribution),
        "version": attribution.get("version", EXPLAINABILITY_VERSION),
        "method": attribution.get("method"),
        "prediction_mw": attribution.get("prediction_mw"),
        "features": attribution.get("features", []),
    }


@router.get("/decision-causality")
def get_decision_causality(
    asset_id: str = Query(..., min_length=1),
    days: int = Query(default=7, ge=1, le=30),
) -> dict[str, Any]:
    """Recommendation sonrası causality lift raporunu döndürür."""
    report = build_causality_report(asset_id=asset_id, storage=_storage, days=days)
    _logger.info(
        "Decision causality raporu: asset_id=%s lift=%s signal=%s",
        asset_id,
        report.get("causality_lift"),
        report.get("causality_signal"),
    )
    return report


@router.get("/model-registry")
def get_model_registry(
    asset_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """Model registry kayıtlarını döndürür."""
    entries = list_registry_entries(asset_id=asset_id, limit=limit)
    return {
        "version": MODEL_REGISTRY_VERSION,
        "count": len(entries),
        "entries": entries,
    }


@router.get("/experiments/{experiment_id}")
def get_experiment_bundle(experiment_id: str) -> dict[str, Any]:
    """Experiment tracking bundle (experiment/metrics/model.json) döndürür."""
    bundle = load_experiment_bundle(experiment_id)
    if bundle is None:
        return {"experiment_id": experiment_id, "found": False}
    return {"found": True, **bundle}


@router.get("/experiments/latest/{asset_id}")
def get_latest_experiment(asset_id: str) -> dict[str, Any]:
    """Varlık için en son registry kaydını ve experiment bundle özetini döndürür."""
    entry = get_latest_registry_entry(asset_id)
    if not entry:
        return {"asset_id": asset_id, "found": False, "version": MODEL_REGISTRY_VERSION}
    bundle = load_experiment_bundle(str(entry.get("experiment_id")))
    return {
        "asset_id": asset_id,
        "found": True,
        "version": MODEL_REGISTRY_VERSION,
        "registry_entry": entry,
        "bundle": bundle,
    }
