"""FAZ 7 — i18n locale ve API dil desteği testleri."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from core.i18n import (
    build_executive_summary,
    build_localized_briefing_structured,
    export_labels,
    get_expert,
    get_recommendations,
    normalize_locale,
    translate,
)
from modules.reporting.export import export_executive_pdf


def test_normalize_locale_defaults_to_tr() -> None:
    assert normalize_locale(None) == "tr"
    assert normalize_locale("en-US") == "en"
    assert normalize_locale("fr") == "tr"


def test_get_expert_english() -> None:
    expert = get_expert("en", "forecast")
    assert expert["title"] == "Forecast Analyst"
    assert "subtitle" in expert


def test_build_executive_summary_english() -> None:
    summary = build_executive_summary(
        "en",
        asset_id="RES-BAL-01",
        period_days=30,
        run_count=5,
        total_imbalance_cost_tl=12000.0,
        average_mape=11.5,
        critical_alerts_count=0,
    )
    assert "RES-BAL-01" in summary
    assert "5 records" in summary


def test_build_localized_briefing_structured_german() -> None:
    structured = build_localized_briefing_structured(
        "de",
        "risk",
        "Test Plant",
        60,
        14.0,
        40000.0,
        72,
        "Monitor position",
        "No critical rule",
        {"steps_completed": ["0800_forecast", "0801_performance_monitoring"]},
    )
    assert structured["title"].startswith("Test Plant")
    assert structured["confidence"] == 72


def test_export_labels_and_pdf_locale() -> None:
    report = {
        "asset_id": "RES-BAL-01",
        "period_days": 30,
        "total_imbalance_cost_tl": 1000.0,
        "average_mape": 10.0,
        "critical_alerts_count": 0,
        "generated_at": "2026-07-12T09:00:00Z",
        "report_id": "00000000-0000-0000-0000-000000000001",
        "executive_summary": build_executive_summary(
            "en",
            asset_id="RES-BAL-01",
            period_days=30,
            run_count=1,
            total_imbalance_cost_tl=1000.0,
            average_mape=10.0,
            critical_alerts_count=0,
        ),
    }
    labels = export_labels("en")
    assert "Executive" in labels["pdf_title"]
    assert labels["section_kpis"]
    assert labels["confidential"]
    pdf_en = export_executive_pdf(report, locale="en")
    assert pdf_en.startswith(b"%PDF")
    assert len(pdf_en) > 2_000

    report_tr = {
        **report,
        "executive_summary": build_executive_summary(
            "tr",
            asset_id="RES-BAL-01",
            period_days=30,
            run_count=1,
            total_imbalance_cost_tl=1000.0,
            average_mape=10.0,
            critical_alerts_count=0,
        ),
    }
    labels_tr = export_labels("tr")
    assert "Yönetici" in labels_tr["pdf_doc_type"]
    pdf_tr = export_executive_pdf(report_tr, locale="tr")
    assert pdf_tr.startswith(b"%PDF")
    assert len(pdf_tr) > 2_000


def test_ai_briefing_locale_query_param(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    en = client.get(
        "/api/v1/ai/briefing?context=dashboard&asset_id=RES-BAL-01&days=7&locale=en",
        headers=auth_headers,
    )
    assert en.status_code == 200, en.text
    en_data = en.json()
    assert en_data.get("locale") == "en"
    assert en_data["expert"]["title"] == "Executive Assistant"

    de = client.get(
        "/api/v1/ai/briefing?context=forecast&asset_id=RES-BAL-01&days=7&locale=de",
        headers=auth_headers,
    )
    assert de.status_code == 200, de.text
    assert de.json()["expert"]["title"] == "Prognose-Analyst"


def test_ai_briefing_annotations_localized(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    en = client.get(
        "/api/v1/ai/briefing?context=ai&asset_id=RES-BAL-01&days=7&locale=en",
        headers=auth_headers,
    )
    assert en.status_code == 200, en.text
    data = en.json()
    assert data.get("locale") == "en"
    annotations = data.get("annotations") or []
    assert annotations, "expected annotations"
    blob = " ".join(
        f"{a.get('label','')} {a.get('insight','')} {a.get('recommended_action','')}"
        for a in annotations
    )
    assert "tavsiyesi" not in blob.lower()
    assert "Dengesizlik maliyeti" not in blob
    assert "Kural uyarısı" not in blob
    assert any(
        "recommendation" in str(a.get("label", "")).lower()
        or "action" in str(a.get("label", "")).lower()
        or "risk" in str(a.get("label", "")).lower()
        or "alert" in str(a.get("label", "")).lower()
        or "accuracy" in str(a.get("label", "")).lower()
        for a in annotations
    )


def test_build_annotations_unit_english() -> None:
    from modules.ai.context_briefing import ContextBriefingService

    svc = ContextBriefingService()
    structured = build_localized_briefing_structured(
        "en",
        "ai",
        "Test Plant",
        60,
        16.0,
        60000.0,
        70,
        "Reduce position",
        "Elevated risk",
        {"steps_completed": ["a", "b"]},
    )
    rules = [
        {
            "rule_id": "elevated_risk",
            "severity": "WARNING",
            "message": "Risk score is elevated.",
            "action": "Monitor hourly production deviation",
        }
    ]
    anns = svc._build_annotations(
        "ai",
        structured,
        rules,
        get_recommendations("en", "ai"),
        60,
        16.0,
        60000.0,
        70,
        {"forecast_mw": 40, "actual_mw": 48},
        "en",
    )
    labels = " ".join(a["label"] for a in anns)
    assert "Rule alert" in labels
    assert "AI recommendation" in labels or "Risk score" in labels
    assert "Kural" not in labels
    assert "tavsiye" not in labels.lower()


def test_localize_action_plan_english() -> None:
    from core.i18n import localize_action_plan

    action = localize_action_plan(
        "en",
        {"risk_score": 10, "total_imbalance_cost_tl": 100, "forecast_mw": 20, "wind_speed_mps": 6},
    )
    assert "monitoring" in action.lower() or "Continue" in action


def test_scenario_summary_and_monitoring_locale() -> None:
    from core.i18n import build_scenario_summary, localize_ai_insight, translate

    summary = build_scenario_summary(
        "en",
        name="Balıkesir RES",
        wind_adjustment_pct=0,
        ptf_adjustment_pct=-17,
        turbines_down=0,
        baseline_forecast_mw=440.1,
        adjusted_forecast_mw=440.1,
        baseline_cost_tl=38355,
        adjusted_cost_tl=32685,
        baseline_risk_score=100,
        adjusted_risk_score=100,
    )
    assert "Scenario for" in summary
    assert "senaryo" not in summary.lower()
    assert translate("en", "monitoring.daily_pipeline") == "Daily Pipeline"
    assert "Log file" in translate("en", "monitoring.log_empty")
    insight = localize_ai_insight(
        "en",
        {"risk_score": 80, "total_imbalance_cost_tl": 5000, "forecast_mw": 40, "wind_speed_mps": 16},
        "Sistem uyarısı: AI servisine ulaşılamadı, otomatik playbook devrede. AI Analizi: [x] y",
    )
    assert insight.startswith("System notice:")
    assert "AI Analizi" not in insight


def test_get_recommendations_localized() -> None:
    recs = get_recommendations("en", "monitoring")
    assert any("API" in item for item in recs)
    assert translate("de", "briefing.default_action")
    ai_recs = get_recommendations("en", "ai")
    assert any("Approve" in item or "pending" in item.lower() for item in ai_recs)


def test_compose_alert_and_notifications_english() -> None:
    from core.i18n import build_localized_notifications, compose_alert_message, localize_pipeline_run

    severity, message = compose_alert_message(
        "en",
        risk_score=100,
        mape_percentage=100.0,
        proxy=True,
    )
    assert severity == "WARNING"
    assert message.startswith("[Simulation]")
    assert "Critical imbalance risk" in message
    assert "Simulation MAPE 100.0%" in message
    assert "Simülasyon" not in message
    assert "Operasyonel" not in message

    notes = build_localized_notifications(
        "en",
        alert_status={"severity": severity, "message": message},
        action_plan="Reduce position",
        risk_score=100,
    )
    titles = [n["title"] for n in notes]
    assert "Operational Alert" in titles
    assert "Recommended Action" in titles
    assert "Operasyonel Uyarı" not in titles
    assert "Önerilen Aksiyon" not in titles

    de_severity, de_message = compose_alert_message(
        "de",
        risk_score=100,
        mape_percentage=100.0,
        proxy=True,
    )
    assert de_message.startswith("[Simulation]")
    assert "Kritisches Ungleichgewichtsrisiko" in de_message
    assert "Simülasyon" not in de_message

    localized = localize_pipeline_run(
        "en",
        {
            "risk_score": 100,
            "mape_percentage": 100.0,
            "evaluation_mode": "simulation",
            "mape_informational": True,
            "scada_source": {"mode": "simulated", "live": "false"},
            "action_plan": "Pozisyonu azalt",
            "total_imbalance_cost_tl": 50000,
            "total_daily_mw": 40,
            "alert_status": {
                "severity": "WARNING",
                "message": "[Simülasyon] Kritik dengesizlik riski!",
            },
            "notifications": [
                {
                    "level": "WARNING",
                    "title": "Operasyonel Uyarı",
                    "message": "[Simülasyon] Kritik dengesizlik riski!",
                },
                {
                    "level": "CRITICAL",
                    "title": "Önerilen Aksiyon",
                    "message": "Pozisyonu azalt",
                },
            ],
        },
    )
    assert localized["alert_status"]["message"].startswith("[Simulation]")
    assert "Simülasyon" not in localized["alert_status"]["message"]
    assert localized["action_plan"] == "Reduce position"
    assert localized["notifications"][0]["title"] == "Operational Alert"
    assert localized["notifications"][1]["title"] == "Recommended Action"
    assert localized["notifications"][1]["message"] == "Reduce position"


def test_pipeline_history_locale_en_notifications(auth_headers: dict[str, str]) -> None:
    """Topbar bell uses fetchLiveDashboard → GET /pipeline/history?locale=…"""
    from core.storage import PipelineStorage

    client = TestClient(app)
    storage = PipelineStorage()
    if not storage.get_recent_runs(limit=1):
        # Seed a TR-stored run so localize-on-read is exercised
        storage.save_run(
            {
                "asset_id": "RES-BAL-01",
                "asset_name": "Test",
                "risk_score": 100,
                "mape_percentage": 100.0,
                "evaluation_mode": "simulation",
                "mape_informational": True,
                "scada_source": {"mode": "simulated", "live": "false"},
                "action_plan": "Pozisyonu azalt",
                "total_imbalance_cost_tl": 50000,
                "total_daily_mw": 40,
                "alert_status": {
                    "severity": "WARNING",
                    "message": "[Simülasyon] Kritik dengesizlik riski!",
                },
                "notifications": [
                    {
                        "level": "WARNING",
                        "title": "Operasyonel Uyarı",
                        "message": "[Simülasyon] Kritik dengesizlik riski!",
                    },
                    {
                        "level": "CRITICAL",
                        "title": "Önerilen Aksiyon",
                        "message": "Pozisyonu azalt",
                    },
                ],
            }
        )

    en = client.get(
        "/api/v1/pipeline/history?limit=5&locale=en",
        headers=auth_headers,
    )
    assert en.status_code == 200, en.text
    runs = en.json()
    assert runs, "pipeline history empty"
    notes = runs[0].get("notifications") or []
    assert notes, "notifications missing"
    titles = [n.get("title", "") for n in notes]
    messages = " ".join(n.get("message", "") for n in notes)
    assert "Operational Alert" in titles or "Recommended Action" in titles
    assert "Operasyonel Uyarı" not in titles
    assert "Önerilen Aksiyon" not in titles
    assert "Simülasyon" not in messages
    assert "Pozisyonu azalt" not in messages

    de = client.get(
        "/api/v1/pipeline/history?limit=1&locale=de",
        headers=auth_headers,
    )
    assert de.status_code == 200, de.text
    de_notes = (de.json()[0].get("notifications") or []) if de.json() else []
    de_titles = [n.get("title", "") for n in de_notes]
    assert "Operasyonel Uyarı" not in de_titles
    assert "Önerilen Aksiyon" not in de_titles
