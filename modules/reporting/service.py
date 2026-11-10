"""Raporlama ve uyum servisi — R1 Executive Intelligence Pack."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from core.i18n import (
    build_executive_conclusion,
    build_executive_summary as build_localized_executive_summary,
    get_recommendations,
    localize_action_plan,
    localize_rule,
    mape_label as i18n_mape_label,
    normalize_locale,
    playbook_insight,
    reporting_level_label,
    risk_label,
    select_playbook_id,
    translate,
)
from core.logger import get_logger
from core.storage import PipelineStorage
from modules.ai.assistant import AIDecisionAssistant
from modules.reporting.schemas import ExecutiveReportResponse

REPORT_TYPES = (
    "executive",
    "operational",
    "forecast",
    "financial",
    "risk",
    "technical",
)

_ASK_PACK_KEYS = (
    "asset_id",
    "period_days",
    "report_type",
    "executive_summary",
    "scorecards",
    "financial",
    "forecast",
    "risk",
    "changes_since_last",
    "conclusion",
    "ai_brief",
    "total_imbalance_cost_tl",
    "average_mape",
    "critical_alerts_count",
)
_ASK_PACK_MAX_CHARS = 8_000
_ASK_ANSWER_MAX_TOKENS = 512

_ASK_SYSTEM_PROMPT = (
    "You are AeroVantage's report analyst. Your job is to answer THIS specific user question, "
    "not to give a generic report overview. "
    "Use ONLY the provided report_pack. Do not invent numbers, trends, or events. "
    "Ground every claim in concrete figures from the pack (MAPE, cost, risk, deltas, alerts, scores). "
    "WHY / NEDEN / WARUM / ARTTI / INCREASE questions: lead with causes and drivers from "
    "changes_since_last (mape_delta, cost_delta_pct, risk_delta, kpi_up/kpi_down), risk.top_rule, "
    "ai_brief, and simulation flags. Compare prior vs recent period when deltas exist. "
    "Numbers support the explanation — NEVER answer a why-question with only "
    "'Average/Ortalama MAPE %X. Latest/Son kayıt %Y.' "
    "OFF-TOPIC / chitchat (age, hello, weather, unrelated): politely refuse in the locale language. "
    "Do NOT dump executive_summary, conclusion, costs, or KPIs for off-topic questions. "
    "If the pack lacks enough detail to answer the question, say so clearly and state what is available. "
    "Never paste internal field names, citation slugs, or JSON keys (no 'forecast', 'ai_brief', etc.). "
    "No boilerplate openings. Keep answers concise (2–6 sentences). "
    "Write entirely in the locale language given in the user message (Turkish when locale=tr)."
)

_REPORT_TOPIC_MARKERS = (
    "mape",
    "tahmin",
    "forecast",
    "rmse",
    "mae",
    "prognose",
    "cost",
    "maliyet",
    "imbalance",
    "dengesizlik",
    "kosten",
    "risk",
    "risko",
    "alarm",
    "uyarı",
    "uyari",
    "warn",
    "aksiyon",
    "action",
    "öner",
    "oner",
    "recommend",
    "ne yap",
    "what should",
    "özet",
    "ozet",
    "summary",
    "zusammenfassung",
    "durum",
    "status",
    "sonuç",
    "sonuc",
    "conclusion",
    "fazit",
    "rapor",
    "report",
    "bericht",
    "kpi",
    "skor",
    "score",
    "sağlık",
    "saglik",
    "health",
    "veri",
    "data",
    "model",
    "güven",
    "guven",
    "confidence",
    "dq",
    "kural",
    "rule",
    "alert",
    "trend",
    "değişim",
    "degisim",
    "change",
    "brifing",
    "briefing",
    "finans",
    "financial",
    "operasyon",
    "operational",
    "kaçınılabilir",
    "kacinilabilir",
    "avoidable",
    "santral",
    "plant",
    "asset",
    "why",
    "neden",
    "niçin",
    "nicin",
    "niye",
    "warum",
    "weshalb",
    "how come",
    "sebebi",
    "nedeni",
)

_ASK_FIELD_LABEL_PREFIXES = (
    "özet:",
    "sonuç:",
    "summary:",
    "conclusion:",
    "zusammenfassung:",
    "fazit:",
)

_WHY_MARKERS = (
    "why",
    "neden",
    "niçin",
    "nicin",
    "niye",
    "warum",
    "weshalb",
    "how come",
    "sebebi",
    "nedeni",
    "arttı",
    "artti",
    "artış",
    "artis",
    "artiyor",
    "artıyor",
    "increase",
    "increased",
    "rose",
    "rising",
    "düştü",
    "dustu",
    "düşüş",
    "dusus",
    "decrease",
    "decreased",
    "fell",
    "değişim",
    "degisim",
    "changed",
    "change",
)

_BARE_DUMP_MARKERS = (
    "ortalama mape",
    "average mape",
    "durchschnittliche mape",
)
_BARE_DUMP_LATEST = ("son kayıt mape", "son kayit mape", "latest mape", "letzte mape")
_CAUSAL_ANSWER_MARKERS = (
    "neden",
    "artış",
    "artis",
    "değişim",
    "degisim",
    "önceki",
    "onceki",
    "delta",
    "dönem",
    "donem",
    "because",
    "increase",
    "prior",
    "change",
    "driver",
    "warum",
    "vergleich",
    "anstieg",
)

REPORT_TYPE_SECTIONS: dict[str, list[str]] = {
    "executive": [
        "summary",
        "ai_brief",
        "scorecards",
        "financial",
        "forecast",
        "operational",
        "risk",
        "data",
        "model",
        "recommendations",
        "actions",
        "trends",
        "benchmark",
        "changes",
        "conclusion",
        "chat",
        "whatif",
    ],
    "operational": [
        "summary",
        "ai_brief",
        "scorecards",
        "operational",
        "risk",
        "actions",
        "recommendations",
        "changes",
        "conclusion",
        "chat",
    ],
    "forecast": [
        "summary",
        "ai_brief",
        "scorecards",
        "forecast",
        "model",
        "trends",
        "recommendations",
        "changes",
        "conclusion",
        "chat",
        "whatif",
    ],
    "financial": [
        "summary",
        "ai_brief",
        "scorecards",
        "financial",
        "benchmark",
        "trends",
        "recommendations",
        "changes",
        "conclusion",
        "chat",
        "whatif",
    ],
    "risk": [
        "summary",
        "ai_brief",
        "scorecards",
        "risk",
        "operational",
        "recommendations",
        "actions",
        "changes",
        "conclusion",
        "chat",
    ],
    "technical": [
        "summary",
        "scorecards",
        "data",
        "model",
        "forecast",
        "trends",
        "changes",
        "conclusion",
        "chat",
    ],
}

WORKSPACE_DEFAULT_REPORT: dict[str, str] = {
    "dashboard": "executive",
    "reports": "executive",
    "operations": "operational",
    "monitoring": "operational",
    "assets": "operational",
    "forecast": "forecast",
    "market": "financial",
    "risk": "risk",
    "ai": "technical",
    "scenarios": "forecast",
    "settings": "technical",
}


def normalize_report_type(value: str | None) -> str:
    raw = (value or "executive").strip().lower()
    return raw if raw in REPORT_TYPES else "executive"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _level_from_thresholds(value: float, *, warn: float, crit: float, higher_is_worse: bool = True) -> str:
    if higher_is_worse:
        if value >= crit:
            return "crit"
        if value >= warn:
            return "warn"
        return "ok"
    if value <= crit:
        return "crit"
    if value <= warn:
        return "warn"
    return "ok"


class ReportingService:
    """Pipeline geçmişinden yönetici ve uyum raporları üretir."""

    def __init__(
        self,
        storage: Optional[PipelineStorage] = None,
        ai_assistant: Optional[AIDecisionAssistant] = None,
    ) -> None:
        self._storage = storage or PipelineStorage()
        self._ai_assistant = ai_assistant or AIDecisionAssistant()
        self._logger = get_logger("modules.reporting")

    def generate_executive_report(
        self,
        asset_id: str,
        days_back: int = 30,
        locale: str = "tr",
        report_type: str = "executive",
        workspace: str | None = None,
    ) -> dict[str, Any]:
        """Belirtilen santral için son N günlük yönetici Intelligence Pack üretir."""
        locale = normalize_locale(locale)
        report_type = normalize_report_type(report_type)

        asset_runs = self._storage.get_recent_runs(limit=days_back, asset_id=asset_id, dedupe=True)
        latest = asset_runs[0] if asset_runs else {}

        total_imbalance_cost_tl = 0.0
        mape_values: list[float] = []
        risk_values: list[float] = []
        critical_alerts_count = 0
        warning_alerts_count = 0
        dq_scores: list[float] = []
        confidence_values: list[float] = []
        trend_points: list[dict[str, Any]] = []

        for run in asset_runs:
            cost = _safe_float(run.get("total_imbalance_cost_tl"))
            total_imbalance_cost_tl += cost

            mape = run.get("mape_percentage")
            if mape is not None:
                mape_values.append(_safe_float(mape))

            risk = run.get("risk_score")
            if risk is not None:
                risk_values.append(_safe_float(risk))

            alert_status = run.get("alert_status") or {}
            severity = str(alert_status.get("severity") or "").upper()
            if severity == "CRITICAL":
                critical_alerts_count += 1
            elif severity in {"WARNING", "WARN"}:
                warning_alerts_count += 1

            dq = run.get("data_quality") or {}
            if isinstance(dq, dict) and dq.get("score") is not None:
                dq_scores.append(_safe_float(dq.get("score")))

            conf = run.get("confidence_calibrated")
            if conf is None:
                stack = run.get("confidence_stack") or {}
                conf = stack.get("confidence_calibrated") if isinstance(stack, dict) else None
            if conf is not None:
                confidence_values.append(_safe_float(conf))

            trend_points.append(
                {
                    "date": str(run.get("target_date") or run.get("saved_at") or "")[:10],
                    "cost_tl": round(cost, 2),
                    "mape": round(_safe_float(mape), 2) if mape is not None else None,
                    "risk": _safe_int(risk) if risk is not None else None,
                    "severity": severity or None,
                }
            )

        average_mape = _avg(mape_values)
        average_risk = _avg(risk_values)
        average_dq = _avg(dq_scores)
        average_confidence = _avg(confidence_values)
        total_imbalance_cost_tl = round(total_imbalance_cost_tl, 2)
        run_count = len(asset_runs)

        simulation = bool(
            latest.get("mape_informational") is True
            or latest.get("ground_truth_mode") in {"simulated", "mock", "simulation"}
        )

        executive_summary = build_localized_executive_summary(
            locale,
            asset_id=asset_id,
            period_days=days_back,
            run_count=run_count,
            total_imbalance_cost_tl=total_imbalance_cost_tl,
            average_mape=average_mape,
            critical_alerts_count=critical_alerts_count,
        )

        pack = self._build_intelligence_pack(
            locale=locale,
            asset_id=asset_id,
            days_back=days_back,
            runs=asset_runs,
            latest=latest,
            mape_values=mape_values,
            total_imbalance_cost_tl=total_imbalance_cost_tl,
            average_mape=average_mape,
            average_risk=average_risk,
            average_dq=average_dq,
            average_confidence=average_confidence,
            critical_alerts_count=critical_alerts_count,
            warning_alerts_count=warning_alerts_count,
            trend_points=trend_points,
            simulation=simulation,
        )

        changes = self._build_changes_since_last(locale, trend_points, mape_values, risk_values)
        visible = list(REPORT_TYPE_SECTIONS.get(report_type, REPORT_TYPE_SECTIONS["executive"]))
        type_label = translate(locale, f"reporting.type_{report_type}")
        focus = translate(locale, f"reporting.type_focus_{report_type}")
        pack_title = translate(locale, "reporting.pack_title", report_type=type_label, asset_id=asset_id)

        # Tip bazlı brifing başlığı / odak cümlesi — aynı pack, farklı vurgu
        ai_brief = dict(pack["ai_brief"])
        ai_brief["title"] = pack_title
        ai_brief["focus"] = focus
        if report_type != "executive":
            base_summary = executive_summary
            executive_summary = f"{pack_title}. {focus} {base_summary}"

        adaptive_hint = ""
        if workspace:
            suggested = WORKSPACE_DEFAULT_REPORT.get(workspace, "executive")
            adaptive_hint = translate(
                locale,
                "reporting.adaptive_hint",
                workspace=workspace,
                report_type=translate(locale, f"reporting.type_{suggested}"),
            )

        report = ExecutiveReportResponse(
            generated_at=datetime.now(timezone.utc),
            asset_id=asset_id,
            period_days=days_back,
            total_imbalance_cost_tl=total_imbalance_cost_tl,
            average_mape=average_mape,
            critical_alerts_count=critical_alerts_count,
            executive_summary=executive_summary,
            run_count=run_count,
            scorecards=pack["scorecards"],
            ai_brief=ai_brief,
            financial=pack["financial"],
            forecast=pack["forecast"],
            operational=pack["operational"],
            risk=pack["risk"],
            data_intelligence=pack["data_intelligence"],
            model_intelligence=pack["model_intelligence"],
            recommendations=pack["recommendations"],
            actions=pack["actions"],
            trends=pack["trends"],
            benchmark=pack["benchmark"],
            conclusion=pack["conclusion"],
            mape_informational=simulation,
            report_type=report_type,
            changes_since_last=changes,
            visible_sections=visible,
            adaptive_hint=adaptive_hint,
        )

        self._logger.info(
            "Yonetici Intelligence Pack uretildi: asset_id=%s type=%s period_days=%s runs=%s",
            asset_id,
            report_type,
            days_back,
            run_count,
        )
        return report.model_dump(mode="json")

    def suggested_report_type(self, workspace: str | None) -> str:
        return WORKSPACE_DEFAULT_REPORT.get((workspace or "").strip().lower(), "executive")

    def ask_about_report(
        self,
        asset_id: str,
        question: str,
        *,
        days_back: int = 30,
        locale: str = "tr",
        report_type: str = "executive",
    ) -> dict[str, Any]:
        """Rapor paketine göre soru-cevap — Gemini/OpenAI varsa canlı, yoksa şablon."""
        locale = normalize_locale(locale)
        report = self.generate_executive_report(
            asset_id=asset_id,
            days_back=days_back,
            locale=locale,
            report_type=report_type,
        )
        off_topic = self._is_off_topic_question(question)

        llm_answer = self._ask_with_llm(
            report,
            question,
            locale=locale,
            off_topic=off_topic,
        )
        if (
            llm_answer
            and not self._is_shallow_why_answer(question, llm_answer)
            and not (off_topic and self._looks_like_report_dump(llm_answer))
        ):
            return {
                "asset_id": asset_id,
                "question": question,
                "answer": llm_answer,
                "citations": [],
                "source": "llm",
                "report_type": report.get("report_type"),
                "locale": locale,
            }

        if off_topic:
            return {
                "asset_id": asset_id,
                "question": question,
                "answer": translate(locale, "reporting.ask_off_topic"),
                "citations": [],
                "source": "template",
                "report_type": report.get("report_type"),
                "locale": locale,
            }

        template = self._ask_with_template(report, question, locale=locale)
        return {
            "asset_id": asset_id,
            "question": question,
            "answer": template["answer"],
            "citations": template["citations"],
            "source": "template",
            "report_type": report.get("report_type"),
            "locale": locale,
        }

    @staticmethod
    def _normalize_ask_question(question: str) -> str:
        return (question or "").strip().casefold()

    @classmethod
    def _is_why_question(cls, question: str) -> bool:
        q = cls._normalize_ask_question(question)
        return any(marker in q for marker in _WHY_MARKERS)

    @classmethod
    def _is_off_topic_question(cls, question: str) -> bool:
        q = cls._normalize_ask_question(question)
        if not q:
            return True
        return not any(marker in q for marker in _REPORT_TOPIC_MARKERS)

    @classmethod
    def _is_shallow_why_answer(cls, question: str, answer: str) -> bool:
        """Reject bare KPI dumps when the user asked for a causal explanation."""
        if not cls._is_why_question(question):
            return False
        text = (answer or "").strip()
        if not text:
            return True
        lower = text.casefold()
        looks_bare = any(m in lower for m in _BARE_DUMP_MARKERS) and any(
            m in lower for m in _BARE_DUMP_LATEST
        )
        has_causal = any(m in lower for m in _CAUSAL_ANSWER_MARKERS)
        return bool(looks_bare and not has_causal)

    @staticmethod
    def _looks_like_report_dump(answer: str) -> bool:
        """Detect executive-summary dumps (cost/MAPE walls) used for off-topic refusals."""
        text = (answer or "").strip()
        if not text:
            return True
        lower = text.casefold()
        has_cost = any(
            tok in lower
            for tok in (" tl", "tl,", "maliyet", "imbalance cost", "ungleichgewicht")
        ) or any(ch.isdigit() for ch in text) and ("." in text or "," in text)
        has_summary_shape = any(
            tok in lower
            for tok in (
                "özet:",
                "sonuç:",
                "summary:",
                "conclusion:",
                "genel durum",
                "acil göz",
                "dengesizlik maliyeti",
                "executive summary",
                "öncelikli aksiyon",
                "oncelikli aksiyon",
            )
        )
        return bool(has_summary_shape or (has_cost and len(text) > 120))

    @staticmethod
    def _truncate_at_word(text: str, max_len: int) -> str:
        value = (text or "").strip()
        if max_len <= 0 or len(value) <= max_len:
            return value
        cut = value[:max_len]
        sp = cut.rfind(" ")
        if sp > max(20, max_len // 3):
            cut = cut[:sp]
        return cut.rstrip(" ,.;:…") + "…"

    @classmethod
    def _strip_ask_field_labels(cls, text: str) -> str:
        value = (text or "").strip()
        lowered = value.casefold()
        for prefix in _ASK_FIELD_LABEL_PREFIXES:
            if lowered.startswith(prefix):
                value = value[len(prefix) :].strip()
                lowered = value.casefold()
        return value

    @classmethod
    def _compose_ask_summary_conclusion(
        cls,
        report: dict[str, Any],
        *,
        locale: str,
        summary_max: int,
        conclusion_max: int,
        template_key: str,
        extra: dict[str, Any] | None = None,
    ) -> str:
        summary = cls._truncate_at_word(
            cls._strip_ask_field_labels(str(report.get("executive_summary") or "")),
            summary_max,
        )
        conclusion = cls._truncate_at_word(
            cls._strip_ask_field_labels(str(report.get("conclusion") or "")),
            conclusion_max,
        )
        params = {"summary": summary or "—", "conclusion": conclusion or "—"}
        if extra:
            params.update(extra)
        return translate(locale, template_key, **params)

    def _ask_with_llm(
        self,
        report: dict[str, Any],
        question: str,
        *,
        locale: str,
        off_topic: bool = False,
    ) -> str | None:
        pack = self._compact_ask_pack(report)
        pack_json = json.dumps(pack, ensure_ascii=False, separators=(",", ":"))
        if len(pack_json) > _ASK_PACK_MAX_CHARS:
            pack_json = pack_json[:_ASK_PACK_MAX_CHARS] + "…"

        if off_topic:
            user_text = (
                f"locale={locale}\n"
                f"question={question.strip()}\n"
                "This question is OFF-TOPIC (not about the report). "
                "Politely refuse in the locale language. Tell the user to ask about MAPE, cost, "
                "risk, or actions. Do NOT quote report numbers, summaries, or conclusions."
            )
        else:
            why_hint = (
                "This is a WHY/causal question. Lead with drivers (deltas, prior vs recent, top rules, "
                "simulation). Do NOT reply with only average + latest MAPE. "
                if self._is_why_question(question)
                else ""
            )
            user_text = (
                f"locale={locale}\n"
                f"question={question.strip()}\n"
                f"report_pack={pack_json}\n"
                f"{why_hint}"
                "Answer THIS question specifically using only report_pack numbers and facts. "
                "Explain why when asked; do not dump unrelated KPIs. Write in the locale language. "
                "Do not mention citation slugs or raw pack keys."
            )
        answer = self._ai_assistant.complete_text(
            _ASK_SYSTEM_PROMPT,
            user_text,
            max_output_tokens=_ASK_ANSWER_MAX_TOKENS,
            temperature=0.2,
        )
        if not answer:
            return None
        cleaned = answer.strip()
        if cleaned.startswith("```"):
            # Strip accidental markdown fences
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned or None

    @staticmethod
    def _compact_ask_pack(report: dict[str, Any]) -> dict[str, Any]:
        pack: dict[str, Any] = {}
        for key in _ASK_PACK_KEYS:
            if key not in report or report[key] is None:
                continue
            value = report[key]
            if key == "scorecards" and isinstance(value, list):
                pack[key] = [
                    {
                        "id": item.get("id"),
                        "label": item.get("label"),
                        "value": item.get("value"),
                        "level": item.get("level"),
                        "level_label": item.get("level_label"),
                    }
                    for item in value[:8]
                    if isinstance(item, dict)
                ]
            elif key == "ai_brief" and isinstance(value, dict):
                pack[key] = {
                    "title": value.get("title"),
                    "status_summary": value.get("status_summary"),
                    "recommended_action": value.get("recommended_action"),
                    "top_event": value.get("top_event"),
                    "top_risk": value.get("top_risk"),
                    "simulation": value.get("simulation"),
                    "confidence": value.get("confidence"),
                }
            elif key == "changes_since_last" and isinstance(value, dict):
                pack[key] = {
                    "summary": value.get("summary"),
                    "mape_delta": value.get("mape_delta"),
                    "cost_delta_pct": value.get("cost_delta_pct"),
                    "risk_delta": value.get("risk_delta"),
                    "kpi_up": value.get("kpi_up"),
                    "kpi_down": value.get("kpi_down"),
                    "new_alerts": value.get("new_alerts"),
                    "prior_avg_mape": value.get("prior_avg_mape"),
                    "recent_avg_mape": value.get("recent_avg_mape"),
                }
            elif key in ("executive_summary", "conclusion") and isinstance(value, str):
                pack[key] = value[:400]
            else:
                pack[key] = value
        return pack

    def _ask_with_template(
        self,
        report: dict[str, Any],
        question: str,
        *,
        locale: str,
    ) -> dict[str, Any]:
        q = self._normalize_ask_question(question)
        # Causal intent first — never let a bare metric branch win on "mape neden arttı".
        wants_why = self._is_why_question(question)
        changes = report.get("changes_since_last") or {}
        change_summary = str(changes.get("summary") or "").strip()
        answer: str
        citations: list[str] = []

        if any(k in q for k in ("mape", "tahmin", "forecast", "rmse", "mae", "prognose")):
            if wants_why:
                answer = self._build_mape_why_answer(report, locale=locale)
            else:
                fc = report.get("forecast") or {}
                answer = translate(
                    locale,
                    "reporting.ask_mape",
                    mape=f"{_safe_float(fc.get('average_mape')):.2f}",
                    label=str(fc.get("mape_label") or ""),
                    latest=f"{_safe_float(fc.get('latest_mape')):.2f}",
                )
            citations = ["forecast"]
        elif any(k in q for k in ("cost", "maliyet", "tl", "imbalance", "dengesizlik", "kosten")):
            fin = report.get("financial") or {}
            total = f"{_safe_float(fin.get('total_cost_tl')):,.2f}"
            trend = str(fin.get("cost_trend_label") or fin.get("cost_trend") or "—")
            avoidable = f"{_safe_float(fin.get('avoidable_cost_estimate_tl')):,.2f}"
            cost_delta = changes.get("cost_delta_pct")
            if wants_why:
                answer = translate(
                    locale,
                    "reporting.ask_cost_why",
                    total=total,
                    trend=trend,
                    avoidable=avoidable,
                    cost_delta=f"{_safe_float(cost_delta):+.1f}" if cost_delta is not None else "—",
                    changes=change_summary or "—",
                    drivers=self._format_why_drivers(report, locale=locale),
                )
            else:
                answer = translate(
                    locale,
                    "reporting.ask_cost",
                    total=total,
                    trend=trend,
                    avoidable=avoidable,
                )
            citations = ["financial"]
        elif any(k in q for k in ("risk", "risko", "alarm", "uyarı", "warn")):
            risk = report.get("risk") or {}
            score = str(risk.get("average_score") or "—")
            level = str(risk.get("level_label") or risk.get("level") or "—")
            rule = str(risk.get("top_rule") or "—")
            risk_delta = changes.get("risk_delta")
            if wants_why:
                answer = translate(
                    locale,
                    "reporting.ask_risk_why",
                    score=score,
                    level=level,
                    rule=rule,
                    risk_delta=f"{_safe_float(risk_delta):+.1f}" if risk_delta is not None else "—",
                    changes=change_summary or "—",
                    drivers=self._format_why_drivers(report, locale=locale),
                )
            else:
                answer = translate(
                    locale,
                    "reporting.ask_risk",
                    score=score,
                    level=level,
                    rule=rule,
                )
            citations = ["risk"]
        elif any(k in q for k in ("aksiyon", "action", "öner", "recommend", "ne yap", "what should")):
            brief = report.get("ai_brief") or {}
            answer = translate(
                locale,
                "reporting.ask_action",
                action=str(brief.get("recommended_action") or report.get("conclusion") or "—"),
            )
            citations = ["ai_brief", "actions"]
        elif wants_why:
            answer = self._compose_ask_summary_conclusion(
                report,
                locale=locale,
                summary_max=220,
                conclusion_max=160,
                template_key="reporting.ask_why_default",
                extra={
                    "changes": change_summary or "—",
                    "drivers": self._format_why_drivers(report, locale=locale),
                },
            )
            citations = ["changes", "summary"]
        else:
            answer = self._compose_ask_summary_conclusion(
                report,
                locale=locale,
                summary_max=280,
                conclusion_max=200,
                template_key="reporting.ask_default",
            )
            citations = ["summary", "conclusion"]

        return {"answer": answer, "citations": citations}

    @classmethod
    def _format_why_drivers(cls, report: dict[str, Any], *, locale: str) -> str:
        changes = report.get("changes_since_last") or {}
        risk = report.get("risk") or {}
        brief = report.get("ai_brief") or {}
        parts: list[str] = []
        kpi_up = changes.get("kpi_up") or []
        kpi_down = changes.get("kpi_down") or []
        if kpi_up:
            parts.append(translate(locale, "reporting.ask_driver_up", items=", ".join(str(x) for x in kpi_up)))
        if kpi_down:
            parts.append(translate(locale, "reporting.ask_driver_down", items=", ".join(str(x) for x in kpi_down)))
        top_rule = str(risk.get("top_rule") or "").strip()
        if top_rule and top_rule != "—":
            parts.append(translate(locale, "reporting.ask_driver_rule", rule=top_rule))
        if brief.get("simulation"):
            parts.append(translate(locale, "reporting.ask_driver_simulation"))
        top_event = str(brief.get("top_event") or "").strip()
        if top_event and top_event != "—":
            parts.append(translate(locale, "reporting.ask_driver_event", event=top_event[:120]))
        new_alerts = changes.get("new_alerts")
        if isinstance(new_alerts, (int, float)) and new_alerts > 0:
            parts.append(translate(locale, "reporting.ask_driver_alerts", count=int(new_alerts)))
        return " ".join(parts) if parts else translate(locale, "reporting.ask_driver_none")

    @classmethod
    def _build_mape_why_answer(cls, report: dict[str, Any], *, locale: str) -> str:
        fc = report.get("forecast") or {}
        changes = report.get("changes_since_last") or {}
        mape = f"{_safe_float(fc.get('average_mape')):.2f}"
        latest = f"{_safe_float(fc.get('latest_mape')):.2f}"
        label = str(fc.get("mape_label") or "")
        mape_delta = changes.get("mape_delta")
        prior = changes.get("prior_avg_mape")
        recent = changes.get("recent_avg_mape")
        prior_s = f"{_safe_float(prior):.2f}" if prior is not None else "—"
        recent_s = f"{_safe_float(recent):.2f}" if recent is not None else "—"
        delta_s = f"{_safe_float(mape_delta):+.2f}" if mape_delta is not None else "—"
        change_summary = str(changes.get("summary") or "").strip() or "—"
        drivers = cls._format_why_drivers(report, locale=locale)
        watch = str((report.get("ai_brief") or {}).get("recommended_action") or report.get("conclusion") or "—")
        return translate(
            locale,
            "reporting.ask_mape_why",
            mape=mape,
            label=label,
            latest=latest,
            mape_delta=delta_s,
            prior=prior_s,
            recent=recent_s,
            changes=change_summary,
            drivers=drivers,
            watch=watch[:180],
        )

    @staticmethod
    def _build_changes_since_last(
        locale: str,
        trend_points: list[dict[str, Any]],
        mape_values: list[float],
        risk_values: list[float],
    ) -> dict[str, Any]:
        if len(trend_points) < 2:
            return {
                "summary": translate(locale, "reporting.changes_insufficient"),
                "kpi_up": [],
                "kpi_down": [],
                "new_alerts": 0,
                "cost_delta_pct": 0.0,
                "mape_delta": 0.0,
                "risk_delta": 0.0,
                "prior_avg_mape": None,
                "recent_avg_mape": None,
            }

        half = max(1, len(trend_points) // 2)
        recent = trend_points[:half]
        prior = trend_points[half:]
        recent_cost = _avg([_safe_float(p.get("cost_tl")) for p in recent])
        prior_cost = _avg([_safe_float(p.get("cost_tl")) for p in prior])
        recent_mape = _avg([_safe_float(p.get("mape")) for p in recent if p.get("mape") is not None])
        prior_mape = _avg([_safe_float(p.get("mape")) for p in prior if p.get("mape") is not None])
        recent_risk = _avg([_safe_float(p.get("risk")) for p in recent if p.get("risk") is not None])
        prior_risk = _avg([_safe_float(p.get("risk")) for p in prior if p.get("risk") is not None])

        cost_delta_pct = round(((recent_cost - prior_cost) / prior_cost) * 100, 1) if prior_cost else 0.0
        mape_delta = round(recent_mape - prior_mape, 2)
        risk_delta = round(recent_risk - prior_risk, 1)

        recent_crit = sum(1 for p in recent if str(p.get("severity") or "").upper() == "CRITICAL")
        prior_crit = sum(1 for p in prior if str(p.get("severity") or "").upper() == "CRITICAL")
        new_alerts = max(0, recent_crit - prior_crit)
        closed_alerts = max(0, prior_crit - recent_crit)

        kpi_up: list[str] = []
        kpi_down: list[str] = []
        if cost_delta_pct > 2:
            kpi_up.append("cost")
        elif cost_delta_pct < -2:
            kpi_down.append("cost")
        if mape_delta > 0.5:
            kpi_up.append("mape")
        elif mape_delta < -0.5:
            kpi_down.append("mape")
        if risk_delta > 2:
            kpi_up.append("risk")
        elif risk_delta < -2:
            kpi_down.append("risk")

        summary = translate(
            locale,
            "reporting.changes_summary",
            cost_delta=cost_delta_pct,
            mape_delta=mape_delta,
            risk_delta=risk_delta,
            new_alerts=new_alerts,
            closed_alerts=closed_alerts,
        )
        return {
            "summary": summary,
            "kpi_up": kpi_up,
            "kpi_down": kpi_down,
            "new_alerts": new_alerts,
            "closed_alerts": closed_alerts,
            "cost_delta_pct": cost_delta_pct,
            "mape_delta": mape_delta,
            "risk_delta": risk_delta,
            "recent_avg_cost_tl": round(recent_cost, 2),
            "prior_avg_cost_tl": round(prior_cost, 2),
            "recent_avg_mape": round(recent_mape, 2),
            "prior_avg_mape": round(prior_mape, 2),
            "recent_avg_risk": round(recent_risk, 1),
            "prior_avg_risk": round(prior_risk, 1),
        }

    def _build_intelligence_pack(
        self,
        *,
        locale: str,
        asset_id: str,
        days_back: int,
        runs: list[dict[str, Any]],
        latest: dict[str, Any],
        mape_values: list[float],
        total_imbalance_cost_tl: float,
        average_mape: float,
        average_risk: float,
        average_dq: float,
        average_confidence: float,
        critical_alerts_count: int,
        warning_alerts_count: int,
        trend_points: list[dict[str, Any]],
        simulation: bool,
    ) -> dict[str, Any]:
        insufficient = translate(locale, "reporting.insufficient")
        risk_data = {
            "risk_score": _safe_int(latest.get("risk_score"), int(average_risk)),
            "total_imbalance_cost_tl": _safe_float(latest.get("total_imbalance_cost_tl"), total_imbalance_cost_tl),
            "forecast_mw": latest.get("forecast_mw") or latest.get("total_daily_mw") or 0,
            "wind_speed_mps": latest.get("wind_speed_mps") or 0,
        }
        action_plan = localize_action_plan(locale, risk_data, latest.get("action_plan"))
        playbook_id = select_playbook_id(risk_data)
        stored_insight = str(latest.get("ai_insight") or "")
        fallback_markers = (
            "AI servisine ulaşılamadı",
            "otomatik playbook",
            "unreachable",
        )
        use_stored = (
            locale == "tr"
            and stored_insight
            and not any(m.lower() in stored_insight.lower() for m in fallback_markers)
        )
        insight = stored_insight if use_stored else playbook_insight(locale, playbook_id)

        raw_rules = latest.get("rules") or []
        rules = [localize_rule(locale, r, simulation=simulation) for r in raw_rules if isinstance(r, dict)]
        top_rule = rules[0] if rules else {}
        top_rule_title = str(
            top_rule.get("message")
            or top_rule.get("title")
            or top_rule.get("action")
            or insufficient
        )
        # rule_id slug asıla kalmasın
        if top_rule_title.replace("_", "").isalnum() and "_" in top_rule_title:
            top_rule_title = insufficient


        # --- Scorecards ---
        financial_level = _level_from_thresholds(total_imbalance_cost_tl, warn=5000, crit=20000)
        forecast_level = _level_from_thresholds(average_mape, warn=10, crit=20)
        risk_level = _level_from_thresholds(average_risk, warn=50, crit=75)
        dq_level = _level_from_thresholds(average_dq or 100, warn=70, crit=50, higher_is_worse=False)
        model_level = _level_from_thresholds(average_confidence or 50, warn=50, crit=30, higher_is_worse=False)
        alert_level = "crit" if critical_alerts_count > 0 else ("warn" if warning_alerts_count > 0 else "ok")
        overall_rank = {"ok": 0, "warn": 1, "crit": 2}
        overall_level = max(
            [financial_level, forecast_level, risk_level, dq_level, model_level, alert_level],
            key=lambda x: overall_rank.get(x, 0),
        )

        def card(key: str, value: str, level: str, note: str = "") -> dict[str, Any]:
            return {
                "id": key,
                "label": translate(locale, f"reporting.score_{key}"),
                "value": value,
                "level": level,
                "level_label": reporting_level_label(locale, level),
                "note": note,
            }

        # Güven: ham 0 ise MAPE/risk'ten türetilmiş operasyonel skor göster
        derived_confidence = average_confidence
        if not derived_confidence:
            derived_confidence = max(5.0, min(95.0, 100.0 - average_mape - (average_risk * 0.15)))
        display_confidence = int(round(derived_confidence))

        scorecards = [
            card("overall", reporting_level_label(locale, overall_level), overall_level),
            card("financial", f"{total_imbalance_cost_tl:,.0f} TL", financial_level),
            card("operational", reporting_level_label(locale, alert_level), alert_level),
            card(
                "forecast",
                f"%{average_mape:.1f}",
                forecast_level,
                translate(locale, "reporting.sim_flag") if simulation else i18n_mape_label(locale, average_mape),
            ),
            card("risk", f"{average_risk:.0f}/100", risk_level),
            card("data", f"{average_dq:.0f}" if dq_scores_present(average_dq, runs) else "—", dq_level if average_dq else "warn"),
            card("model", f"{display_confidence}", model_level if average_confidence else "warn"),
            card("alerts", str(critical_alerts_count), alert_level),
        ]

        ai_brief = {
            "title": translate(locale, "reporting.ai_brief_title"),
            "status_summary": insight[:500] if insight else executive_fallback_brief(locale, asset_id, average_risk, average_mape),
            "top_event": top_rule_title,
            "top_risk": f"{average_risk:.0f}/100 — {top_rule_title}",
            "financial_impact": f"{total_imbalance_cost_tl:,.2f} TL",
            "operational_impact": i18n_mape_label(locale, average_mape),
            "recommended_action": action_plan or translate(locale, "briefing.default_action"),
            "confidence": display_confidence,
            "simulation": simulation,
        }

        # Financial
        costs = [_safe_float(r.get("total_imbalance_cost_tl")) for r in runs]
        half = max(1, len(costs) // 2)
        recent_avg = _avg(costs[:half]) if costs else 0.0
        prior_avg = _avg(costs[half:]) if len(costs) > half else recent_avg
        cost_trend = "up" if recent_avg > prior_avg * 1.05 else ("down" if recent_avg < prior_avg * 0.95 else "flat")
        cost_trend_label = translate(locale, f"reporting.trend_{cost_trend}")
        financial = {
            "total_cost_tl": total_imbalance_cost_tl,
            "average_daily_cost_tl": round(total_imbalance_cost_tl / max(len(runs), 1), 2),
            "latest_cost_tl": _safe_float(latest.get("total_imbalance_cost_tl")),
            "cost_trend": cost_trend,
            "cost_trend_label": cost_trend_label,
            "avoidable_cost_estimate_tl": round(total_imbalance_cost_tl * 0.15, 2) if critical_alerts_count else 0.0,
            "revenue_risk_tl": round(total_imbalance_cost_tl * (average_risk / 100.0), 2),
        }

        # Forecast
        reliability = latest.get("model_reliability") or {}
        if not isinstance(reliability, dict):
            reliability = {}
        walk = reliability.get("walk_forward") or reliability.get("acceptance") or {}
        if not isinstance(walk, dict):
            walk = {}
        forecast = {
            "average_mape": average_mape,
            "latest_mape": _safe_float(latest.get("mape_percentage")),
            "mape_label": i18n_mape_label(locale, average_mape),
            "rmse": walk.get("rmse") or reliability.get("rmse"),
            "mae": walk.get("mae") or reliability.get("mae"),
            "confidence": display_confidence,
            "informational": simulation,
            "prediction_interval": (latest.get("confidence_stack") or {}).get("prediction_interval")
            if isinstance(latest.get("confidence_stack"), dict)
            else None,
        }

        # Operational
        notifications = latest.get("notifications") or []
        operational = {
            "latest_severity": (latest.get("alert_status") or {}).get("severity"),
            "critical_count": critical_alerts_count,
            "warning_count": warning_alerts_count,
            "active_rules": len(rules),
            "rules": [
                {
                    "rule_id": r.get("rule_id"),
                    "title": (
                        r.get("message")
                        or r.get("title")
                        or r.get("action")
                        or insufficient
                    ),
                    "severity": r.get("severity"),
                }
                for r in rules[:8]
            ],
            "notification_count": len(notifications) if isinstance(notifications, list) else 0,
            "pipeline_runs": len(runs),
        }

        # Risk
        risk = {
            "average_score": round(average_risk, 1),
            "latest_score": _safe_int(latest.get("risk_score")),
            "max_score": max((_safe_int(r.get("risk_score")) for r in runs), default=0),
            "level": risk_level,
            "level_label": reporting_level_label(locale, risk_level),
            "top_rule": top_rule_title,
            "financial_risk_tl": financial["revenue_risk_tl"],
            "overall_index": round(average_risk, 1),
        }

        # Data intelligence
        latest_dq = latest.get("data_quality") if isinstance(latest.get("data_quality"), dict) else {}
        data_intelligence = {
            "average_score": round(average_dq, 1) if average_dq else None,
            "latest_score": latest_dq.get("score"),
            "gate_passed": latest_dq.get("gate_passed"),
            "checks": latest_dq.get("checks") or latest_dq.get("issues") or [],
            "trust_score": round(average_dq, 1) if average_dq else None,
            "level": dq_level if average_dq else "warn",
        }

        # Model intelligence
        drift = latest.get("drift") if isinstance(latest.get("drift"), dict) else {}
        model_intelligence = {
            "confidence": display_confidence,
            "reliability_gate": reliability.get("gate_passed") or reliability.get("passed"),
            "drift_detected": drift.get("detected") or drift.get("status"),
            "model_version": latest.get("model_version") or reliability.get("model_version"),
            "physics_fallback": bool(latest.get("physics_fallback") or reliability.get("physics_fallback")),
            "coverage": (
                reliability.get("coverage")
                if reliability.get("coverage") is not None
                else (
                    (latest.get("confidence_stack") or {}).get("coverage")
                    if isinstance(latest.get("confidence_stack"), dict)
                    else None
                )
            ),
            "level": model_level if average_confidence else "warn",
        }

        # Recommendations + actions
        context_recs = get_recommendations(locale, "reports")
        recommendations: list[dict[str, Any]] = []
        if action_plan:
            priority = "high" if critical_alerts_count or average_risk >= 75 else "medium"
            recommendations.append(
                {
                    "title": action_plan,
                    "situation": top_rule_title,
                    "impact": f"{total_imbalance_cost_tl:,.0f} TL",
                    "priority": priority,
                    "priority_label": translate(locale, f"reporting.priority_{priority}"),
                    "confidence": display_confidence,
                }
            )
        for text in context_recs[:5]:
            recommendations.append(
                {
                    "title": text,
                    "situation": asset_id,
                    "impact": "—",
                    "priority": "medium",
                    "priority_label": translate(locale, "reporting.priority_medium"),
                    "confidence": display_confidence,
                }
            )

        actions = []
        for idx, rec in enumerate(recommendations[:6], start=1):
            priority = str(rec.get("priority") or "medium")
            actions.append(
                {
                    "id": f"ACT-{idx:02d}",
                    "title": rec.get("title"),
                    "priority": priority,
                    "priority_label": translate(locale, f"reporting.priority_{priority}"),
                    "status": translate(locale, "reporting.status_open"),
                    "owner": "Operations",
                    "expected_impact": rec.get("impact"),
                }
            )

        # Trends (newest-first input → chronological for charts)
        series = list(reversed(trend_points[:30]))
        trends = {
            "period_days": days_back,
            "points": series,
            "cost_sparkline": [p["cost_tl"] for p in series if p.get("cost_tl") is not None],
            "mape_sparkline": [p["mape"] for p in series if p.get("mape") is not None],
            "risk_sparkline": [p["risk"] for p in series if p.get("risk") is not None],
        }

        # Benchmark: prior half of period vs recent half; portfolio peer if available
        peer_runs = [
            r
            for r in self._storage.get_recent_runs(limit=days_back * 3, dedupe=True)
            if r.get("asset_id") and r.get("asset_id") != asset_id
        ]
        peer_mape = _avg([_safe_float(r.get("mape_percentage")) for r in peer_runs if r.get("mape_percentage") is not None])
        peer_cost = _avg([_safe_float(r.get("total_imbalance_cost_tl")) for r in peer_runs])
        benchmark = {
            "prior_period_avg_cost_tl": round(prior_avg, 2),
            "recent_period_avg_cost_tl": round(recent_avg, 2),
            "prior_period_avg_mape": _avg(mape_values[half:]) if len(mape_values) > half else average_mape,
            "recent_period_avg_mape": _avg(mape_values[:half]) if mape_values else average_mape,
            "portfolio_avg_mape": peer_mape or None,
            "portfolio_avg_cost_tl": round(peer_cost, 2) if peer_runs else None,
            "vs_prior_cost_pct": round(((recent_avg - prior_avg) / prior_avg) * 100, 1) if prior_avg else 0.0,
        }

        if critical_alerts_count > 0:
            posture_key = "critical_alerts"
        elif average_mape > 15.0:
            posture_key = "low_accuracy"
        elif total_imbalance_cost_tl > 5000.0:
            posture_key = "high_cost"
        else:
            posture_key = "normal"

        conclusion = build_executive_conclusion(
            locale,
            posture_key=posture_key,
            action=action_plan or translate(locale, "briefing.default_action"),
            cost=total_imbalance_cost_tl,
            risk=average_risk,
            dq=average_dq,
        )

        return {
            "scorecards": scorecards,
            "ai_brief": ai_brief,
            "financial": financial,
            "forecast": forecast,
            "operational": operational,
            "risk": risk,
            "data_intelligence": data_intelligence,
            "model_intelligence": model_intelligence,
            "recommendations": recommendations,
            "actions": actions,
            "trends": trends,
            "benchmark": benchmark,
            "conclusion": conclusion,
        }

    def get_system_kpi(self, days_back: int = 30) -> dict[str, Any]:
        """Sistem geneli MAPE, uptime ve API availability KPI'larını hesaplar."""
        from core.health import HealthMonitor

        runs = self._storage.get_recent_runs(limit=days_back)
        mape_values = [
            float(run["mape_percentage"])
            for run in runs
            if run.get("mape_percentage") is not None
        ]
        average_mape = round(sum(mape_values) / len(mape_values), 4) if mape_values else 0.0

        completed_runs = [run for run in runs if run.get("asset_id")]
        uptime_percentage = 100.0 if completed_runs else 0.0

        data_hub_status = HealthMonitor().check_data_hub()
        available_clients = sum(
            1 for status in data_hub_status.values() if status.get("status") == "ok"
        )
        total_clients = len(data_hub_status) or 1
        api_availability = round((available_clients / total_clients) * 100, 2)

        kpi = {
            "period_days": days_back,
            "average_mape": average_mape,
            "uptime_percentage": uptime_percentage,
            "api_availability_percentage": api_availability,
            "pipeline_run_count": len(completed_runs),
            "data_hub": data_hub_status,
        }
        self._logger.info("Sistem KPI hesaplandi: %s", kpi)
        return kpi

    def generate_weekly_report(self, asset_id: str, weeks_back: int = 4, locale: str = "tr") -> dict[str, Any]:
        """Haftalık agregasyon raporu üretir."""
        locale = normalize_locale(locale)
        asset_runs = self._storage.get_recent_runs(
            limit=weeks_back * 7,
            asset_id=asset_id,
            dedupe=True,
        )

        weeks: dict[str, dict[str, Any]] = {}
        for run in asset_runs:
            target = str(run.get("target_date", ""))[:10]
            if not target:
                continue
            week_key = target[:7]
            bucket = weeks.setdefault(
                week_key,
                {"week": week_key, "runs": 0, "total_cost_tl": 0.0, "mape_values": [], "max_risk": 0},
            )
            bucket["runs"] += 1
            cost = run.get("total_imbalance_cost_tl")
            if cost is not None:
                bucket["total_cost_tl"] += float(cost)
            mape = run.get("mape_percentage")
            if mape is not None:
                bucket["mape_values"].append(float(mape))
            risk = run.get("risk_score")
            if risk is not None:
                bucket["max_risk"] = max(bucket["max_risk"], int(risk))

        weekly_rows = []
        for week_key in sorted(weeks.keys(), reverse=True)[:weeks_back]:
            bucket = weeks[week_key]
            avg_mape = (
                round(sum(bucket["mape_values"]) / len(bucket["mape_values"]), 2)
                if bucket["mape_values"]
                else 0.0
            )
            weekly_rows.append(
                {
                    "week": week_key,
                    "runs": bucket["runs"],
                    "total_cost_tl": round(bucket["total_cost_tl"], 2),
                    "average_mape": avg_mape,
                    "max_risk_score": bucket["max_risk"],
                }
            )

        if weekly_rows:
            summary = translate(
                locale,
                "reporting.weekly_summary",
                asset_id=asset_id,
                weeks=len(weekly_rows),
                runs=sum(row["runs"] for row in weekly_rows),
            )
        else:
            summary = translate(locale, "reporting.weekly_empty", asset_id=asset_id)

        return {
            "asset_id": asset_id,
            "weeks_analyzed": len(weekly_rows),
            "weeks": weekly_rows,
            "summary": summary,
        }


def dq_scores_present(average_dq: float, runs: list[dict[str, Any]]) -> bool:
    if average_dq:
        return True
    return any(isinstance(r.get("data_quality"), dict) and r["data_quality"].get("score") is not None for r in runs)


def executive_fallback_brief(locale: str, asset_id: str, risk: float, mape: float) -> str:
    return translate(
        locale,
        "briefing.status_summary",
        name=asset_id,
        risk=int(risk),
        risk_label=risk_label(locale, int(risk)),
        mape=mape,
        mape_label=i18n_mape_label(locale, mape),
        context="reports",
    )
