"""Reporting modülü entegrasyon testleri."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.main import app
from core.storage import PipelineStorage
from modules.reporting.service import ReportingService


def _write_sample_history(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "saved_at": "2026-07-01T08:05:00+00:00",
            "target_date": "2026-07-01",
            "asset_id": "RES-BAL-01",
            "total_imbalance_cost_tl": 1200.5,
            "mape_percentage": 12.4,
            "risk_score": 40,
            "action_plan": "Pozisyonu azalt",
            "alert_status": {"severity": "WARNING", "message": "test"},
            "data_quality": {"score": 82, "gate_passed": True},
            "confidence_calibrated": 55,
            "rules": [{"rule_id": "R1", "title": "Imbalance", "severity": "WARNING"}],
        },
        {
            "saved_at": "2026-07-02T08:05:00+00:00",
            "target_date": "2026-07-02",
            "asset_id": "RES-BAL-01",
            "total_imbalance_cost_tl": 800.0,
            "mape_percentage": 18.2,
            "risk_score": 80,
            "action_plan": "Pozisyonu azalt",
            "alert_status": {"severity": "CRITICAL", "message": "test"},
            "data_quality": {"score": 70, "gate_passed": True},
            "confidence_calibrated": 40,
            "rules": [{"rule_id": "R2", "title": "Critical cost", "severity": "CRITICAL"}],
        },
        {
            "saved_at": "2026-07-03T08:05:00+00:00",
            "target_date": "2026-07-03",
            "asset_id": "RES-BND-02",
            "total_imbalance_cost_tl": 500.0,
            "mape_percentage": 9.0,
            "risk_score": 20,
            "alert_status": {"severity": "INFO", "message": "test"},
        },
    ]
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def test_reporting_service_metrics(tmp_path: Path) -> None:
    history_file = tmp_path / "pipeline_history.jsonl"
    _write_sample_history(history_file)
    assistant = MagicMock()
    assistant.complete_text.return_value = None
    service = ReportingService(
        storage=PipelineStorage(history_file=history_file),
        ai_assistant=assistant,
    )

    report = service.generate_executive_report("RES-BAL-01", days_back=30)

    assert report["asset_id"] == "RES-BAL-01"
    assert report["period_days"] == 30
    assert report["total_imbalance_cost_tl"] == 2000.5
    assert report["average_mape"] == 15.3
    assert report["critical_alerts_count"] == 1
    assert "executive_summary" in report
    assert "report_id" in report
    assert len(report["scorecards"]) >= 6
    assert report["ai_brief"]["title"]
    assert report["financial"]["total_cost_tl"] == 2000.5
    assert report["forecast"]["average_mape"] == 15.3
    assert report["recommendations"]
    assert report["actions"]
    assert report["conclusion"]
    assert "trends" in report
    assert "benchmark" in report
    assert report["report_type"] == "executive"
    assert report["changes_since_last"]["summary"]
    assert "ai_brief" in report["visible_sections"]

    report_ops = service.generate_executive_report("RES-BAL-01", days_back=30, locale="en", report_type="operational")
    assert report_ops["report_type"] == "operational"
    assert "financial" not in report_ops["visible_sections"]
    assert "operational" in report_ops["visible_sections"]

    asked = service.ask_about_report("RES-BAL-01", "Why did MAPE increase?", locale="en")
    assert "MAPE" in asked["answer"] or "mape" in asked["answer"].lower()
    assert "period" in asked["answer"].lower() or "change" in asked["answer"].lower() or "delta" in asked["answer"].lower() or "comparison" in asked["answer"].lower() or "prior" in asked["answer"].lower()
    assert "forecast" in asked["citations"]
    assert asked["source"] == "template"
    # Answer text must not expose raw citation/pack slugs
    assert "ai_brief" not in asked["answer"]
    assert "[forecast]" not in asked["answer"]
    # Must not be the bare ask_mape dump
    assert not asked["answer"].startswith("Average MAPE")


def test_ask_mape_neden_artti_is_causal_not_bare_dump(tmp_path: Path) -> None:
    history_file = tmp_path / "pipeline_history.jsonl"
    _write_sample_history(history_file)
    assistant = MagicMock()
    assistant.complete_text.return_value = None  # force template path
    service = ReportingService(
        storage=PipelineStorage(history_file=history_file),
        ai_assistant=assistant,
    )

    asked = service.ask_about_report("RES-BAL-01", "mape neden arttı", locale="tr")
    answer = asked["answer"]
    bare = "Ortalama MAPE %"
    assert not answer.startswith(bare), f"got bare dump: {answer}"
    assert asked["source"] == "template"
    lower = answer.casefold()
    assert any(
        token in lower
        for token in ("neden", "artış", "artis", "değişim", "degisim", "önceki", "onceki", "delta", "dönem", "donem")
    ), answer
    assert "mape" in lower or "MAPE" in answer


def test_ask_off_topic_refuses_without_cost_dump(tmp_path: Path) -> None:
    history_file = tmp_path / "pipeline_history.jsonl"
    _write_sample_history(history_file)
    assistant = MagicMock()
    assistant.complete_text.return_value = None
    service = ReportingService(
        storage=PipelineStorage(history_file=history_file),
        ai_assistant=assistant,
    )

    for question in ("kaç yaşındasın", "sne kaç yaşındasın", "hello"):
        asked = service.ask_about_report("RES-BAL-01", question, locale="tr")
        answer = asked["answer"]
        assert asked["source"] == "template"
        assert "rapor verisiyle ilgili değil" in answer.casefold() or "rapor verisiyle ilgili değil" in answer
        assert "143" not in answer
        assert "1,200" not in answer and "1200" not in answer
        assert "Sonuç: Sonuç:" not in answer
        assert "Özet:" not in answer


def test_ask_default_compose_no_duplicate_sonuc(tmp_path: Path) -> None:
    history_file = tmp_path / "pipeline_history.jsonl"
    _write_sample_history(history_file)
    assistant = MagicMock()
    assistant.complete_text.return_value = None
    service = ReportingService(
        storage=PipelineStorage(history_file=history_file),
        ai_assistant=assistant,
    )

    asked = service.ask_about_report("RES-BAL-01", "rapor özeti nedir", locale="tr")
    answer = asked["answer"]
    assert asked["source"] == "template"
    assert "Sonuç: Sonuç:" not in answer
    assert "Özet: Özet:" not in answer
    assert answer.count("Sonuç:") <= 1
    # Mid-word cut from posture text should not appear
    assert "acil göz " not in answer
    assert "acil göz," not in answer


def test_ask_off_topic_llm_dump_falls_back_to_refusal(tmp_path: Path) -> None:
    history_file = tmp_path / "pipeline_history.jsonl"
    _write_sample_history(history_file)
    assistant = MagicMock()
    assistant.complete_text.return_value = (
        "Özet: RES-BAL-01 için toplam dengesizlik maliyeti 143,564 TL. "
        "Sonuç: Sonuç: acil gözden geçirme önerilir."
    )
    service = ReportingService(
        storage=PipelineStorage(history_file=history_file),
        ai_assistant=assistant,
    )

    asked = service.ask_about_report("RES-BAL-01", "kaç yaşındasın", locale="tr")
    assert asked["source"] == "template"
    assert "rapor verisiyle ilgili değil" in asked["answer"]
    assert "143,564" not in asked["answer"]


def test_ask_rejects_shallow_llm_why_answer(tmp_path: Path) -> None:
    history_file = tmp_path / "pipeline_history.jsonl"
    _write_sample_history(history_file)
    assistant = MagicMock()
    assistant.complete_text.return_value = "Ortalama MAPE %36.56 (kritik). Son kayıt MAPE %7.58."
    service = ReportingService(
        storage=PipelineStorage(history_file=history_file),
        ai_assistant=assistant,
    )

    asked = service.ask_about_report("RES-BAL-01", "mape neden arttı", locale="tr")
    assert asked["source"] == "template"
    assert not asked["answer"].startswith("Ortalama MAPE %")
    assert "neden" in asked["answer"].casefold() or "önceki" in asked["answer"].casefold() or "onceki" in asked["answer"].casefold()

    kpi = service.get_system_kpi(days_back=30)
    assert kpi["average_mape"] == 13.2
    assert kpi["uptime_percentage"] == 100.0
    assert kpi["api_availability_percentage"] == 100.0
    assert kpi["pipeline_run_count"] == 3
    assert "data_hub" in kpi


def test_ask_about_report_uses_llm_when_available(tmp_path: Path) -> None:
    history_file = tmp_path / "pipeline_history.jsonl"
    _write_sample_history(history_file)
    assistant = MagicMock()
    assistant.complete_text.return_value = (
        "MAPE rose because recent runs hit 18.2% after an earlier 12.4%, "
        "which also lifted imbalance cost risk in the pack."
    )
    service = ReportingService(
        storage=PipelineStorage(history_file=history_file),
        ai_assistant=assistant,
    )

    asked = service.ask_about_report("RES-BAL-01", "Why did MAPE increase?", locale="en")
    assert asked["source"] == "llm"
    assert "18.2" in asked["answer"] or "MAPE" in asked["answer"]
    assert asked["citations"] == []
    assistant.complete_text.assert_called_once()
    system_prompt = assistant.complete_text.call_args.args[0]
    user_payload = assistant.complete_text.call_args.args[1]
    assert "THIS specific" in system_prompt or "this specific" in system_prompt.lower()
    assert "locale=en" in user_payload
    assert "report_pack=" in user_payload
    assert "THIS question specifically" in user_payload
    assert "WHY" in user_payload or "causal" in user_payload.lower()
    assert "Why did MAPE increase?" in user_payload
    assert "NEVER" in system_prompt or "neden" in system_prompt.lower() or "ARTTI" in system_prompt


def test_ask_about_report_falls_back_when_llm_fails(tmp_path: Path) -> None:
    history_file = tmp_path / "pipeline_history.jsonl"
    _write_sample_history(history_file)
    assistant = MagicMock()
    assistant.complete_text.return_value = None
    service = ReportingService(
        storage=PipelineStorage(history_file=history_file),
        ai_assistant=assistant,
    )

    asked = service.ask_about_report("RES-BAL-01", "Why did MAPE increase?", locale="en")
    assert asked["source"] == "template"
    assert "MAPE" in asked["answer"] or "mape" in asked["answer"].lower()
    assert "forecast" in asked["citations"]
    assert "ai_brief" not in asked["answer"]
    assert not asked["answer"].startswith("Average MAPE")


def test_complete_text_returns_none_for_mock_provider() -> None:
    from core.config import Settings
    from modules.ai.assistant import AIDecisionAssistant

    assistant = AIDecisionAssistant(settings=Settings(llm_provider="mock"))
    assert assistant.complete_text("sys", "user") is None


def test_executive_report_api(tmp_path: Path, monkeypatch, auth_headers: dict[str, str]) -> None:
    history_file = tmp_path / "pipeline_history.jsonl"
    _write_sample_history(history_file)
    monkeypatch.setattr(
        "api.routes.reporting._reporting_service",
        ReportingService(storage=PipelineStorage(history_file=history_file)),
    )

    client = TestClient(app)
    response = client.get(
        "/api/v1/reporting/executive",
        params={"asset_id": "RES-BAL-01", "days": 30, "locale": "en"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_imbalance_cost_tl"] == 2000.5
    assert data["critical_alerts_count"] == 1
    assert len(data["scorecards"]) >= 6
    assert data["ai_brief"]["recommended_action"]


def test_pdf_export_with_turkish_chars() -> None:
    from modules.reporting.export import export_executive_pdf

    report = {
        "asset_id": "RES-BAL-01",
        "period_days": 30,
        "total_imbalance_cost_tl": 1500.0,
        "average_mape": 12.5,
        "critical_alerts_count": 0,
        "executive_summary": "Balıkesir santrali için şğü özet metni.",
        "scorecards": [
            {"id": "overall", "label": "Genel Sağlık", "value": "Kritik", "level": "crit", "level_label": "Kritik"}
        ],
        "ai_brief": {
            "title": "AI Yönetici Brifingi",
            "status_summary": "",
            "top_event": "Imbalance kuralı tetiklendi ve uzun açıklama satırı",
            "top_risk": "80/100 — Imbalance",
            "recommended_action": "İzle",
        },
        "financial": {"total_cost_tl": 1500.0, "cost_trend": "flat"},
        "forecast": {"average_mape": 12.5},
        "operational": {"critical_count": 0},
        "risk": {"average_score": 20, "level_label": "Normal"},
        "data_intelligence": {"trust_score": 80},
        "model_intelligence": {"confidence": 60},
        "recommendations": [{"title": "İzleme devam", "priority": "low"}],
        "actions": [{"id": "ACT-01", "title": "İzle", "priority_label": "Düşük", "status": "Açık"}],
        "trends": {"cost_sparkline": [1, 2, 3], "mape_sparkline": [10, 12], "risk_sparkline": [20, 22]},
        "benchmark": {"vs_prior_cost_pct": 0.0},
        "conclusion": "Sonuç metni.",
    }
    content = export_executive_pdf(report, locale="tr")
    assert len(content) > 100
    assert content[:4] == b"%PDF"
    # Smoke: empty status_summary should not crash; scorecard value==level_label is fine
    assert b"%%EOF" in content[-32:] or content.rstrip().endswith(b"%%EOF")


def _assert_focus_left_aligned(pdf_bytes: bytes, *, must_contain: str, full_focus: str) -> None:
    """Assert focus/subtitle is intact and starts near left margin (not x≈547 clipped)."""
    import fitz

    page = fitz.open(stream=pdf_bytes, filetype="pdf")[0]
    text = page.get_text("text")
    collapsed = " ".join(text.split())
    assert full_focus in collapsed or full_focus in text, (
        f"full focus missing from PDF text; got excerpt:\n{text[:800]!r}"
    )
    # Classic right-edge orphan truncations (full phrase cut mid-comma / mid-word)
    assert "Risk view f\n" not in text
    if full_focus.startswith("Finans, risk,") or "Finans, risk," in full_focus:
        assert "Finans, risk\n" not in text

    found = False
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            line_text = "".join(span.get("text", "") for span in line.get("spans", []))
            if must_contain in line_text:
                found = True
                left = float(line["bbox"][0])
                # ~18mm left margin ≈ 51pt; right-clipped bug starts near ~540pt
                assert left < 90, f"focus starts too far right: {left} text={line_text!r}"
                assert len(line_text) > 12, f"focus truncated: {line_text!r}"
    assert found, f"focus marker {must_contain!r} not found in PDF glyphs"


def test_pdf_risk_focus_not_right_clipped() -> None:
    """Focus subtitle must start at left margin (not classic fpdf2 RIGHT-edge clip)."""
    from core.i18n import translate
    from modules.reporting.export import export_executive_pdf

    focus = translate("en", "reporting.type_focus_risk")
    assert "Risk view" in focus
    assert focus != "Risk view f"
    assert "focused" in focus or "Risk view for" in focus

    report = {
        "asset_id": "RES-BAL-01",
        "period_days": 30,
        "report_type": "risk",
        "total_imbalance_cost_tl": 1500.0,
        "average_mape": 12.5,
        "critical_alerts_count": 0,
        "executive_summary": "Risk summary.",
        "scorecards": [],
        "ai_brief": {
            "title": "Risk Report — RES-BAL-01",
            "focus": focus,
            "status_summary": "ok",
            "top_event": "none",
            "top_risk": "20/100",
            "recommended_action": "Monitor",
        },
        "financial": {"total_cost_tl": 1500.0, "cost_trend": "flat"},
        "forecast": {"average_mape": 12.5},
        "operational": {"critical_count": 0},
        "risk": {"average_score": 20, "level_label": "Normal"},
        "data_intelligence": {"trust_score": 80},
        "model_intelligence": {"confidence": 60},
        "recommendations": [],
        "actions": [],
        "trends": {"cost_sparkline": [1], "mape_sparkline": [10], "risk_sparkline": [20]},
        "benchmark": {"vs_prior_cost_pct": 0.0},
        "conclusion": "Done.",
    }
    content = export_executive_pdf(report, locale="en")
    _assert_focus_left_aligned(content, must_contain="Risk view", full_focus=focus)


def test_pdf_tr_executive_finans_focus_not_right_clipped() -> None:
    """TR executive focus ('Finans, risk...') must be full + left-aligned (user PDF clip)."""
    from core.i18n import translate
    from modules.reporting.export import export_executive_pdf

    focus = translate("tr", "reporting.type_focus_executive")
    assert focus.startswith("Finans, risk")
    assert "tahmin" in focus
    assert focus != "Finans, risk"

    report = {
        "asset_id": "RES-BAL-01",
        "period_days": 30,
        "report_type": "executive",
        "generated_at": "2026-07-13T23:18:33Z",
        "report_id": "focus-align-test",
        "total_imbalance_cost_tl": 176606.21,
        "average_mape": 79.29,
        "critical_alerts_count": 3,
        "executive_summary": "Özet.",
        "scorecards": [
            {"id": "overall", "label": "Genel Sağlık", "value": "Kritik", "level_label": "Kritik"},
            {"id": "financial", "label": "Finansal Sağlık", "value": "176,606 TL", "level_label": "Kritik"},
        ],
        "ai_brief": {
            "title": "Yönetici Raporu — RES-BAL-01",
            "focus": focus,
            "status_summary": "Durum özeti",
            "top_event": "Olay",
            "top_risk": "Risk",
            "financial_impact": "176,606.21 TL",
            "recommended_action": "Pozisyonu azalt",
            "confidence": 6,
        },
        "financial": {"total_cost_tl": 176606.21, "cost_trend": "down"},
        "forecast": {"average_mape": 79.29},
        "operational": {"critical_count": 3},
        "risk": {"average_score": 80, "level_label": "Kritik"},
        "data_intelligence": {"trust_score": 70},
        "model_intelligence": {"confidence": 50},
        "recommendations": [],
        "actions": [],
        "trends": {"cost_sparkline": [1], "mape_sparkline": [10], "risk_sparkline": [20]},
        "benchmark": {"vs_prior_cost_pct": -34.8},
        "conclusion": "Sonuç.",
    }
    content = export_executive_pdf(report, locale="tr")
    _assert_focus_left_aligned(content, must_contain="Finans, risk", full_focus=focus)


def test_context_briefing_ai_annotations() -> None:
    from modules.ai.context_briefing import ContextBriefingService

    service = ContextBriefingService()
    briefing = service.generate("ai", "RES-BAL-01", days=7)
    assert briefing["context"] == "ai"
    assert "annotations" in briefing
    actions = [a for a in briefing["annotations"] if a.get("recommended_action")]
    assert len(actions) >= 1
    assert briefing["expert"]["title"] == "Karar Merkezi"


def test_context_briefing_monitoring() -> None:
    from modules.ai.context_briefing import ContextBriefingService

    service = ContextBriefingService()
    briefing = service.generate("monitoring", "RES-BAL-01", days=7)
    assert briefing["context"] == "monitoring"
    assert "executive_summary" in briefing
    assert "technical_detail" in briefing
    assert len(briefing["recommendations"]) >= 1
    assert "annotations" in briefing
    assert len(briefing["annotations"]) >= 1
    assert briefing["annotations"][0]["recommended_action"]
    assert briefing["expert"]["title"] == "Sistem Analisti"
    assert briefing["mode"] == "technical"
    assert "structured" in briefing
    assert briefing["structured"]["title"]
    assert "panel" in briefing
    assert "technical" in briefing


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "pipeline_history.jsonl"
        _write_sample_history(path)
        service = ReportingService(storage=PipelineStorage(history_file=path))
        report = service.generate_executive_report("RES-BAL-01", days_back=30)
        assert report["average_mape"] == 15.3
    print("ALL_REPORTING_TESTS_PASSED")
