"""Sayfa baglamina gore kurumsal AI brifing uretici."""

from __future__ import annotations

from typing import Any, Optional

from core.config import get_settings
from core.i18n import (
    build_localized_briefing_structured,
    get_expert,
    get_recommendations,
    localize_action_plan,
    localize_rule,
    mape_label as i18n_mape_label,
    normalize_locale,
    playbook_insight,
    quality_label,
    select_playbook_id,
    translate,
)
from core.health import HealthMonitor
from core.logger import get_logger
from core.storage import PipelineStorage
from modules.forecast.production.confidence_stack import (
    compute_base_confidence,
    compute_calibrated_confidence,
)
from modules.forecast.production.explainability import to_feature_importance
from modules.recommendation.quality import evaluate_recommendation_quality
from modules.reporting.service import ReportingService

_CONTEXTS = {
    "dashboard",
    "operations",
    "forecast",
    "market",
    "risk",
    "ai",
    "reports",
    "assets",
    "monitoring",
    "scenarios",
    "settings",
}

_EXPERTS: dict[str, dict[str, str]] = {
    "dashboard": {"title": "Yönetici Asistanı", "subtitle": "Portföy ve üst düzey karar desteği"},
    "operations": {"title": "Operasyon Asistanı", "subtitle": "Kontrol odası ve canlı operasyon"},
    "forecast": {"title": "Tahmin Analisti", "subtitle": "Üretim tahmini ve model performansı"},
    "market": {"title": "Piyasa Analisti", "subtitle": "PTF, SMF ve dengesizlik maliyeti"},
    "risk": {"title": "Risk Analisti", "subtitle": "Risk skoru ve maruziyet yönetimi"},
    "ai": {"title": "Karar Merkezi", "subtitle": "Bekleyen aksiyonlar ve onay akışı"},
    "reports": {"title": "Yönetici Asistanı", "subtitle": "Raporlama ve finansal özet"},
    "assets": {"title": "Varlık Analisti", "subtitle": "Santral envanteri ve kapasite"},
    "monitoring": {"title": "Sistem Analisti", "subtitle": "API, veri kalitesi ve entegrasyon"},
    "scenarios": {"title": "Senaryo Analisti", "subtitle": "What-if simülasyon desteği"},
    "settings": {"title": "Platform Asistanı", "subtitle": "Yapılandırma ve yönetim"},
}

_TECHNICAL_CONTEXTS = {"forecast", "risk", "monitoring"}
_EXECUTIVE_CONTEXTS = {"reports", "dashboard", "operations", "market"}


class ContextBriefingService:
    """Her calisma alani icin yapisal AI brifing uretir."""

    def __init__(
        self,
        storage: Optional[PipelineStorage] = None,
        reporting: Optional[ReportingService] = None,
    ) -> None:
        self._storage = storage or PipelineStorage()
        self._reporting = reporting or ReportingService(self._storage)
        self._logger = get_logger("modules.ai.context_briefing")

    def generate(self, context: str, asset_id: str, days: int = 7, locale: str = "tr") -> dict[str, Any]:
        locale = normalize_locale(locale)
        if context not in _CONTEXTS:
            context = "dashboard"

        runs = [
            r for r in self._storage.get_recent_runs(limit=days * 3)
            if r.get("asset_id") == asset_id
        ]
        latest = runs[0] if runs else {}
        report = self._reporting.generate_executive_report(asset_id=asset_id, days_back=days)

        risk = int(latest.get("risk_score") or 0)
        live_mape = float(latest.get("mape_percentage") or 0)
        period_mape = float(report.get("average_mape") or 0)
        mape = live_mape if live_mape > 0 else period_mape
        cost = float(latest.get("total_imbalance_cost_tl") or report.get("total_imbalance_cost_tl") or 0)
        asset_name = str(latest.get("asset_name") or asset_id)
        base_confidence = compute_base_confidence(risk, mape)
        drift = latest.get("drift") or {}
        confidence_calibrated = int(
            latest.get("confidence_calibrated")
            or compute_calibrated_confidence(base_confidence, drift)
        )
        simulation = latest.get("ground_truth_mode") in {
            "simulated",
            "mock",
            "simulation",
        } or latest.get("mape_informational") is True

        risk_data = {
            "risk_score": risk,
            "total_imbalance_cost_tl": cost,
            "forecast_mw": latest.get("forecast_mw") or latest.get("total_daily_mw") or 0,
            "wind_speed_mps": latest.get("wind_speed_mps") or 0,
        }
        action_plan = localize_action_plan(locale, risk_data, latest.get("action_plan"))
        stored_insight = str(latest.get("ai_insight") or "")
        if locale == "tr" and stored_insight:
            ai_insight = stored_insight
        else:
            ai_insight = playbook_insight(locale, select_playbook_id(risk_data))

        raw_rules = latest.get("rules") or []
        rules = [localize_rule(locale, r, simulation=bool(simulation)) for r in raw_rules]
        top_rule = rules[0].get("message") if rules else translate(locale, "briefing.no_rule")

        settings = get_settings()
        provider = settings.llm_provider
        ai_connected = bool(settings.llm_api_key.get_secret_value()) and provider != "mock"
        expert = get_expert(locale, context)
        mode = "technical" if context in _TECHNICAL_CONTEXTS else "executive"

        if locale == "tr":
            structured = self._build_structured(
                context, asset_name, risk, mape, cost, confidence_calibrated,
                action_plan, ai_insight, top_rule, latest, report,
            )
        else:
            structured = build_localized_briefing_structured(
                locale,
                context,
                asset_name,
                risk,
                mape,
                cost,
                confidence_calibrated,
                action_plan,
                top_rule,
                latest,
            )
        technical_block = (
            self._build_technical(context, mape, risk, latest, confidence_calibrated, locale)
            if mode == "technical"
            else None
        )
        recent_decisions = self._recent_decisions(runs, locale)
        recommendations = self._recommendations(context, risk, mape, cost, locale)
        recommendation_quality = evaluate_recommendation_quality(runs, period_days=days)
        annotations = self._build_annotations(
            context,
            structured,
            rules,
            recommendations,
            risk,
            mape,
            cost,
            confidence_calibrated,
            latest,
            locale,
        )

        executive = structured["status_summary"]
        technical = structured["analysis"]
        if technical_block:
            technical = (
                f"{structured['analysis']} Model: {technical_block['model']}. "
                f"Forecast: {technical_block['forecast_quality']}. "
                f"Data: {technical_block['data_quality']}."
            )
        contribution_summary = []
        if technical_block:
            contribution_summary = [
                {
                    "feature": item.get("feature"),
                    "weight": item.get("weight"),
                }
                for item in technical_block.get("feature_importance", [])[:3]
            ]

        payload: dict[str, Any] = {
            "context": context,
            "asset_id": asset_id,
            "asset_name": asset_name,
            "mode": mode,
            "expert": {
                "id": context,
                "title": expert["title"],
                "subtitle": expert["subtitle"],
            },
            "structured": structured,
            "panel": {
                "executive_summary": structured["status_summary"],
                "top_risk": structured["risk"],
                "top_recommendation": structured["recommended_action"],
                "financial_impact": structured["financial_impact"],
                "confidence": confidence_calibrated,
                "contribution_summary": contribution_summary,
            },
            "recent_decisions": recent_decisions,
            "executive_summary": executive,
            "technical_detail": technical,
            "recommendations": recommendations,
            "recommendation_quality": recommendation_quality,
            "annotations": annotations,
            "metrics": {
                "risk_score": risk,
                "mape_percentage": round(mape, 2),
                "live_mape_percentage": round(live_mape, 2),
                "period_mape_percentage": round(period_mape, 2),
                "total_imbalance_cost_tl": round(cost, 2),
                "confidence": confidence_calibrated,
                "drift": drift,
            },
            "ai_source": provider,
            "ai_connected": ai_connected,
            "locale": locale,
        }
        if technical_block:
            payload["technical"] = technical_block

        self._logger.info("Baglam brifingi: context=%s asset_id=%s", context, asset_id)
        return payload

    def _severity_from_risk(self, risk: int) -> str:
        if risk > 75:
            return "crit"
        if risk > 50:
            return "warn"
        return "normal"

    def _build_annotations(
        self,
        context: str,
        structured: dict[str, Any],
        rules: list[dict[str, Any]],
        recommendations: list[str],
        risk: int,
        mape: float,
        cost: float,
        confidence: int,
        latest: dict[str, Any],
        locale: str = "tr",
    ) -> list[dict[str, Any]]:
        loc = normalize_locale(locale)
        annotations: list[dict[str, Any]] = []
        primary_action = str(structured.get("recommended_action") or "").strip()
        alt_action = str(structured.get("alternative_action") or "").strip()
        base_severity = self._severity_from_risk(risk)
        ml = i18n_mape_label(loc, mape)

        if primary_action:
            annotations.append({
                "id": f"decision-primary-{context}",
                "target_type": "decision",
                "target_id": "primary",
                "label": str(structured.get("title") or translate(loc, "annotations.primary_action"))[:80],
                "insight": str(structured.get("status_summary") or "")[:200],
                "severity": base_severity,
                "confidence": confidence,
                "recommended_action": primary_action,
                "context": context,
            })

        if alt_action:
            annotations.append({
                "id": f"decision-alt-{context}",
                "target_type": "decision",
                "target_id": "alternative",
                "label": translate(loc, "annotations.alternative_action"),
                "insight": str(structured.get("operational_impact") or "")[:200],
                "severity": "normal",
                "confidence": max(0, confidence - 10),
                "recommended_action": alt_action,
                "context": context,
            })

        for i, rule in enumerate(rules):
            rule_id = str(rule.get("rule_id") or f"rule-{i}")
            rule_action = str(
                rule.get("action") or primary_action or translate(loc, "annotations.verify_rule")
            ).strip()
            sev = str(rule.get("severity") or "").lower()
            if sev in {"critical", "kritik", "high", "yüksek"}:
                severity = "crit"
            elif sev in {"medium", "orta", "warn", "warning"}:
                severity = "warn"
            else:
                severity = base_severity
            annotations.append({
                "id": f"alert-{rule_id}",
                "target_type": "alert",
                "target_id": rule_id,
                "label": translate(loc, "annotations.rule_alert"),
                "insight": str(rule.get("message") or "")[:200],
                "severity": severity,
                "confidence": confidence,
                "recommended_action": rule_action,
                "context": context,
            })

        seen_actions = {primary_action, alt_action}
        for i, rec in enumerate(recommendations[:4]):
            rec_text = str(rec or "").strip()
            if not rec_text or rec_text in seen_actions:
                continue
            seen_actions.add(rec_text)
            annotations.append({
                "id": f"rec-{context}-{i}",
                "target_type": "recommendation",
                "target_id": f"rec-{i}",
                "label": translate(loc, "annotations.ai_recommendation"),
                "insight": rec_text[:200],
                "severity": base_severity,
                "confidence": confidence,
                "recommended_action": rec_text,
                "context": context,
            })

        if cost > 50000:
            annotations.append({
                "id": f"kpi-cost-{context}",
                "target_type": "kpi",
                "target_id": "imbalance_cost",
                "label": translate(loc, "annotations.imbalance_cost"),
                "insight": translate(loc, "annotations.cost_over_budget", cost=cost)[:200],
                "severity": "warn" if cost < 100000 else "crit",
                "confidence": confidence,
                "recommended_action": translate(loc, "annotations.cost_action"),
                "context": context,
            })

        risk_insight = str(
            structured.get("risk") or translate(loc, "annotations.risk_fallback", risk=risk)
        )[:200]
        annotations.append({
            "id": f"kpi-risk-{context}",
            "target_type": "kpi",
            "target_id": "risk",
            "label": translate(loc, "annotations.risk_score"),
            "insight": risk_insight,
            "severity": base_severity,
            "confidence": confidence,
            "recommended_action": primary_action if risk > 50 else "",
            "context": context,
        })

        mape_severity = "crit" if mape >= 20 else "warn" if mape >= 15 else "normal"
        annotations.append({
            "id": f"kpi-mape-base-{context}",
            "target_type": "kpi",
            "target_id": "live_mape",
            "label": translate(loc, "annotations.forecast_accuracy"),
            "insight": translate(loc, "annotations.mape_insight", mape=mape, mape_label=ml)[:200],
            "severity": mape_severity,
            "confidence": confidence,
            "recommended_action": translate(loc, "annotations.mape_action") if mape >= 15 else "",
            "context": context,
        })

        rule_count = len(rules)
        if rule_count > 0:
            annotations.append({
                "id": f"kpi-alerts-{context}",
                "target_type": "kpi",
                "target_id": "critical_alerts",
                "label": translate(loc, "annotations.active_alerts"),
                "insight": translate(loc, "annotations.alerts_insight", count=rule_count)[:200],
                "severity": "crit" if rule_count > 2 else "warn",
                "confidence": confidence,
                "recommended_action": str(rules[0].get("action") or primary_action or "")[:200],
                "context": context,
            })

        forecast_mw = latest.get("forecast_mw") or latest.get("total_daily_mw")
        if forecast_mw:
            band = translate(
                loc,
                "annotations.forecast_band_tight" if mape < 15 else "annotations.forecast_band_wide",
            )
            annotations.append({
                "id": f"kpi-forecast-{context}",
                "target_type": "kpi",
                "target_id": "forecast",
                "label": translate(loc, "annotations.production_forecast"),
                "insight": translate(loc, "annotations.forecast_insight", mw=forecast_mw, band=band)[:200],
                "severity": mape_severity,
                "confidence": confidence,
                "recommended_action": primary_action if mape >= 15 else "",
                "context": context,
            })

        actual_mw = latest.get("actual_mw")
        if actual_mw is not None:
            annotations.append({
                "id": f"kpi-production-{context}",
                "target_type": "kpi",
                "target_id": "production",
                "label": translate(loc, "annotations.actual_production"),
                "insight": translate(loc, "annotations.production_insight", mw=actual_mw)[:200],
                "severity": base_severity,
                "confidence": confidence,
                "recommended_action": "",
                "context": context,
            })

        if actual_mw is not None and forecast_mw:
            try:
                deviation = float(actual_mw) - float(forecast_mw)
            except (TypeError, ValueError):
                deviation = 0.0
            if abs(deviation) >= 1:
                note = translate(
                    loc,
                    "annotations.deviation_systematic"
                    if abs(deviation) > 5
                    else "annotations.deviation_ok",
                )
                annotations.append({
                    "id": f"kpi-deviation-{context}",
                    "target_type": "kpi",
                    "target_id": "forecast_deviation",
                    "label": translate(loc, "annotations.forecast_deviation"),
                    "insight": translate(
                        loc, "annotations.deviation_insight", delta=deviation, note=note
                    )[:200],
                    "severity": "warn" if abs(deviation) > 5 else "normal",
                    "confidence": confidence,
                    "recommended_action": (
                        translate(loc, "annotations.deviation_action") if abs(deviation) > 5 else ""
                    ),
                    "context": context,
                })

        return annotations

    def _recent_decisions(self, runs: list[dict[str, Any]], locale: str = "tr") -> list[dict[str, str]]:
        loc = normalize_locale(locale)
        decisions: list[dict[str, str]] = []
        for run in runs[:5]:
            risk = int(run.get("risk_score") or 0)
            mape = float(run.get("mape_percentage") or 0)
            cost = float(run.get("total_imbalance_cost_tl") or 0)
            risk_data = {
                "risk_score": risk,
                "total_imbalance_cost_tl": cost,
                "forecast_mw": run.get("forecast_mw") or run.get("total_daily_mw") or 0,
                "wind_speed_mps": run.get("wind_speed_mps") or 0,
            }
            stored_insight = str(run.get("ai_insight") or "").strip()
            stored_action = str(run.get("action_plan") or "").strip()
            if loc == "tr" and (stored_insight or stored_action):
                insight = stored_insight or translate(loc, "decisions.pipeline_done")
                action = stored_action or translate(loc, "decisions.continue_monitoring")
            else:
                insight = translate(loc, "decisions.run_insight", risk=risk, mape=mape, cost=cost)
                action = localize_action_plan(loc, risk_data, stored_action)
            if not insight and not action:
                continue
            decisions.append({
                "at": str(run.get("saved_at") or run.get("target_date") or "—"),
                "insight": insight[:200],
                "action": action,
            })
        return decisions

    def _build_technical(
        self,
        context: str,
        mape: float,
        risk: int,
        latest: dict[str, Any],
        confidence: int,
        locale: str = "tr",
    ) -> dict[str, Any]:
        loc = normalize_locale(locale)
        quality = (
            quality_label(loc, "high")
            if mape < 10
            else quality_label(loc, "medium")
            if mape < 18
            else quality_label(loc, "low")
        )
        data_hub = HealthMonitor().check_data_hub()
        degraded = sum(1 for v in data_hub.values() if v.get("status") != "ok")
        data_quality = (
            quality_label(loc, "high")
            if degraded == 0
            else quality_label(loc, "medium")
            if degraded <= 1
            else quality_label(loc, "low")
        )

        if context == "forecast":
            attribution = latest.get("model_attribution") or {}
            if attribution.get("features"):
                features = to_feature_importance(attribution)
                model = (
                    "Hybrid Physics + XGBoost (SHAP)"
                    if attribution.get("method") == "xgboost_tree_shap"
                    else "Hybrid Physics Model"
                )
            else:
                features = [
                    {"feature": "Wind speed (10m)", "weight": 0.34},
                    {"feature": "Turbine power curve", "weight": 0.28},
                    {"feature": "Hourly seasonality", "weight": 0.18},
                    {"feature": "SCADA lag correction", "weight": 0.12},
                    {"feature": "Capacity factor", "weight": 0.08},
                ]
                model = "Hybrid Physics + XGBoost v2"
            forecast_quality = f"MAPE {mape:.1f}% — {quality}"
        elif context == "risk":
            features = [
                {"feature": "Imbalance cost", "weight": 0.32},
                {"feature": "Forecast error (MAPE)", "weight": 0.26},
                {"feature": "PTF volatility", "weight": 0.18},
                {"feature": "Rule engine score", "weight": 0.14},
                {"feature": "Production drop signal", "weight": 0.10},
            ]
            model = "Risk Scoring Engine v1"
            forecast_quality = f"Risk {risk}/100 — {len(latest.get('rules', []))} rules"
        else:
            features = [
                {"feature": "API response time", "weight": 0.30},
                {"feature": "Data Hub uptime", "weight": 0.28},
                {"feature": "SCADA freshness", "weight": 0.22},
                {"feature": "EPİAŞ integration", "weight": 0.12},
                {"feature": "Pipeline job lag", "weight": 0.08},
            ]
            model = "System Observability Layer"
            forecast_quality = f"{len(data_hub) - degraded}/{len(data_hub)} sources healthy"

        return {
            "model": model,
            "confidence": confidence,
            "feature_importance": features,
            "forecast_quality": forecast_quality,
            "data_quality": data_quality,
        }

    def _recommendations(
        self, context: str, risk: int, mape: float, cost: float, locale: str = "tr"
    ) -> list[str]:
        return get_recommendations(locale, context)

    def _build_structured(
        self,
        context: str,
        name: str,
        risk: int,
        mape: float,
        cost: float,
        confidence: int,
        action_plan: str,
        ai_insight: str,
        top_rule: str,
        latest: dict[str, Any],
        report: dict[str, Any],
    ) -> dict[str, Any]:
        risk_label = "yüksek" if risk > 75 else "orta" if risk > 50 else "düşük"
        mape_label = "kabul edilebilir" if mape < 12 else "izlenmeli" if mape < 18 else "kritik"
        cost_fmt = f"{cost:,.0f} TL"

        builders = {
            "operations": self._structured_operations,
            "forecast": self._structured_forecast,
            "market": self._structured_market,
            "risk": self._structured_risk,
            "reports": self._structured_reports,
            "monitoring": self._structured_monitoring,
            "dashboard": self._structured_dashboard,
            "ai": self._structured_ai,
            "assets": self._structured_assets,
            "scenarios": self._structured_scenarios,
            "settings": self._structured_settings,
        }
        builder = builders.get(context, self._structured_dashboard)
        return builder(
            name, risk, mape, cost, confidence, risk_label, mape_label,
            cost_fmt, action_plan, ai_insight, top_rule, latest, report,
        )

    def _structured_operations(
        self, name, risk, mape, cost, confidence, risk_label, mape_label,
        cost_fmt, action_plan, ai_insight, top_rule, latest, report,
    ) -> dict[str, Any]:
        return {
            "title": f"{name} — Kontrol Odası Değerlendirmesi",
            "status_summary": (
                f"{name} santralinde operasyonel risk {risk}/100 seviyesinde ({risk_label}). "
                f"Canlı MAPE %{mape:.1f} ile üretim tahmini {mape_label} bandında. "
                f"Kontrol odası önceliği: {'alarm triyajı ve saha doğrulaması' if risk > 50 else 'rutin izleme ve vardiya devir teslimi'}."
            ),
            "analysis": (
                f"Son pipeline döngüsünde {len(latest.get('steps_completed', []))} adım tamamlandı. "
                f"{ai_insight[:220] if ai_insight else 'AI değerlendirmesi mevcut pipeline kaydından üretildi.'} "
                f"Dengesizlik maliyeti {cost_fmt} ile operasyonel baskı {'yükselmiş' if cost > 50000 else 'normal'} durumda."
            ),
            "risk": (
                f"Birincil risk: {top_rule} "
                f"Kurumsal risk skoru {risk}/100 — eskalasyon eşiği {'aşıldı' if risk > 75 else 'aşılmadı'}."
            ),
            "financial_impact": (
                f"Tahmini dengesizlik maliyeti {cost_fmt}. "
                f"{'Maliyet baskısı yüksek; pozisyon ve üretim planı gözden geçirilmeli.' if cost > 50000 else 'Maliyet normal operasyon bandında.'}"
            ),
            "operational_impact": (
                f"Üretim tahmin güvenilirliği {mape_label}. "
                f"Vardiya planı ve saha ekibi {'acil koordinasyon' if risk > 75 else 'standart protokol'} ile yönlendirilmeli."
            ),
            "recommended_action": action_plan,
            "alternative_action": (
                "Üretim marjını %5 artırarak dengesizlik riskini azaltın."
                if risk > 50
                else "Mevcut üretim planını koruyun; saatlik SCADA doğrulaması yeterli."
            ),
            "confidence": confidence,
        }

    def _structured_forecast(
        self, name, risk, mape, cost, confidence, risk_label, mape_label,
        cost_fmt, action_plan, ai_insight, top_rule, latest, report,
    ) -> dict[str, Any]:
        daily = latest.get("total_daily_mw", "—")
        return {
            "title": f"{name} — Tahmin Performans Analizi",
            "status_summary": (
                f"Hibrit tahmin modeli {name} için canlı MAPE %{mape:.1f} ({mape_label}). "
                f"Günlük toplam tahmin {daily} MWh. "
                f"Model güveni %{confidence} — planlama için {'yeterli' if mape < 15 else 'dikkatli marj gerekli'}."
            ),
            "analysis": (
                f"Fizik tabanlı üretim eğrisi ile XGBoost düzeltme katmanı birlikte çalışıyor. "
                f"{'Sistematik under-forecast eğilimi olabilir; saatlik bias analizi önerilir.' if mape > 15 else 'Saatlik tahmin bandı planlama toleransı içinde.'} "
                f"{ai_insight[:180] if ai_insight else ''}"
            ),
            "risk": (
                f"Tahmin sapması risk skoruna %{min(40, int(mape * 2))} oranında katkı yapıyor. "
                f"Yüksek sapma saatleri dengesizlik maliyetini artırır."
            ),
            "financial_impact": (
                f"Tahmin hatası kaynaklı tahmini maliyet maruziyeti {cost_fmt}. "
                f"MAPE her %1 artışta dengesizlik maliyeti yaklaşık %{min(8, int(mape / 2))} artabilir."
            ),
            "operational_impact": (
                f"Saha ekibi için üretim hedefi güven aralığı ±{max(3, int(mape / 3))}% olarak önerilir. "
                f"Düşük güvenli saatlerde turbin erişim planı revize edilmeli."
            ),
            "recommended_action": (
                "Model kalibrasyonu ve hava verisi çapraz kontrolü planlayın."
                if mape > 15
                else action_plan
            ),
            "alternative_action": "Kısa vadede fizik modeli ağırlığını artırarak XGBoost katkısını %20 azaltın.",
            "confidence": confidence,
        }

    def _structured_market(
        self, name, risk, mape, cost, confidence, risk_label, mape_label,
        cost_fmt, action_plan, ai_insight, top_rule, latest, report,
    ) -> dict[str, Any]:
        return {
            "title": f"{name} — Piyasa ve Dengesizlik Değerlendirmesi",
            "status_summary": (
                f"{name} için toplam dengesizlik maliyeti {cost_fmt}. "
                f"Piyasa maruziyeti {risk_label} seviyede. "
                f"PTF/SMF etkisi risk skoruna yansımış durumda."
            ),
            "analysis": (
                f"Saatlik dengesizlik dağılımı risk modülünden izlenebilir. "
                f"Tahmin doğruluğu (MAPE %{mape:.1f}) maliyet tahmininin güvenilirliğini doğrudan etkiler. "
                f"{ai_insight[:160] if ai_insight else ''}"
            ),
            "risk": f"Piyasa fiyat volatilitesi ve tahmin sapması birleşik risk oluşturuyor: {top_rule}",
            "financial_impact": (
                f"Dönem dengesizlik maliyeti {cost_fmt}. "
                f"{'Acil pozisyon optimizasyonu değerlendirilmeli.' if cost > 50000 else 'Maliyet bütçe bandında.'}"
            ),
            "operational_impact": "Yüksek maliyetli saatlerde üretim planı ile piyasa pozisyonu hizalanmalı.",
            "recommended_action": action_plan,
            "alternative_action": "Dengesizlik maliyetini düşürmek için düşük PTF saatlerinde üretim marjı artırılabilir.",
            "confidence": confidence,
        }

    def _structured_risk(
        self, name, risk, mape, cost, confidence, risk_label, mape_label,
        cost_fmt, action_plan, ai_insight, top_rule, latest, report,
    ) -> dict[str, Any]:
        rule_count = len(latest.get("rules", []))
        return {
            "title": f"{name} — Kurumsal Risk Panoraması",
            "status_summary": (
                f"{name} risk skoru {risk}/100 ({risk_label}). "
                f"{rule_count} aktif kural tetiklenmiş durumda. "
                f"Kritik uyarı sayısı: {report.get('critical_alerts_count', 0)}."
            ),
            "analysis": (
                f"Risk motoru; tahmin sapması (%{mape:.1f}), dengesizlik maliyeti ve kural ihlallerini birleştirir. "
                f"{ai_insight[:180] if ai_insight else 'Son pipeline değerlendirmesi risk skorunu güncelledi.'}"
            ),
            "risk": f"Öncelikli risk kalemi: {top_rule}",
            "financial_impact": f"Finansal maruziyet: {cost_fmt} dengesizlik maliyeti.",
            "operational_impact": (
                f"Operasyonel etki: {'Üretim planı ve saha koordinasyonu acil revize edilmeli.' if risk > 75 else 'Standart izleme yeterli.'}"
            ),
            "recommended_action": action_plan,
            "alternative_action": "Risk skorunu düşürmek için tahmin marjı ve pozisyon limitlerini sıkılaştırın.",
            "confidence": confidence,
        }

    def _structured_reports(
        self, name, risk, mape, cost, confidence, risk_label, mape_label,
        cost_fmt, action_plan, ai_insight, top_rule, latest, report,
    ) -> dict[str, Any]:
        exec_sum = report.get(
            "executive_summary",
            f"{name} için dönemsel operasyon özeti hazır.",
        )
        return {
            "title": f"{name} — Yönetici Dönem Özeti",
            "status_summary": (
                f"Bu dönemde {name} santrali {cost_fmt} dengesizlik maliyeti üretti. "
                f"Genel performans {'hedefin altında' if mape > 15 or cost > 50000 else 'beklenen bandda'}. "
                f"Yönetim kurulu için özet hazır."
            ),
            "analysis": (
                f"{exec_sum[:300]} "
                f"Teknik detay yerine finansal sonuç odaklı değerlendirme: "
                f"tahmin performansı {'iyileştirme gerektiriyor' if mape > 15 else 'kabul edilebilir'}."
            ),
            "risk": (
                f"Yönetici düzeyinde birincil endişe: "
                f"{'yüksek maliyet ve operasyonel belirsizlik' if risk > 50 or cost > 50000 else 'düşük düzeyde operasyonel risk'}."
            ),
            "financial_impact": (
                f"Toplam dengesizlik maliyeti {cost_fmt}. "
                f"Bu tutar dönem bütçesinin {'üzerinde baskı oluşturuyor' if cost > 100000 else 'tolerans sınırları içinde'}."
            ),
            "operational_impact": (
                "Saha operasyonları genel olarak sürdürülebilir; "
                f"{'acil müdahale planı devrede' if risk > 75 else 'ek kaynak tahsisi gerekmiyor'}."
            ),
            "recommended_action": (
                "Finans ekibiyle haftalık maliyet brifingi planlayın."
                if cost > 50000
                else "Mevcut operasyon planını sürdürün; aylık rapor yeterli."
            ),
            "alternative_action": "Dış denetim veya bağımsız performans değerlendirmesi talep edilebilir.",
            "confidence": confidence,
        }

    def _structured_monitoring(
        self, name, risk, mape, cost, confidence, risk_label, mape_label,
        cost_fmt, action_plan, ai_insight, top_rule, latest, report,
    ) -> dict[str, Any]:
        hub = HealthMonitor().check_data_hub()
        degraded = [k for k, v in hub.items() if v.get("status") != "ok"]
        return {
            "title": "Sistem ve Entegrasyon Sağlığı",
            "status_summary": (
                f"{len(hub) - len(degraded)}/{len(hub)} veri kaynağı sağlıklı. "
                f"{'Operasyonel veri akışı risk altında.' if degraded else 'Tüm entegrasyonlar aktif.'}"
            ),
            "analysis": (
                f"Data Hub durumu: {', '.join(f'{k}={v.get('status')}' for k, v in hub.items())}. "
                f"Pipeline audit ve job kuyruğu izleme sekmesinden erişilebilir."
            ),
            "risk": (
                f"Veri kaybı riski: {', '.join(degraded) if degraded else 'tespit edilmedi'}."
            ),
            "financial_impact": "Veri kesintisi durumunda tahmin ve maliyet hesapları güvenilirliğini yitirir.",
            "operational_impact": (
                f"{'SCADA veya EPİAŞ gecikmesi operasyon kararlarını etkileyebilir.' if degraded else 'Operasyon kararları güvenilir veriyle destekleniyor.'}"
            ),
            "recommended_action": (
                "Bozuk veri kaynağı için failover prosedürünü uygulayın."
                if degraded
                else "Rutin sağlık kontrolü yeterli."
            ),
            "alternative_action": "Yedek veri kaynağına geçiş senaryosunu test edin.",
            "confidence": confidence if not degraded else max(30, confidence - 20),
        }

    def _structured_dashboard(
        self, name, risk, mape, cost, confidence, risk_label, mape_label,
        cost_fmt, action_plan, ai_insight, top_rule, latest, report,
    ) -> dict[str, Any]:
        return {
            "title": f"Portföy Durumu — {name}",
            "status_summary": (
                f"{name} portföy görünümü: risk {risk}/100, dengesizlik maliyeti {cost_fmt}. "
                f"{'Kritik uyarı mevcut; öncelikli müdahale gerekli.' if risk > 75 else 'Operasyonel durum kontrol altında.'}"
            ),
            "analysis": ai_insight[:250] if ai_insight else f"Son {report.get('period_days', 7)} günlük analiz tamamlandı. MAPE %{mape:.1f}.",
            "risk": top_rule,
            "financial_impact": f"Dönem maliyeti {cost_fmt}.",
            "operational_impact": f"Üretim tahmin güvenilirliği {mape_label}.",
            "recommended_action": action_plan,
            "alternative_action": "Operasyon Merkezi'nde canlı KPI doğrulaması yapın.",
            "confidence": confidence,
        }

    def _structured_ai(
        self, name, risk, mape, cost, confidence, risk_label, mape_label,
        cost_fmt, action_plan, ai_insight, top_rule, latest, report,
    ) -> dict[str, Any]:
        return {
            "title": "AI Karar Destek Değerlendirmesi",
            "status_summary": ai_insight[:280] if ai_insight else f"{name} için AI değerlendirmesi üretildi.",
            "analysis": (
                f"Playbook/LLM kaynağı son pipeline'dan. "
                f"Girdi: risk={risk}, maliyet={cost_fmt}, MAPE=%{mape:.1f}."
            ),
            "risk": top_rule,
            "financial_impact": f"Önerilen aksiyonun maliyet etkisi: {cost_fmt} maruziyet bağlamında.",
            "operational_impact": action_plan,
            "recommended_action": action_plan,
            "alternative_action": "Öneriyi 24 saat içinde gerçekleşen aksiyonla karşılaştırın.",
            "confidence": confidence,
        }

    def _structured_assets(
        self, name, risk, mape, cost, confidence, risk_label, mape_label,
        cost_fmt, action_plan, ai_insight, top_rule, latest, report,
    ) -> dict[str, Any]:
        cap = latest.get("capacity_mw", "—")
        return {
            "title": f"Varlık Durumu — {name}",
            "status_summary": f"{name} ({cap} MW) operasyonel sağlık: {'dikkat gerektiriyor' if risk > 50 else 'iyi'}.",
            "analysis": f"Kapasite kullanımı ve performans detayı varlık API'sinden izlenir.",
            "risk": top_rule,
            "financial_impact": f"Dengesizlik maliyeti {cost_fmt}.",
            "operational_impact": "Bakım pencereleri düşük rüzgar tahminleriyle hizalanmalı.",
            "recommended_action": action_plan,
            "alternative_action": "Kapasite kullanım oranını haftalık izleyin.",
            "confidence": confidence,
        }

    def _structured_scenarios(
        self, name, risk, mape, cost, confidence, risk_label, mape_label,
        cost_fmt, action_plan, ai_insight, top_rule, latest, report,
    ) -> dict[str, Any]:
        return {
            "title": f"Senaryo Baz Durumu — {name}",
            "status_summary": f"Baz durum: risk {risk}/100, maliyet {cost_fmt}. What-if simülasyonları bu baz üzerinden kurgulanmalı.",
            "analysis": f"Son gerçekleşen MAPE %{mape:.1f}, günlük {latest.get('total_daily_mw', '—')} MWh.",
            "risk": top_rule,
            "financial_impact": f"Baz maliyet {cost_fmt}.",
            "operational_impact": "Fırtına ve düşük rüzgar senaryolarını ayrı çalıştırın.",
            "recommended_action": action_plan,
            "alternative_action": "Sonuçları risk panosuyla karşılaştırın.",
            "confidence": confidence,
        }

    def _structured_settings(
        self, name, risk, mape, cost, confidence, risk_label, mape_label,
        cost_fmt, action_plan, ai_insight, top_rule, latest, report,
    ) -> dict[str, Any]:
        return {
            "title": "Platform Yönetimi",
            "status_summary": "Kullanıcı, model ve entegrasyon ayarları bu alandan yönetilir.",
            "analysis": "LLM sağlayıcı, EPİAŞ/SCADA modları ve log seviyesi yapılandırılabilir.",
            "risk": "Yapılandırma değişiklikleri değişiklik penceresinde yapılmalı.",
            "financial_impact": "Doğrudan finansal etki yok.",
            "operational_impact": "Mock/canlı mod geçişleri operasyonu etkileyebilir.",
            "recommended_action": "API anahtarlarını periyodik rotate edin.",
            "alternative_action": "Yedek yapılandırma dosyasını güncel tutun.",
            "confidence": 90,
        }
