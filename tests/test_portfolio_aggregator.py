"""Portföy aggregator testleri."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.main import app
from core.storage import PipelineStorage
from modules.ai.schemas import AIResponse
from modules.portfolio_aggregator.service import PortfolioAggregatorService
from modules.reporting.service import ReportingService


def _write_sample_history(path: Path) -> None:
    records = [
        {
            "asset_id": "RES-BAL-01",
            "total_imbalance_cost_tl": 1000.0,
            "mape_percentage": 10.0,
            "alert_status": {"severity": "CRITICAL"},
        },
        {
            "asset_id": "RES-BND-02",
            "total_imbalance_cost_tl": 500.0,
            "mape_percentage": 20.0,
            "alert_status": {"severity": "INFO"},
        },
    ]
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def test_portfolio_aggregator_metrics(tmp_path: Path) -> None:
    history_file = tmp_path / "pipeline_history.jsonl"
    _write_sample_history(history_file)
    reporting = ReportingService(storage=PipelineStorage(history_file=history_file))
    ai_assistant = MagicMock()
    ai_assistant.generate_explanation.return_value = AIResponse(
        insight="Portfoy genel durumu stabil.",
        action_plan="Standart izleme prosedürüne devam et",
    )

    service = PortfolioAggregatorService(
        reporting_service=reporting,
        ai_assistant=ai_assistant,
    )
    report = service.get_aggregated_report(
        asset_ids=["RES-BAL-01", "RES-BND-02"],
        days=30,
    )

    assert report["total_cost"] == 1500.0
    assert report["critical_alert_count"] == 1
    # weighted mape: (10*50 + 20*35) / 85 = 14.1176...
    assert round(report["avg_mape"], 2) == 14.12
    assert report["summary"] == "Portfoy genel durumu stabil."
    ai_assistant.generate_explanation.assert_called_once()


def test_portfolio_report_api(tmp_path: Path, monkeypatch, auth_headers: dict[str, str]) -> None:
    history_file = tmp_path / "pipeline_history.jsonl"
    _write_sample_history(history_file)
    monkeypatch.setattr(
        "api.routes.reporting._portfolio_service",
        PortfolioAggregatorService(
            reporting_service=ReportingService(storage=PipelineStorage(history_file=history_file)),
            ai_assistant=MagicMock(
                generate_explanation=lambda _: AIResponse(
                    insight="Portfoy ozeti",
                    action_plan="Pozisyonu gozden gecir",
                )
            ),
        ),
    )

    client = TestClient(app)
    response = client.get(
        "/api/v1/reporting/portfolio",
        params={"asset_ids": "RES-BAL-01,RES-BND-02", "days": 30},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_cost"] == 1500.0
    assert len(data["asset_ids"]) == 2


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "pipeline_history.jsonl"
        _write_sample_history(path)
        reporting = ReportingService(storage=PipelineStorage(history_file=path))
        ai = MagicMock()
        ai.generate_explanation.return_value = AIResponse(
            insight="ok",
            action_plan="izle",
        )
        report = PortfolioAggregatorService(
            reporting_service=reporting,
            ai_assistant=ai,
        ).get_aggregated_report(["RES-BAL-01", "RES-BND-02"], 30)
        assert report["critical_alert_count"] == 1
    print("ALL_PORTFOLIO_TESTS_PASSED")
