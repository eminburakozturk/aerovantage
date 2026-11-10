"""FAZ 5 — observability endpoint ve pipeline metrics testleri."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from core.pipeline import EventPipeline
from modules.monitoring.observability import (
    OBSERVABILITY_VERSION,
    aggregate_coverage_metrics,
    aggregate_pipeline_latency,
    build_observability_summary,
    build_pipeline_observability_snapshot,
    compute_pipeline_success_rate,
    compute_source_success_rates,
)


def test_compute_source_success_rates() -> None:
    rates = compute_source_success_rates(
        {
            "weather": {"live": 3, "mock": 1},
            "scada": {"live": 0, "mock": 4},
            "epias": {"live": 2, "mock": 2},
        }
    )
    assert rates["weather"] == 0.75
    assert rates["scada"] == 0.0
    assert rates["epias"] == 0.5


def test_compute_pipeline_success_rate_from_audit() -> None:
    audit = [
        {"asset_id": "A1", "target_date": "2026-07-01", "step": "0800_forecast", "status": "completed"},
        {"asset_id": "A1", "target_date": "2026-07-01", "step": "0801_performance_monitoring", "status": "completed"},
        {"asset_id": "A1", "target_date": "2026-07-01", "step": "0802_risk_calculation", "status": "completed"},
        {"asset_id": "A1", "target_date": "2026-07-01", "step": "0803_alert_generation", "status": "completed"},
        {"asset_id": "A1", "target_date": "2026-07-01", "step": "0804_ai_explanation", "status": "completed"},
        {"asset_id": "A1", "target_date": "2026-07-01", "step": "0805_dashboard_update", "status": "completed"},
        {"asset_id": "A2", "target_date": "2026-07-02", "step": "0800_forecast", "status": "completed"},
    ]
    result = compute_pipeline_success_rate(audit)
    assert result["pipeline_runs"] == 2
    assert result["successful_runs"] == 1
    assert result["success_rate"] == 0.5


def test_aggregate_coverage_and_latency() -> None:
    metrics = [
        {
            "confidence_stack": {"coverage": {"coverage_rate": 0.9, "meets_target": True}},
            "observability": {
                "pipeline_total_ms": 100.0,
                "step_timings_ms": {"0800_forecast": 20.0, "pipeline_total_ms": 100.0},
            },
        },
        {
            "confidence_stack": {"coverage": {"coverage_rate": 0.8, "meets_target": False}},
            "observability": {
                "pipeline_total_ms": 200.0,
                "step_timings_ms": {"0800_forecast": 40.0, "pipeline_total_ms": 200.0},
            },
        },
    ]
    coverage = aggregate_coverage_metrics(metrics)
    latency = aggregate_pipeline_latency(metrics)

    assert coverage["sample_size"] == 2
    assert coverage["avg_coverage_rate"] == 0.85
    assert coverage["meets_target_runs"] == 1
    assert latency["sample_size"] == 2
    assert latency["avg_pipeline_total_ms"] == 150.0
    assert latency["avg_step_timings_ms"]["0800_forecast"] == 30.0


def test_build_pipeline_observability_snapshot() -> None:
    snapshot = build_pipeline_observability_snapshot(
        step_timings_ms={"0800_forecast": 12.5, "pipeline_total_ms": 99.0},
        telemetry={
            "is_degraded": True,
            "degraded_sources": ["epias"],
            "sources": {
                "weather": {"mode": "live", "reason": "ok"},
                "scada": {"mode": "mock", "reason": "timeout"},
                "epias": {"mode": "mock", "reason": "auth_failed"},
            },
        },
        confidence_stack={"coverage": {"coverage_rate": 0.92, "meets_target": True}},
        gates_passed={"data_quality": True, "model_reliability": True, "decision_reliability": True},
    )
    assert snapshot["version"] == OBSERVABILITY_VERSION
    assert snapshot["fallback_reasons"]["scada"] == "timeout"
    assert snapshot["coverage_rate"] == 0.92
    assert snapshot["api_success"] is True


def test_build_observability_summary_merges_sections() -> None:
    summary = build_observability_summary(
        metrics=[{"confidence_stack": {"coverage": {"coverage_rate": 0.9, "meets_target": True}}}],
        audit_entries=[],
        degraded_summary={
            "degraded_ratio_pct": 10.0,
            "avg_mock_usage_rate": 0.25,
            "source_mode_counts": {"weather": {"live": 1, "mock": 0}},
            "degraded_reason_counts": {"timeout": 1},
        },
    )
    assert summary["version"] == OBSERVABILITY_VERSION
    assert summary["fallback_reasons"]["timeout"] == 1
    assert "api_success" in summary
    assert "latency" in summary
    assert summary["endpoints"]["observability_summary"] is True


def test_pipeline_includes_observability_metadata() -> None:
    pipeline = EventPipeline()
    result = pipeline.execute_daily_pipeline("RES-BAL-01")
    observability = result.metadata.get("observability", {})
    assert observability.get("version") == OBSERVABILITY_VERSION
    assert "step_timings_ms" in observability
    assert observability.get("pipeline_total_ms", 0) >= 0
    assert "source_success_rates" in observability
    assert "gates_passed" in observability


def _trigger_pipeline(client: TestClient, headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/pipeline/trigger-pipeline",
        json={"asset_id": "RES-BAL-01", "target_date": "2026-07-06"},
        headers=headers,
    )
    assert response.status_code == 200, response.text


def test_monitoring_observability_summary_endpoint(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    _trigger_pipeline(client, auth_headers)

    response = client.get("/api/v1/monitoring/observability-summary?limit=20", headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["version"] == OBSERVABILITY_VERSION
    assert "source_success_rates" in data
    assert "api_success" in data
    assert "latency" in data
    assert "coverage" in data
    assert data["endpoints"]["degraded_summary"] is True


def test_monitoring_endpoints_exist(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    _trigger_pipeline(client, auth_headers)
    asset_id = "RES-BAL-01"

    endpoints = [
        ("/api/v1/monitoring/degraded-summary?limit=10", {"version", "source_mode_counts"}),
        ("/api/v1/monitoring/drift-summary?limit=10", {"version", "sample_size"}),
        (
            f"/api/v1/monitoring/recommendation-quality?asset_id={asset_id}&days=7",
            {"asset_id", "quality_score"},
        ),
        (
            f"/api/v1/monitoring/alert-quality?asset_id={asset_id}&days=7",
            {"asset_id", "precision_proxy"},
        ),
        (f"/api/v1/monitoring/confidence-stack?asset_id={asset_id}", {"asset_id", "version"}),
        (f"/api/v1/monitoring/model-attribution?asset_id={asset_id}", {"asset_id", "version"}),
        (
            f"/api/v1/monitoring/decision-causality?asset_id={asset_id}&days=7",
            {"asset_id", "causality_signal"},
        ),
        ("/api/v1/monitoring/model-registry?limit=10", {"version", "entries"}),
    ]
    for path, required_keys in endpoints:
        response = client.get(path, headers=auth_headers)
        assert response.status_code == 200, f"{path}: {response.text}"
        data = response.json()
        for key in required_keys:
            assert key in data, f"{path} missing {key}"

    latest = client.get(
        f"/api/v1/monitoring/experiments/latest/{asset_id}",
        headers=auth_headers,
    )
    assert latest.status_code == 200, latest.text
    assert "found" in latest.json()
