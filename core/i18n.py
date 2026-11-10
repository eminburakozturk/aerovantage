"""Merkezi locale katalogları — AI brifing, rapor ve export metinleri."""

from __future__ import annotations

from typing import Any

SUPPORTED_LOCALES = frozenset({"tr", "en", "de"})
DEFAULT_LOCALE = "tr"


def normalize_locale(value: str | None) -> str:
    if not value:
        return DEFAULT_LOCALE
    base = value.lower().split("-")[0]
    return base if base in SUPPORTED_LOCALES else DEFAULT_LOCALE


def translate(locale: str, key: str, **params: Any) -> str:
    catalog = _CATALOG.get(normalize_locale(locale), _CATALOG[DEFAULT_LOCALE])
    parts = key.split(".")
    current: Any = catalog
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return key
        current = current[part]
    if not isinstance(current, str):
        return key
    try:
        return current.format(**params)
    except KeyError:
        return current


def get_expert(locale: str, context: str) -> dict[str, str]:
    experts = _CATALOG[normalize_locale(locale)]["experts"]
    return experts.get(context, experts["dashboard"])


def get_recommendations(locale: str, context: str) -> list[str]:
    recs = _CATALOG[normalize_locale(locale)]["recommendations"]
    return list(recs.get(context, recs.get("operations", recs.get("dashboard", []))))


def risk_label(locale: str, risk: int) -> str:
    labels = _CATALOG[normalize_locale(locale)]["risk_labels"]
    if risk > 75:
        return labels["high"]
    if risk > 50:
        return labels["medium"]
    return labels["low"]


def mape_label(locale: str, mape: float) -> str:
    labels = _CATALOG[normalize_locale(locale)]["mape_labels"]
    if mape < 12:
        return labels["acceptable"]
    if mape < 18:
        return labels["watch"]
    return labels["critical"]


def build_localized_briefing_structured(
    locale: str,
    context: str,
    name: str,
    risk: int,
    mape: float,
    cost: float,
    confidence: int,
    action_plan: str,
    top_rule: str,
    latest: dict[str, Any],
) -> dict[str, Any]:
    loc = normalize_locale(locale)
    rl = risk_label(loc, risk)
    ml = mape_label(loc, mape)
    cost_fmt = f"{cost:,.0f} TL"
    steps = len(latest.get("steps_completed", []))
    return {
        "title": translate(loc, f"briefing.titles.{context}", name=name),
        "status_summary": translate(
            loc,
            "briefing.status_summary",
            name=name,
            risk=risk,
            risk_label=rl,
            mape=mape,
            mape_label=ml,
            context=context,
        ),
        "analysis": translate(
            loc,
            "briefing.analysis",
            steps=steps,
            cost=cost_fmt,
            elevated="yes" if cost > 50000 else "no",
        ),
        "risk": translate(loc, "briefing.risk", rule=top_rule, risk=risk, escalated="yes" if risk > 75 else "no"),
        "financial_impact": translate(
            loc,
            "briefing.financial_impact",
            cost=cost_fmt,
            high="yes" if cost > 50000 else "no",
        ),
        "operational_impact": translate(
            loc,
            "briefing.operational_impact",
            mape_label=ml,
            urgent="yes" if risk > 75 else "no",
        ),
        "recommended_action": action_plan or translate(loc, "briefing.default_action"),
        "alternative_action": translate(loc, "briefing.alternative_action", high_risk="yes" if risk > 50 else "no"),
        "confidence": confidence,
    }


def build_executive_summary(
    locale: str,
    *,
    asset_id: str,
    period_days: int,
    run_count: int,
    total_imbalance_cost_tl: float,
    average_mape: float,
    critical_alerts_count: int,
) -> str:
    loc = normalize_locale(locale)
    if run_count == 0:
        return translate(loc, "reporting.no_data", asset_id=asset_id, period_days=period_days)

    if critical_alerts_count > 0:
        posture_key = "critical_alerts"
    elif average_mape > 15.0:
        posture_key = "low_accuracy"
    elif total_imbalance_cost_tl > 5000.0:
        posture_key = "high_cost"
    else:
        posture_key = "normal"

    posture = translate(loc, f"reporting.posture.{posture_key}")
    return translate(
        loc,
        "reporting.summary",
        asset_id=asset_id,
        period_days=period_days,
        run_count=run_count,
        cost=f"{total_imbalance_cost_tl:,.2f}",
        mape=f"{average_mape:.2f}",
        critical_alerts=critical_alerts_count,
        posture=posture,
    )


def build_executive_conclusion(
    locale: str,
    *,
    posture_key: str,
    action: str,
    cost: float,
    risk: float,
    dq: float,
) -> str:
    loc = normalize_locale(locale)
    posture = translate(loc, f"reporting.posture.{posture_key}")
    return translate(
        loc,
        "reporting.conclusion",
        posture=posture,
        action=action or translate(loc, "reporting.insufficient"),
        cost=f"{cost:,.2f}",
        risk=f"{risk:.0f}",
        dq=f"{dq:.0f}" if dq else "—",
    )


def reporting_level_label(locale: str, level: str) -> str:
    loc = normalize_locale(locale)
    key = {
        "ok": "reporting.level_ok",
        "normal": "reporting.level_ok",
        "warn": "reporting.level_warn",
        "warning": "reporting.level_warn",
        "crit": "reporting.level_crit",
        "critical": "reporting.level_crit",
    }.get(level.lower(), "reporting.level_ok")
    return translate(loc, key)


def export_labels(locale: str) -> dict[str, str]:
    return dict(_CATALOG[normalize_locale(locale)]["export"])


_HIGH_IMBALANCE_COST_TL = 3_000.0
_LOW_IMBALANCE_COST_TL = 1_500.0
_HIGH_RISK_SCORE = 50
_LOW_RISK_SCORE = 30


def select_playbook_id(risk_data: dict[str, Any]) -> str:
    """Risk metriklerine göre playbook maddesi seçer."""
    wind_speed = float(risk_data.get("wind_speed_mps", 0) or 0)
    risk_score = int(risk_data.get("risk_score", 0) or 0)
    total_cost = float(risk_data.get("total_imbalance_cost_tl", 0) or 0)
    forecast_mw = float(risk_data.get("forecast_mw", 0) or 0)

    if wind_speed >= 15 and (total_cost > _HIGH_IMBALANCE_COST_TL or risk_score > _HIGH_RISK_SCORE):
        return "storm_high_cost"
    if wind_speed < 4 and total_cost < _LOW_IMBALANCE_COST_TL and risk_score < _LOW_RISK_SCORE:
        return "low_wind_maintenance"
    if risk_score > _HIGH_RISK_SCORE or total_cost > _HIGH_IMBALANCE_COST_TL:
        return "elevated_risk"
    if forecast_mw <= 0:
        return "low_wind_maintenance"
    return "default"


def playbook_texts(locale: str, entry_id: str) -> dict[str, str]:
    loc = normalize_locale(locale)
    catalog = _CATALOG[loc]["playbook"]
    entry = catalog.get(entry_id) or catalog["default"]
    return {
        "title": str(entry["title"]),
        "message": str(entry["message"]),
        "action": str(entry["action"]),
    }


def playbook_insight(locale: str, entry_id: str) -> str:
    texts = playbook_texts(locale, entry_id)
    return translate(locale, "playbook.insight_fmt", title=texts["title"], message=texts["message"])


def localize_action_plan(locale: str, risk_data: dict[str, Any], stored: str | None = None) -> str:
    """Kayıtlı TR aksiyon yerine güncel dile göre playbook aksiyonu döner."""
    entry_id = select_playbook_id(risk_data)
    return playbook_texts(locale, entry_id)["action"] or (stored or translate(locale, "briefing.default_action"))


def ai_fallback_prefix(locale: str) -> str:
    return translate(locale, "playbook.fallback_prefix")


def localize_ai_insight(locale: str, risk_data: dict[str, Any], stored: str | None = None) -> str:
    """Kayıtlı TR AI insight metnini güncel dile göre yeniden üretir."""
    loc = normalize_locale(locale)
    entry_id = select_playbook_id(risk_data)
    insight = playbook_insight(loc, entry_id)
    text = (stored or "").strip()
    if text.startswith("Sistem uyarısı:") or "AI servisine ulaşılamadı" in text:
        return f"{ai_fallback_prefix(loc)} {insight}"
    return insight


_ALERT_CRITICAL = 75
_ALERT_WARNING = 50
_ALERT_MAPE_WARNING = 15.0


def run_is_proxy_ground_truth(run: dict[str, Any]) -> bool:
    """Pipeline kaydından simülasyon / proxy ground-truth bayrağını çıkarır."""
    scada = run.get("scada_source") or run.get("scada") or {}
    if not isinstance(scada, dict):
        scada = {}
    mode = str(scada.get("mode") or "")
    live = scada.get("live")
    if live is True or live == "true":
        return False
    if mode in {"simulated", "mock", "simulation", "simulated_from_epias"}:
        return True
    if scada.get("source") == "simulated_from_epias":
        return True
    if run.get("evaluation_mode") == "simulation":
        return True
    if run.get("mape_informational") is True:
        return True
    if run.get("ground_truth_mode") in {"simulated", "mock", "simulation"}:
        return True
    return False


def compose_alert_message(
    locale: str,
    *,
    risk_score: int,
    mape_percentage: float,
    proxy: bool,
) -> tuple[str, str]:
    """Risk/MAPE/proxy koşullarından (severity, message) üretir."""
    loc = normalize_locale(locale)
    risk = int(risk_score)
    mape = float(mape_percentage)

    if risk > _ALERT_CRITICAL:
        risk_severity = "CRITICAL"
        risk_message = translate(loc, "alerts.risk_critical")
    elif risk > _ALERT_WARNING:
        risk_severity = "WARNING"
        risk_message = translate(loc, "alerts.risk_warning")
    else:
        risk_severity = "INFO"
        risk_message = translate(loc, "alerts.risk_info")

    mape_high = mape > _ALERT_MAPE_WARNING
    if proxy:
        mape_message = translate(loc, "alerts.mape_sim", mape=mape)
    else:
        mape_message = translate(loc, "alerts.mape_live", mape=mape)

    if risk_severity == "CRITICAL":
        severity = "CRITICAL"
        message = f"{risk_message} | {mape_message}" if mape_high else risk_message
    elif risk_severity == "WARNING":
        severity = "WARNING"
        message = f"{risk_message} | {mape_message}" if mape_high else risk_message
    elif mape_high:
        severity = "WARNING"
        message = mape_message
    else:
        severity = "INFO"
        message = risk_message

    if proxy:
        if severity == "CRITICAL":
            severity = "WARNING"
        if mape_high and risk_severity == "INFO":
            severity = "INFO"
        message = f"{translate(loc, 'alerts.sim_prefix')} {message}"

    return severity, message


def build_localized_notifications(
    locale: str,
    *,
    alert_status: dict[str, Any],
    action_plan: str,
    risk_score: int,
) -> list[dict[str, str]]:
    """Uyarı + aksiyon planından locale'e göre bildirim listesi üretir."""
    loc = normalize_locale(locale)
    notifications: list[dict[str, str]] = []

    alert_severity = str(alert_status.get("severity", "INFO")).upper()
    if alert_severity not in {"INFO", "WARNING", "CRITICAL"}:
        alert_severity = "INFO"
    alert_message = str(alert_status.get("message", "")).strip()
    if alert_message:
        notifications.append(
            {
                "level": alert_severity,
                "title": translate(loc, "alerts.title_operational"),
                "message": alert_message,
            }
        )

    if action_plan:
        action_level = (
            "CRITICAL" if risk_score > _ALERT_CRITICAL else "WARNING" if risk_score > _ALERT_WARNING else "INFO"
        )
        notifications.append(
            {
                "level": action_level,
                "title": translate(loc, "alerts.title_action"),
                "message": action_plan,
            }
        )

    if not notifications:
        notifications.append(
            {
                "level": "INFO",
                "title": translate(loc, "alerts.title_status"),
                "message": translate(loc, "alerts.no_active"),
            }
        )

    return notifications


def localize_pipeline_run(locale: str, run: dict[str, Any]) -> dict[str, Any]:
    """Pipeline geçmiş kaydındaki AI/rule/bildirim metinlerini locale'e çevirir."""
    loc = normalize_locale(locale)
    if loc == DEFAULT_LOCALE:
        return run
    out = dict(run)
    risk_score = int(run.get("risk_score") or 0)
    mape_percentage = float(run.get("mape_percentage") or 0)
    risk_data = {
        "risk_score": risk_score,
        "total_imbalance_cost_tl": run.get("total_imbalance_cost_tl", 0),
        "forecast_mw": run.get("total_daily_mw") or run.get("forecast_mw") or 0,
        "wind_speed_mps": run.get("wind_speed_mps", 0),
    }
    if run.get("ai_insight"):
        out["ai_insight"] = localize_ai_insight(loc, risk_data, str(run.get("ai_insight")))
    if run.get("action_plan"):
        out["action_plan"] = localize_action_plan(loc, risk_data, str(run.get("action_plan")))
    rules = run.get("rules")
    if isinstance(rules, list):
        simulation = run_is_proxy_ground_truth(run)
        out["rules"] = [
            localize_rule(loc, rule, simulation=simulation) for rule in rules if isinstance(rule, dict)
        ]

    proxy = run_is_proxy_ground_truth(run)
    severity, message = compose_alert_message(
        loc,
        risk_score=risk_score,
        mape_percentage=mape_percentage,
        proxy=proxy,
    )
    alert_status = run.get("alert_status")
    if isinstance(alert_status, dict):
        out["alert_status"] = {**alert_status, "severity": severity, "message": message}
    else:
        out["alert_status"] = {"severity": severity, "message": message}

    out["notifications"] = build_localized_notifications(
        loc,
        alert_status=out["alert_status"],
        action_plan=str(out.get("action_plan") or ""),
        risk_score=risk_score,
    )
    return out


def build_scenario_summary(
    locale: str,
    *,
    name: str,
    wind_adjustment_pct: float,
    ptf_adjustment_pct: float,
    turbines_down: int,
    baseline_forecast_mw: float,
    adjusted_forecast_mw: float,
    baseline_cost_tl: float,
    adjusted_cost_tl: float,
    baseline_risk_score: int,
    adjusted_risk_score: int,
) -> str:
    return translate(
        locale,
        "scenario.summary",
        name=name,
        wind=f"{wind_adjustment_pct:+.0f}",
        ptf=f"{ptf_adjustment_pct:+.0f}",
        turbines=turbines_down,
        baseline_mw=f"{baseline_forecast_mw:.1f}",
        adjusted_mw=f"{adjusted_forecast_mw:.1f}",
        baseline_cost=f"{baseline_cost_tl:,.0f}",
        adjusted_cost=f"{adjusted_cost_tl:,.0f}",
        baseline_risk=baseline_risk_score,
        adjusted_risk=adjusted_risk_score,
    )


def rule_texts(locale: str, rule_id: str, *, simulation: bool = False) -> dict[str, str]:
    loc = normalize_locale(locale)
    rules = _CATALOG[loc]["rules"]
    entry = rules.get(rule_id) or rules["nominal_operations"]
    variant = entry["sim"] if simulation and "sim" in entry else entry["live"]
    return {"message": str(variant["message"]), "action": str(variant["action"])}


def localize_rule(locale: str, rule: dict[str, Any], *, simulation: bool = False) -> dict[str, Any]:
    """Kural kaydını dil katalogundan yeniden üretir (rule_id ile)."""
    rule_id = str(rule.get("rule_id") or "nominal_operations")
    texts = rule_texts(locale, rule_id, simulation=simulation)
    out = dict(rule)
    out["message"] = texts["message"]
    out["action"] = texts["action"]
    return out


def quality_label(locale: str, level: str) -> str:
    return translate(locale, f"quality.{level}")


_CATALOG: dict[str, dict[str, Any]] = {
    "tr": {
        "experts": {
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
        },
        "recommendations": {
            "operations": [
                "Operasyonel akıştaki son 5 olayı shift defterine işleyin.",
                "Aktif alarm ve kural eşiklerini kontrol odası protokolüyle doğrulayın.",
                "SCADA ve tahmin sapması arasında saatlik çapraz kontrol yapın.",
            ],
            "forecast": [
                "MAPE %15 üzerindeyse model kalibrasyon penceresi planlayın.",
                "Hava tahmini ile üretim eğrisi arasındaki bias'ı saatlik inceleyin.",
            ],
            "market": [
                "Yüksek dengesizlik maliyetli saatleri PTF eğrisiyle eşleştirin.",
                "Günlük maliyet özetini finans ekibiyle paylaşın.",
            ],
            "risk": [
                "Risk skoru 75 üzerindeyse üst yönetim brifingi tetikleyin.",
                "Finansal ve üretim riskini ayrı panellerde izleyin.",
            ],
            "ai": [
                "Bekleyen aksiyonları öncelik sırasına göre onaylayın veya erteleyin.",
                "Düşük güvenli önerileri saha ekibiyle doğrulayın.",
            ],
            "dashboard": [
                "Kritik uyarıları Operasyon Merkezi'nde triyaj edin.",
                "Yönetici özetini günlük brifinge ekleyin.",
            ],
            "reports": ["Yönetici PDF raporunu haftalık arşivleyin."],
            "monitoring": ["API gecikme ve hata oranını saatlik kontrol edin."],
            "assets": ["Santral sağlık skorlarını haftalık gözden geçirin."],
            "scenarios": ["What-if sonuçlarını karar defterine işleyin."],
            "settings": ["API anahtarlarını periyodik rotate edin."],
        },
        "risk_labels": {"high": "yüksek", "medium": "orta", "low": "düşük"},
        "mape_labels": {"acceptable": "kabul edilebilir", "watch": "izlenmeli", "critical": "kritik"},
        "briefing": {
            "default_action": "Standart izleme protokolü sürdürülsün.",
            "no_rule": "Aktif kritik kural tespit edilmedi.",
            "titles": {
                "dashboard": "{name} — Yönetici Özeti",
                "operations": "{name} — Kontrol Odası Değerlendirmesi",
                "forecast": "{name} — Tahmin Performans Analizi",
                "market": "{name} — Piyasa Değerlendirmesi",
                "risk": "{name} — Risk Değerlendirmesi",
                "ai": "{name} — Karar Merkezi",
                "reports": "{name} — Rapor Özeti",
                "assets": "{name} — Varlık Durumu",
                "monitoring": "{name} — Sistem İzleme",
                "scenarios": "{name} — Senaryo Analizi",
                "settings": "{name} — Platform Yapılandırması",
            },
            "status_summary": (
                "{name} için operasyonel risk {risk}/100 ({risk_label}). "
                "MAPE %{mape:.1f} ({mape_label}). Bağlam: {context}."
            ),
            "analysis": "Son pipeline {steps} adım tamamladı. Dengesizlik maliyeti {cost}.",
            "risk": "Birincil risk: {rule} Kurumsal risk {risk}/100.",
            "financial_impact": "Tahmini dengesizlik maliyeti {cost}.",
            "operational_impact": "Tahmin güvenilirliği {mape_label}.",
            "alternative_action": "Alternatif aksiyon değerlendirmesi önerilir.",
        },
        "annotations": {
            "primary_action": "Önerilen aksiyon",
            "alternative_action": "Alternatif aksiyon",
            "rule_alert": "Kural uyarısı",
            "ai_recommendation": "AI tavsiyesi",
            "imbalance_cost": "Dengesizlik maliyeti",
            "risk_score": "Risk skoru",
            "forecast_accuracy": "Tahmin doğruluğu",
            "active_alerts": "Aktif uyarılar",
            "production_forecast": "Üretim tahmini",
            "actual_production": "Gerçekleşen üretim",
            "forecast_deviation": "Tahmin sapması",
            "cost_over_budget": "Toplam maliyet {cost:,.0f} TL — bütçe bandının üzerinde.",
            "cost_action": "Pozisyon ve üretim planını maliyet baskısına göre revize edin.",
            "risk_fallback": "Risk skoru {risk}/100.",
            "mape_insight": "Canlı MAPE %{mape:.1f} — {mape_label}.",
            "mape_action": "Saatlik bias analizi çalıştırın ve tahmin marjını güncelleyin.",
            "alerts_insight": "{count} kural tetiklendi — triyaj ve saha doğrulaması gerekli.",
            "forecast_insight": "Tahmin {mw} MW — {band}.",
            "forecast_band_tight": "güven aralığı dar",
            "forecast_band_wide": "marj artırılmalı",
            "production_insight": "Güncel üretim {mw} MW.",
            "deviation_insight": "Gerçekleşen-tahmin farkı {delta:+.1f} MW — {note}.",
            "deviation_systematic": "sistematik sapma olabilir",
            "deviation_ok": "tolerans içinde",
            "deviation_action": "Sapma kök neden analizi başlatın.",
            "verify_rule": "Kuralı doğrula ve izlemeye devam et.",
        },
        "scenario": {
            "summary": (
                "{name} için senaryo: rüzgar {wind}%, PTF {ptf}%, {turbines} türbin devre dışı. "
                "Tahmin {baseline_mw} → {adjusted_mw} MW, maliyet {baseline_cost} → {adjusted_cost} TL, "
                "risk {baseline_risk} → {adjusted_risk}."
            ),
        },
        "monitoring": {
            "log_empty": "Log dosyası henüz oluşturulmadı. API aktif.",
            "daily_pipeline": "Günlük Pipeline",
            "kpi_refresh": "KPI Yenileme",
            "kpi_schedule": "Her 30 dakika",
        },
        "alerts": {
            "title_operational": "Operasyonel Uyarı",
            "title_action": "Önerilen Aksiyon",
            "title_status": "Durum",
            "no_active": "Aktif bildirim yok.",
            "sim_prefix": "[Simülasyon]",
            "risk_critical": "Kritik dengesizlik riski! Acil pozisyon kontrolü önerilir.",
            "risk_warning": "Yüksek dengesizlik riski tespit edildi.",
            "risk_info": "Risk seviyesi operasyonel sınırlar içinde.",
            "mape_sim": (
                "Simülasyon MAPE %{mape:.1f} (bilgi). "
                "Ground truth EPİAŞ türevi/mock — model kalibrasyonu için kullanılmaz."
            ),
            "mape_live": (
                "Düşük tahmin isabeti (MAPE: %{mape:.1f}). "
                "Model güncellemesi gerekebilir."
            ),
        },
        "playbook": {
            "fallback_prefix": "Sistem uyarısı: AI servisine ulaşılamadı, otomatik playbook devrede.",
            "insight_fmt": "AI Analizi: [{title}] {message}",
            "storm_high_cost": {
                "title": "Lessons Learned",
                "message": "Geçmiş fırtınalarda türbin pitch açıları geç uyarlandı, üretim durduruldu. Aksiyon: Pitch kontrol sistemlerini manuel denetle.",
                "action": "Pitch kontrol sistemlerini manuel denetle",
            },
            "low_wind_maintenance": {
                "title": "Playbook",
                "message": "Düşük rüzgar senaryosu. Planlı bakım çalışmaları için uygun zaman penceresi.",
                "action": "Planlı bakım penceresini değerlendir",
            },
            "elevated_risk": {
                "title": "Risk Uyarısı",
                "message": "Dengesizlik maliyeti yükseliyor. Gün içi üretim tahmini ile gerçekleşen değerleri saatlik izleyin; gerekirse operasyon ekibini bilgilendirin.",
                "action": "Pozisyonu azalt",
            },
            "default": {
                "title": "Operasyonel Durum",
                "message": "Parametreler normal aralıkta. Standart izleme prosedürüne devam edin.",
                "action": "Standart izleme prosedürüne devam et",
            },
        },
        "rules": {
            "critical_risk": {
                "live": {
                    "message": "Risk skoru kritik eşiği aştı.",
                    "action": "Acil pozisyon kontrolü başlat",
                },
                "sim": {
                    "message": "Simülasyon risk skoru yüksek (proxy ground truth).",
                    "action": "Ground truth canlı SCADA olmadan pozisyon alarmı üretme",
                },
            },
            "elevated_risk": {
                "live": {
                    "message": "Risk skoru yükselmiş durumda.",
                    "action": "Saatlik üretim sapmasını izle",
                },
                "sim": {
                    "message": "Simülasyon risk skoru yükselmiş.",
                    "action": "Operational MW kaynağını doğrula",
                },
            },
            "high_mape": {
                "live": {
                    "message": "Tahmin isabeti düşük (MAPE > %15).",
                    "action": "Forecast modelini kalibre et",
                },
                "sim": {
                    "message": "Simülasyon MAPE yüksek — model başarısızlığı değil, proxy actual.",
                    "action": "MAPE bilgisel; model kalibrasyonu için canlı SCADA bekleniyor",
                },
            },
            "high_imbalance_cost": {
                "live": {
                    "message": "Dengesizlik maliyeti yükseldi.",
                    "action": "Pozisyonu gözden geçir",
                },
                "sim": {
                    "message": "Simülasyon dengesizlik maliyeti yüksek (proxy).",
                    "action": "Maliyet simülasyon bağlamında yorumla",
                },
            },
            "nominal_operations": {
                "live": {
                    "message": "Operasyonel parametreler normal aralıkta.",
                    "action": "Standart izlemeye devam et",
                },
                "sim": {
                    "message": "Operasyonel parametreler normal aralıkta.",
                    "action": "Standart izlemeye devam et",
                },
            },
        },
        "quality": {"high": "yüksek", "medium": "orta", "low": "düşük"},
        "decisions": {
            "pipeline_done": "Pipeline değerlendirmesi tamamlandı.",
            "continue_monitoring": "İzleme devam",
            "run_insight": "Risk {risk}/100 · MAPE %{mape:.1f} · maliyet {cost:,.0f} TL.",
        },
        "reporting": {
            "no_data": (
                "{asset_id} santrali için son {period_days} kayıt içinde analiz edilebilir "
                "pipeline verisi bulunamadı."
            ),
            "summary": (
                "{asset_id} için son {period_days} günlük dönemde {run_count} kayıt analiz edildi. "
                "Toplam dengesizlik maliyeti {cost} TL, ortalama MAPE %{mape}, "
                "kritik uyarı sayısı {critical_alerts}. Genel durum: {posture}."
            ),
            "posture": {
                "critical_alerts": "kritik uyarılar mevcut; acil gözden geçirme önerilir",
                "low_accuracy": "tahmin isabeti düşük; model kalibrasyonu değerlendirilmelidir",
                "high_cost": "dengesizlik maliyeti yükselmiş; pozisyon yönetimi gözden geçirilmelidir",
                "normal": "operasyonel sınırlar içinde; rutin izleme yeterlidir",
            },
            "conclusion": (
                "Sonuç: {posture} Öncelikli aksiyon: {action}. "
                "Dönem maliyeti {cost} TL, ortalama risk {risk}/100, DQ skoru {dq}."
            ),
            "insufficient": "Yeterli veri yok",
            "ai_brief_title": "AI Yönetici Brifingi",
            "score_financial": "Finansal Sağlık",
            "score_operational": "Operasyonel Sağlık",
            "score_forecast": "Tahmin Güveni",
            "score_data": "Veri Kalitesi",
            "score_model": "Model Güvenilirliği",
            "score_risk": "Risk Durumu",
            "score_alerts": "Kritik Alarmlar",
            "score_overall": "Genel Sağlık",
            "priority_high": "Yüksek",
            "priority_medium": "Orta",
            "priority_low": "Düşük",
            "trend_up": "Yükseliş",
            "trend_down": "Düşüş",
            "trend_flat": "Yatay",
            "status_open": "Açık",
            "level_warn": "Uyarı",
            "level_crit": "Kritik",
            "level_ok": "Normal",
            "sim_flag": "Simülasyon / bilgi amaçlı",
            "weekly_summary": (
                "{asset_id} için {weeks} haftalık dönem analiz edildi. "
                "Toplam {runs} pipeline kaydı."
            ),
            "weekly_empty": "{asset_id} için haftalık analiz edilebilir kayıt bulunamadı.",
            "type_executive": "Yönetici Raporu",
            "type_operational": "Operasyon Raporu",
            "type_forecast": "Tahmin Raporu",
            "type_financial": "Finansal Rapor",
            "type_risk": "Risk Raporu",
            "type_technical": "Teknik Rapor",
            "adaptive_hint": "Çalışma alanı ({workspace}) için önerilen rapor: {report_type}.",
            "changes_insufficient": "Karşılaştırma için yeterli dönem kaydı yok.",
            "changes_summary": (
                "Son döneme göre maliyet %{cost_delta}, MAPE {mape_delta}, risk {risk_delta}. "
                "Yeni kritik alarm: {new_alerts}, kapanan: {closed_alerts}."
            ),
            "ask_mape": "Ortalama MAPE %{mape} ({label}). Son kayıt MAPE %{latest}.",
            "ask_mape_why": (
                "MAPE neden değişti: önceki dönem ort. %{prior} -> son dönem ort. %{recent} "
                "(delta {mape_delta} puan). Dönem ortalaması %{mape} ({label}), son kayıt %{latest}. "
                "Olası sürücüler: {drivers} İzlenmesi gereken: {watch}. Dönem özeti: {changes}"
            ),
            "ask_cost": "Toplam dengesizlik maliyeti {total} TL (trend: {trend}). Kaçınılabilir tahmin: {avoidable} TL.",
            "ask_cost_why": (
                "Maliyet neden değişti: toplam {total} TL (trend: {trend}), kaçınılabilir {avoidable} TL; "
                "önceki döneme göre maliyet değişimi %{cost_delta}. Olası sürücüler: {drivers} "
                "Dönem karşılaştırması: {changes}"
            ),
            "ask_risk": "Ortalama risk {score}/100 ({level}). Ön plandaki kural: {rule}.",
            "ask_risk_why": (
                "Risk neden değişti: ortalama {score}/100 ({level}), öne çıkan kural: {rule}; "
                "önceki döneme göre risk değişimi {risk_delta}. Olası sürücüler: {drivers} "
                "Dönem karşılaştırması: {changes}"
            ),
            "ask_action": "Önerilen aksiyon: {action}",
            "ask_default": "Özet: {summary} Sonuç: {conclusion}",
            "ask_why_default": (
                "Bu soruya göre en net dönem sinyali: {changes} "
                "Olası sürücüler: {drivers} Özet: {summary} Sonuç: {conclusion}"
            ),
            "ask_off_topic": (
                "Bu soru rapor verisiyle ilgili değil. "
                "MAPE, maliyet, risk veya aksiyon hakkında sorun."
            ),
            "ask_driver_up": "Yükselen KPI'lar ({items}).",
            "ask_driver_down": "Gerileyen KPI'lar ({items}).",
            "ask_driver_rule": "Öne çıkan kural: {rule}.",
            "ask_driver_simulation": "Simülasyon/sentetik veri etkisi olası.",
            "ask_driver_event": "Üst olay: {event}.",
            "ask_driver_alerts": "Yeni kritik alarm artışı: {count}.",
            "ask_driver_none": "Pakette net ek sürücü sinyali yok; dönem delta ve son kayıtları izleyin.",
            "type_focus_executive": "Finans, risk, tahmin ve aksiyon odaklı yönetici görünümü.",
            "type_focus_operational": "Alarm, kural, saha aksiyonları ve operasyonel risk odaklı görünüm.",
            "type_focus_forecast": "MAPE, model güveni ve tahmin trendi odaklı görünüm.",
            "type_focus_financial": "Dengesizlik maliyeti, trend ve portföy kıyası odaklı görünüm.",
            "type_focus_risk": "Risk skoru, kurallar ve önerilen aksiyonlar odaklı görünüm.",
            "type_focus_technical": "Veri kalitesi, model güvenilirliği ve teknik metrik odaklı görünüm.",
            "pack_title": "{report_type} — {asset_id}",
            "portfolio_fallback": (
                "Portföy ({count} santral): toplam maliyet {cost:,.0f} TL, "
                "ort. MAPE %{mape:.1f}, kritik uyarı {critical}."
            ),
        },
        "export": {
            "pdf_title": "AeroVantage — Yönetici Raporu",
            "pdf_doc_type": "Yönetici Operasyonel Zeka Raporu",
            "pdf_brand": "AeroVantage",
            "pdf_tagline": "Operasyonel Zeka",
            "section_meta": "Belge Bilgileri",
            "section_kpis": "Temel Performans Göstergeleri",
            "section_summary": "Yönetici Özeti",
            "section_ai_brief": "AI Yönetici Brifingi",
            "section_scorecards": "Skor Kartları",
            "section_financial": "Finansal Zeka",
            "section_forecast": "Tahmin Zekası",
            "section_operational": "Operasyonel Zeka",
            "section_risk": "Risk Zekası",
            "section_data": "Veri Zekası",
            "section_model": "Model Zekası",
            "section_recommendations": "AI Önerileri",
            "section_actions": "Aksiyon Merkezi",
            "section_trends": "Trend Analizi",
            "section_benchmark": "Kıyaslama",
            "section_conclusion": "Yönetici Sonuç",
            "section_changes": "Değişim Özeti",
            "plant": "Santral",
            "period": "Dönem",
            "period_days": "gün",
            "cost": "Toplam dengesizlik maliyeti",
            "mape": "Ortalama MAPE",
            "critical_alerts": "Kritik uyarı sayısı",
            "generated_at": "Üretim zamanı (UTC)",
            "document_id": "Belge no",
            "locale": "Dil",
            "metric": "Gösterge",
            "value": "Değer",
            "status": "Durum",
            "status_summary": "Durum özeti",
            "priority": "Öncelik",
            "action": "Aksiyon",
            "owner": "Sorumlu",
            "top_event": "Öne çıkan olay",
            "top_risk": "Öne çıkan risk",
            "avg_daily_cost": "Günlük ortalama maliyet",
            "cost_trend": "Maliyet trendi",
            "avoidable_cost": "Kaçınılabilir maliyet (tahmini)",
            "revenue_risk": "Gelir riski",
            "latest_mape": "Son MAPE",
            "confidence": "Güven",
            "critical_count": "Kritik alarm",
            "warning_count": "Uyarı",
            "active_rules": "Aktif kurallar",
            "pipeline_runs": "Pipeline kayıtları",
            "avg_risk": "Ortalama risk",
            "latest_risk": "Son risk",
            "max_risk": "Maks. risk",
            "top_rule": "Öne çıkan kural",
            "trust_score": "Güven skoru",
            "latest_dq": "Son DQ skoru",
            "gate": "Kapı",
            "drift": "Drift",
            "model_version": "Model sürümü",
            "physics_fallback": "Physics fallback",
            "coverage": "Kapsama",
            "cost_spark": "Maliyet trendi",
            "mape_spark": "MAPE trendi",
            "risk_spark": "Risk trendi",
            "prior_avg_cost": "Önceki dönem ort. maliyet",
            "recent_avg_cost": "Son dönem ort. maliyet",
            "vs_prior_pct": "Önceki döneme göre %",
            "portfolio_mape": "Portföy ort. MAPE",
            "portfolio_cost": "Portföy ort. maliyet",
            "changes_summary": "Değişim özeti",
            "report_type": "Rapor tipi",
            "confidential": "Gizli — Dahili kullanım içindir. İzinsiz dağıtılmaz.",
            "page": "Sayfa",
            "footer_brand": "AeroVantage Operasyonel Zeka",
            "csv_field": "Alan",
            "csv_value": "Değer",
            "excel_executive": "Yönetici",
            "excel_history": "Geçmiş",
            "excel_sections": "Bölümler",
        },
    },
    "en": {
        "experts": {
            "dashboard": {"title": "Executive Assistant", "subtitle": "Portfolio and executive decision support"},
            "operations": {"title": "Operations Assistant", "subtitle": "Control room and live operations"},
            "forecast": {"title": "Forecast Analyst", "subtitle": "Production forecast and model performance"},
            "market": {"title": "Market Analyst", "subtitle": "PTF, SMF and imbalance cost"},
            "risk": {"title": "Risk Analyst", "subtitle": "Risk score and exposure management"},
            "ai": {"title": "Decision Center", "subtitle": "Pending actions and approval flow"},
            "reports": {"title": "Executive Assistant", "subtitle": "Reporting and financial summary"},
            "assets": {"title": "Asset Analyst", "subtitle": "Plant inventory and capacity"},
            "monitoring": {"title": "Systems Analyst", "subtitle": "API, data quality and integration"},
            "scenarios": {"title": "Scenario Analyst", "subtitle": "What-if simulation support"},
            "settings": {"title": "Platform Assistant", "subtitle": "Configuration and administration"},
        },
        "recommendations": {
            "operations": [
                "Log the last 5 operational events in the shift journal.",
                "Validate active alarm thresholds with the control room protocol.",
                "Cross-check SCADA and forecast deviation hourly.",
            ],
            "forecast": [
                "Plan a model calibration window if MAPE exceeds 15%.",
                "Inspect hourly bias between weather forecast and production curve.",
            ],
            "market": [
                "Align high imbalance cost hours with the PTF curve.",
                "Share the daily cost summary with finance.",
            ],
            "risk": [
                "Trigger executive briefing if risk score exceeds 75.",
                "Monitor financial and production risk on separate panels.",
            ],
            "ai": [
                "Approve or postpone pending actions by priority.",
                "Validate low-confidence recommendations with the field team.",
            ],
            "dashboard": [
                "Triage critical alerts in the Operations Center.",
                "Add the executive summary to the daily briefing.",
            ],
            "reports": ["Archive the executive PDF report weekly."],
            "monitoring": ["Check API latency and error rate hourly."],
            "assets": ["Review plant health scores weekly."],
            "scenarios": ["Log what-if outcomes in the decision journal."],
            "settings": ["Rotate API keys periodically."],
        },
        "risk_labels": {"high": "high", "medium": "medium", "low": "low"},
        "mape_labels": {"acceptable": "acceptable", "watch": "watch", "critical": "critical"},
        "briefing": {
            "default_action": "Continue standard monitoring protocol.",
            "no_rule": "No active critical rule detected.",
            "titles": {
                "dashboard": "{name} — Executive Summary",
                "operations": "{name} — Control Room Assessment",
                "forecast": "{name} — Forecast Performance Analysis",
                "market": "{name} — Market Assessment",
                "risk": "{name} — Risk Assessment",
                "ai": "{name} — Decision Center",
                "reports": "{name} — Report Summary",
                "assets": "{name} — Asset Status",
                "monitoring": "{name} — System Monitoring",
                "scenarios": "{name} — Scenario Analysis",
                "settings": "{name} — Platform Configuration",
            },
            "status_summary": (
                "Operational risk for {name} is {risk}/100 ({risk_label}). "
                "MAPE {mape:.1f}% ({mape_label}). Context: {context}."
            ),
            "analysis": "Latest pipeline completed {steps} steps. Imbalance cost {cost}.",
            "risk": "Primary risk: {rule} Corporate risk {risk}/100.",
            "financial_impact": "Estimated imbalance cost {cost}.",
            "operational_impact": "Forecast reliability is {mape_label}.",
            "alternative_action": "Consider an alternative action path.",
        },
        "annotations": {
            "primary_action": "Recommended action",
            "alternative_action": "Alternative action",
            "rule_alert": "Rule alert",
            "ai_recommendation": "AI recommendation",
            "imbalance_cost": "Imbalance cost",
            "risk_score": "Risk score",
            "forecast_accuracy": "Forecast accuracy",
            "active_alerts": "Active alerts",
            "production_forecast": "Production forecast",
            "actual_production": "Actual production",
            "forecast_deviation": "Forecast deviation",
            "cost_over_budget": "Total cost {cost:,.0f} TL — above the budget band.",
            "cost_action": "Revise position and production plan under cost pressure.",
            "risk_fallback": "Risk score {risk}/100.",
            "mape_insight": "Live MAPE {mape:.1f}% — {mape_label}.",
            "mape_action": "Run hourly bias analysis and update the forecast margin.",
            "alerts_insight": "{count} rules triggered — triage and field verification required.",
            "forecast_insight": "Forecast {mw} MW — {band}.",
            "forecast_band_tight": "confidence band is tight",
            "forecast_band_wide": "margin should be increased",
            "production_insight": "Current production {mw} MW.",
            "deviation_insight": "Actual-forecast delta {delta:+.1f} MW — {note}.",
            "deviation_systematic": "possible systematic bias",
            "deviation_ok": "within tolerance",
            "deviation_action": "Start root-cause analysis on the deviation.",
            "verify_rule": "Verify the rule and continue monitoring.",
        },
        "scenario": {
            "summary": (
                "Scenario for {name}: wind {wind}%, PTF {ptf}%, {turbines} turbine(s) offline. "
                "Forecast {baseline_mw} → {adjusted_mw} MW, cost {baseline_cost} → {adjusted_cost} TL, "
                "risk {baseline_risk} → {adjusted_risk}."
            ),
        },
        "monitoring": {
            "log_empty": "Log file has not been created yet. API is active.",
            "daily_pipeline": "Daily Pipeline",
            "kpi_refresh": "KPI Refresh",
            "kpi_schedule": "Every 30 minutes",
        },
        "alerts": {
            "title_operational": "Operational Alert",
            "title_action": "Recommended Action",
            "title_status": "Status",
            "no_active": "No active notifications.",
            "sim_prefix": "[Simulation]",
            "risk_critical": "Critical imbalance risk! Immediate position check recommended.",
            "risk_warning": "Elevated imbalance risk detected.",
            "risk_info": "Risk level is within operational limits.",
            "mape_sim": (
                "Simulation MAPE {mape:.1f}% (informational). "
                "Ground truth is EPİAŞ-derived/mock — not used for model calibration."
            ),
            "mape_live": (
                "Low forecast accuracy (MAPE: {mape:.1f}%). "
                "Model update may be required."
            ),
        },
        "playbook": {
            "fallback_prefix": "System notice: AI service unreachable, automatic playbook engaged.",
            "insight_fmt": "AI analysis: [{title}] {message}",
            "storm_high_cost": {
                "title": "Lessons Learned",
                "message": "In past storms, turbine pitch angles were adjusted late and production stopped. Action: Manually inspect pitch control systems.",
                "action": "Manually inspect pitch control systems",
            },
            "low_wind_maintenance": {
                "title": "Playbook",
                "message": "Low-wind scenario. Suitable window for planned maintenance.",
                "action": "Evaluate the planned maintenance window",
            },
            "elevated_risk": {
                "title": "Risk Alert",
                "message": "Imbalance cost is rising. Monitor hourly forecast vs actual production and notify operations if needed.",
                "action": "Reduce position",
            },
            "default": {
                "title": "Operational Status",
                "message": "Parameters are within normal range. Continue standard monitoring.",
                "action": "Continue standard monitoring procedure",
            },
        },
        "rules": {
            "critical_risk": {
                "live": {
                    "message": "Risk score exceeded the critical threshold.",
                    "action": "Start emergency position control",
                },
                "sim": {
                    "message": "Simulation risk score is high (proxy ground truth).",
                    "action": "Do not raise position alarms without live SCADA ground truth",
                },
            },
            "elevated_risk": {
                "live": {
                    "message": "Risk score is elevated.",
                    "action": "Monitor hourly production deviation",
                },
                "sim": {
                    "message": "Simulation risk score has risen.",
                    "action": "Verify the Operational MW source",
                },
            },
            "high_mape": {
                "live": {
                    "message": "Forecast accuracy is low (MAPE > 15%).",
                    "action": "Calibrate the forecast model",
                },
                "sim": {
                    "message": "Simulation MAPE is high — not model failure; proxy actuals.",
                    "action": "MAPE is informational; live SCADA needed for calibration",
                },
            },
            "high_imbalance_cost": {
                "live": {
                    "message": "Imbalance cost has increased.",
                    "action": "Review the position",
                },
                "sim": {
                    "message": "Simulation imbalance cost is high (proxy).",
                    "action": "Interpret cost in the simulation context",
                },
            },
            "nominal_operations": {
                "live": {
                    "message": "Operational parameters are within normal range.",
                    "action": "Continue standard monitoring",
                },
                "sim": {
                    "message": "Operational parameters are within normal range.",
                    "action": "Continue standard monitoring",
                },
            },
        },
        "quality": {"high": "high", "medium": "medium", "low": "low"},
        "decisions": {
            "pipeline_done": "Pipeline evaluation completed.",
            "continue_monitoring": "Continue monitoring",
            "run_insight": "Risk {risk}/100 · MAPE {mape:.1f}% · cost {cost:,.0f} TL.",
        },
        "reporting": {
            "no_data": (
                "No analyzable pipeline data found for plant {asset_id} "
                "in the last {period_days} records."
            ),
            "summary": (
                "For {asset_id}, {run_count} records were analyzed over {period_days} days. "
                "Total imbalance cost {cost} TL, average MAPE {mape}%, "
                "critical alerts {critical_alerts}. Overall: {posture}."
            ),
            "posture": {
                "critical_alerts": "critical alerts present; urgent review recommended",
                "low_accuracy": "forecast accuracy is low; model calibration advised",
                "high_cost": "imbalance cost elevated; review position management",
                "normal": "within operational limits; routine monitoring sufficient",
            },
            "conclusion": (
                "Conclusion: {posture} Priority action: {action}. "
                "Period cost {cost} TL, average risk {risk}/100, DQ score {dq}."
            ),
            "insufficient": "Insufficient data",
            "ai_brief_title": "AI Executive Brief",
            "score_financial": "Financial Health",
            "score_operational": "Operational Health",
            "score_forecast": "Forecast Confidence",
            "score_data": "Data Quality",
            "score_model": "Model Reliability",
            "score_risk": "Risk Posture",
            "score_alerts": "Critical Alerts",
            "score_overall": "Overall Health",
            "priority_high": "High",
            "priority_medium": "Medium",
            "priority_low": "Low",
            "trend_up": "Up",
            "trend_down": "Down",
            "trend_flat": "Flat",
            "status_open": "Open",
            "level_warn": "Warning",
            "level_crit": "Critical",
            "level_ok": "Normal",
            "sim_flag": "Simulation / informational",
            "weekly_summary": (
                "For {asset_id}, {weeks} weekly periods were analyzed. "
                "Total {runs} pipeline records."
            ),
            "weekly_empty": "No analyzable weekly records found for {asset_id}.",
            "type_executive": "Executive Report",
            "type_operational": "Operational Report",
            "type_forecast": "Forecast Report",
            "type_financial": "Financial Report",
            "type_risk": "Risk Report",
            "type_technical": "Technical Report",
            "adaptive_hint": "Suggested report for workspace ({workspace}): {report_type}.",
            "changes_insufficient": "Not enough period records for comparison.",
            "changes_summary": (
                "Vs prior period: cost {cost_delta}%, MAPE {mape_delta}, risk {risk_delta}. "
                "New critical alerts: {new_alerts}, closed: {closed_alerts}."
            ),
            "ask_mape": "Average MAPE {mape}% ({label}). Latest MAPE {latest}%.",
            "ask_mape_why": (
                "Why MAPE changed: prior-period avg {prior}% -> recent-period avg {recent}% "
                "(delta {mape_delta} pts). Period average {mape}% ({label}), latest {latest}%. "
                "Plausible drivers: {drivers} Watch: {watch}. Period summary: {changes}"
            ),
            "ask_cost": "Total imbalance cost {total} TL (trend: {trend}). Avoidable estimate: {avoidable} TL.",
            "ask_cost_why": (
                "Why cost changed: total {total} TL (trend: {trend}), avoidable {avoidable} TL; "
                "period cost change {cost_delta}%. Plausible drivers: {drivers} "
                "Period comparison: {changes}"
            ),
            "ask_risk": "Average risk {score}/100 ({level}). Top rule: {rule}.",
            "ask_risk_why": (
                "Why risk changed: average {score}/100 ({level}), top rule: {rule}; "
                "period risk change {risk_delta}. Plausible drivers: {drivers} "
                "Period comparison: {changes}"
            ),
            "ask_action": "Recommended action: {action}",
            "ask_default": "Summary: {summary} Conclusion: {conclusion}",
            "ask_why_default": (
                "The clearest period signal for this question: {changes} "
                "Plausible drivers: {drivers} Summary: {summary} Conclusion: {conclusion}"
            ),
            "ask_off_topic": (
                "This question is not about the report data. "
                "Ask about MAPE, cost, risk, or recommended actions."
            ),
            "ask_driver_up": "Rising KPIs ({items}).",
            "ask_driver_down": "Falling KPIs ({items}).",
            "ask_driver_rule": "Top rule: {rule}.",
            "ask_driver_simulation": "Simulation/synthetic data may be influencing the signal.",
            "ask_driver_event": "Top event: {event}.",
            "ask_driver_alerts": "New critical alert increase: {count}.",
            "ask_driver_none": "No extra driver signal in the pack; watch period deltas and latest readings.",
            "type_focus_executive": "Executive view focused on finance, risk, forecast and actions.",
            "type_focus_operational": "Operations view focused on alarms, rules and field actions.",
            "type_focus_forecast": "Forecast view focused on MAPE, model confidence and trends.",
            "type_focus_financial": "Financial view focused on imbalance cost, trends and portfolio comparison.",
            "type_focus_risk": "Risk view focused on score, rules and recommended actions.",
            "type_focus_technical": "Technical view focused on data quality and model reliability.",
            "pack_title": "{report_type} — {asset_id}",
            "portfolio_fallback": (
                "Portfolio ({count} plants): total cost {cost:,.0f} TL, "
                "avg. MAPE {mape:.1f}%, critical alerts {critical}."
            ),
        },
        "export": {
            "pdf_title": "AeroVantage — Executive Report",
            "pdf_doc_type": "Executive Operational Intelligence Report",
            "pdf_brand": "AeroVantage",
            "pdf_tagline": "Operational Intelligence",
            "section_meta": "Document Information",
            "section_kpis": "Key Performance Indicators",
            "section_summary": "Executive Summary",
            "section_ai_brief": "AI Executive Brief",
            "section_scorecards": "Scorecards",
            "section_financial": "Financial Intelligence",
            "section_forecast": "Forecast Intelligence",
            "section_operational": "Operational Intelligence",
            "section_risk": "Risk Intelligence",
            "section_data": "Data Intelligence",
            "section_model": "Model Intelligence",
            "section_recommendations": "AI Recommendations",
            "section_actions": "Action Center",
            "section_trends": "Trend Analysis",
            "section_benchmark": "Benchmark",
            "section_conclusion": "Executive Conclusion",
            "section_changes": "Changes Summary",
            "plant": "Plant",
            "period": "Period",
            "period_days": "days",
            "cost": "Total imbalance cost",
            "mape": "Average MAPE",
            "critical_alerts": "Critical alerts",
            "generated_at": "Generated at (UTC)",
            "document_id": "Document ID",
            "locale": "Language",
            "metric": "Metric",
            "value": "Value",
            "status": "Status",
            "status_summary": "Status summary",
            "priority": "Priority",
            "action": "Action",
            "owner": "Owner",
            "top_event": "Top event",
            "top_risk": "Top risk",
            "avg_daily_cost": "Average daily cost",
            "cost_trend": "Cost trend",
            "avoidable_cost": "Avoidable cost (est.)",
            "revenue_risk": "Revenue risk",
            "latest_mape": "Latest MAPE",
            "confidence": "Confidence",
            "critical_count": "Critical alerts",
            "warning_count": "Warnings",
            "active_rules": "Active rules",
            "pipeline_runs": "Pipeline runs",
            "avg_risk": "Average risk",
            "latest_risk": "Latest risk",
            "max_risk": "Max risk",
            "top_rule": "Top rule",
            "trust_score": "Trust score",
            "latest_dq": "Latest DQ score",
            "gate": "Gate",
            "drift": "Drift",
            "model_version": "Model version",
            "physics_fallback": "Physics fallback",
            "coverage": "Coverage",
            "cost_spark": "Cost trend",
            "mape_spark": "MAPE trend",
            "risk_spark": "Risk trend",
            "prior_avg_cost": "Prior avg cost",
            "recent_avg_cost": "Recent avg cost",
            "vs_prior_pct": "vs prior %",
            "portfolio_mape": "Portfolio MAPE",
            "portfolio_cost": "Portfolio cost",
            "changes_summary": "Changes summary",
            "report_type": "Report type",
            "confidential": "Confidential — For internal use only. Do not distribute.",
            "page": "Page",
            "footer_brand": "AeroVantage Operational Intelligence",
            "csv_field": "Field",
            "csv_value": "Value",
            "excel_executive": "Executive",
            "excel_history": "History",
            "excel_sections": "Sections",
        },
    },
    "de": {
        "experts": {
            "dashboard": {"title": "Management-Assistent", "subtitle": "Portfolio und Management-Entscheidungsunterstuetzung"},
            "operations": {"title": "Operations-Assistent", "subtitle": "Leitstand und Live-Betrieb"},
            "forecast": {"title": "Prognose-Analyst", "subtitle": "Produktionsprognose und Modellleistung"},
            "market": {"title": "Markt-Analyst", "subtitle": "PTF, SMF und Ungleichgewichtskosten"},
            "risk": {"title": "Risiko-Analyst", "subtitle": "Risikoscore und Exposure-Management"},
            "ai": {"title": "Entscheidungszentrum", "subtitle": "Ausstehende Aktionen und Freigabe"},
            "reports": {"title": "Management-Assistent", "subtitle": "Berichterstattung und Finanzuebersicht"},
            "assets": {"title": "Anlagen-Analyst", "subtitle": "Kraftwerksinventar und Kapazitaet"},
            "monitoring": {"title": "System-Analyst", "subtitle": "API, Datenqualitaet und Integration"},
            "scenarios": {"title": "Szenario-Analyst", "subtitle": "What-if-Simulationsunterstuetzung"},
            "settings": {"title": "Plattform-Assistent", "subtitle": "Konfiguration und Verwaltung"},
        },
        "recommendations": {
            "operations": [
                "Die letzten 5 Betriebsereignisse im Schichtbuch erfassen.",
                "Aktive Alarm-Schwellen mit dem Leitstand-Protokoll pruefen.",
                "SCADA und Prognoseabweichung stuendlich abgleichen.",
            ],
            "forecast": [
                "Kalibrierungsfenster planen, wenn MAPE ueber 15% liegt.",
                "Stuendlichen Bias zwischen Wetterprognose und Produktionskurve pruefen.",
            ],
            "market": [
                "Stunden mit hohen Ungleichgewichtskosten mit der PTF-Kurve abgleichen.",
                "Taegliche Kostenzusammenfassung mit Finance teilen.",
            ],
            "risk": [
                "Management-Briefing ausloesen, wenn Risikoscore ueber 75 liegt.",
                "Finanzielles und Produktionsrisiko getrennt ueberwachen.",
            ],
            "ai": [
                "Ausstehende Aktionen nach Prioritaet freigeben oder verschieben.",
                "Empfehlungen mit niedriger Konfidenz mit dem Feldteam pruefen.",
            ],
            "dashboard": [
                "Kritische Alarme im Operations Center triageieren.",
                "Management-Zusammenfassung dem taeglichen Briefing hinzufuegen.",
            ],
            "reports": ["Management-PDF woechentlich archivieren."],
            "monitoring": ["API-Latenz und Fehlerquote stuendlich pruefen."],
            "assets": ["Anlagen-Gesundheitswerte woechentlich pruefen."],
            "scenarios": ["What-if-Ergebnisse im Entscheidungsjournal erfassen."],
            "settings": ["API-Schluessel periodisch rotieren."],
        },
        "risk_labels": {"high": "hoch", "medium": "mittel", "low": "niedrig"},
        "mape_labels": {"acceptable": "akzeptabel", "watch": "beobachten", "critical": "kritisch"},
        "briefing": {
            "default_action": "Standard-Ueberwachungsprotokoll fortsetzen.",
            "no_rule": "Keine aktive kritische Regel erkannt.",
            "titles": {
                "dashboard": "{name} — Management-Uebersicht",
                "operations": "{name} — Leitstand-Bewertung",
                "forecast": "{name} — Prognoseleistung",
                "market": "{name} — Marktbewertung",
                "risk": "{name} — Risikobewertung",
                "ai": "{name} — Entscheidungszentrum",
                "reports": "{name} — Berichtszusammenfassung",
                "assets": "{name} — Anlagenstatus",
                "monitoring": "{name} — Systemueberwachung",
                "scenarios": "{name} — Szenarioanalyse",
                "settings": "{name} — Plattformkonfiguration",
            },
            "status_summary": (
                "Operatives Risiko fuer {name}: {risk}/100 ({risk_label}). "
                "MAPE {mape:.1f}% ({mape_label}). Kontext: {context}."
            ),
            "analysis": "Letzte Pipeline: {steps} Schritte abgeschlossen. Ungleichgewichtskosten {cost}.",
            "risk": "Primaeres Risiko: {rule} Unternehmensrisiko {risk}/100.",
            "financial_impact": "Geschaetzte Ungleichgewichtskosten {cost}.",
            "operational_impact": "Prognosezuverlaessigkeit: {mape_label}.",
            "alternative_action": "Alternativen Aktionspfad pruefen.",
        },
        "annotations": {
            "primary_action": "Empfohlene Aktion",
            "alternative_action": "Alternative Aktion",
            "rule_alert": "Regelalarm",
            "ai_recommendation": "KI-Empfehlung",
            "imbalance_cost": "Ungleichgewichtskosten",
            "risk_score": "Risikoscore",
            "forecast_accuracy": "Prognosegenauigkeit",
            "active_alerts": "Aktive Alarme",
            "production_forecast": "Produktionsprognose",
            "actual_production": "Tatsaechliche Produktion",
            "forecast_deviation": "Prognoseabweichung",
            "cost_over_budget": "Gesamtkosten {cost:,.0f} TL — ueber dem Budgetband.",
            "cost_action": "Position und Produktionsplan unter Kostendruck ueberarbeiten.",
            "risk_fallback": "Risikoscore {risk}/100.",
            "mape_insight": "Live-MAPE {mape:.1f}% — {mape_label}.",
            "mape_action": "Stuendliche Bias-Analyse starten und Prognosemarge aktualisieren.",
            "alerts_insight": "{count} Regeln ausgeloest — Triage und Feldpruefung erforderlich.",
            "forecast_insight": "Prognose {mw} MW — {band}.",
            "forecast_band_tight": "Konfidenzband eng",
            "forecast_band_wide": "Marge erhoehen",
            "production_insight": "Aktuelle Produktion {mw} MW.",
            "deviation_insight": "Ist-Prognose-Differenz {delta:+.1f} MW — {note}.",
            "deviation_systematic": "moegliche systematische Abweichung",
            "deviation_ok": "innerhalb der Toleranz",
            "deviation_action": "Ursachenanalyse der Abweichung starten.",
            "verify_rule": "Regel pruefen und Ueberwachung fortsetzen.",
        },
        "scenario": {
            "summary": (
                "Szenario fuer {name}: Wind {wind}%, PTF {ptf}%, {turbines} Turbine(n) offline. "
                "Prognose {baseline_mw} → {adjusted_mw} MW, Kosten {baseline_cost} → {adjusted_cost} TL, "
                "Risiko {baseline_risk} → {adjusted_risk}."
            ),
        },
        "monitoring": {
            "log_empty": "Logdatei wurde noch nicht erstellt. API ist aktiv.",
            "daily_pipeline": "Taegliche Pipeline",
            "kpi_refresh": "KPI-Aktualisierung",
            "kpi_schedule": "Alle 30 Minuten",
        },
        "alerts": {
            "title_operational": "Betrieblicher Alarm",
            "title_action": "Empfohlene Aktion",
            "title_status": "Status",
            "no_active": "Keine aktiven Benachrichtigungen.",
            "sim_prefix": "[Simulation]",
            "risk_critical": "Kritisches Ungleichgewichtsrisiko! Sofortige Positionskontrolle empfohlen.",
            "risk_warning": "Erhoehtes Ungleichgewichtsrisiko erkannt.",
            "risk_info": "Risikoniveau liegt innerhalb der betrieblichen Grenzen.",
            "mape_sim": (
                "Simulations-MAPE {mape:.1f}% (informativ). "
                "Ground Truth ist EPİAŞ-abgeleitet/Mock — nicht fuer Modellkalibrierung."
            ),
            "mape_live": (
                "Niedrige Prognosegenauigkeit (MAPE: {mape:.1f}%). "
                "Modellaktualisierung kann erforderlich sein."
            ),
        },
        "playbook": {
            "fallback_prefix": "Systemhinweis: KI-Dienst nicht erreichbar, automatisches Playbook aktiv.",
            "insight_fmt": "KI-Analyse: [{title}] {message}",
            "storm_high_cost": {
                "title": "Lessons Learned",
                "message": "Bei frueheren Stuermen wurden Pitch-Winkel zu spaet angepasst und die Produktion gestoppt. Aktion: Pitch-Steuerung manuell pruefen.",
                "action": "Pitch-Steuerungssysteme manuell pruefen",
            },
            "low_wind_maintenance": {
                "title": "Playbook",
                "message": "Schwachwind-Szenario. Geeignetes Fenster fuer geplante Wartung.",
                "action": "Geplantes Wartungsfenster bewerten",
            },
            "elevated_risk": {
                "title": "Risikowarnung",
                "message": "Ungleichgewichtskosten steigen. Stuendlich Prognose vs. Ist ueberwachen und bei Bedarf Operations informieren.",
                "action": "Position reduzieren",
            },
            "default": {
                "title": "Betriebsstatus",
                "message": "Parameter im Normalbereich. Standardueberwachung fortsetzen.",
                "action": "Standardueberwachungsverfahren fortsetzen",
            },
        },
        "rules": {
            "critical_risk": {
                "live": {
                    "message": "Risikoscore hat den kritischen Schwellwert ueberschritten.",
                    "action": "Notfall-Positionskontrolle starten",
                },
                "sim": {
                    "message": "Simulations-Risikoscore ist hoch (Proxy-Ground-Truth).",
                    "action": "Ohne Live-SCADA keine Positionsalarme erzeugen",
                },
            },
            "elevated_risk": {
                "live": {
                    "message": "Risikoscore ist erhoeht.",
                    "action": "Stuendliche Produktionsabweichung ueberwachen",
                },
                "sim": {
                    "message": "Simulations-Risikoscore ist gestiegen.",
                    "action": "Operational-MW-Quelle verifizieren",
                },
            },
            "high_mape": {
                "live": {
                    "message": "Prognosegenauigkeit ist niedrig (MAPE > 15%).",
                    "action": "Prognosemodell kalibrieren",
                },
                "sim": {
                    "message": "Simulations-MAPE ist hoch — kein Modellfehler; Proxy-Istwerte.",
                    "action": "MAPE informativ; Live-SCADA fuer Kalibrierung erforderlich",
                },
            },
            "high_imbalance_cost": {
                "live": {
                    "message": "Ungleichgewichtskosten sind gestiegen.",
                    "action": "Position ueberpruefen",
                },
                "sim": {
                    "message": "Simulations-Ungleichgewichtskosten sind hoch (Proxy).",
                    "action": "Kosten im Simulationskontext interpretieren",
                },
            },
            "nominal_operations": {
                "live": {
                    "message": "Betriebsparameter liegen im Normalbereich.",
                    "action": "Standardueberwachung fortsetzen",
                },
                "sim": {
                    "message": "Betriebsparameter liegen im Normalbereich.",
                    "action": "Standardueberwachung fortsetzen",
                },
            },
        },
        "quality": {"high": "hoch", "medium": "mittel", "low": "niedrig"},
        "decisions": {
            "pipeline_done": "Pipeline-Bewertung abgeschlossen.",
            "continue_monitoring": "Ueberwachung fortsetzen",
            "run_insight": "Risiko {risk}/100 · MAPE {mape:.1f}% · Kosten {cost:,.0f} TL.",
        },
        "reporting": {
            "no_data": (
                "Fuer Anlage {asset_id} wurden in den letzten {period_days} "
                "Datensaetzen keine analysierbaren Pipeline-Daten gefunden."
            ),
            "summary": (
                "Fuer {asset_id} wurden {run_count} Datensaetze ueber {period_days} Tage analysiert. "
                "Gesamte Ungleichgewichtskosten {cost} TL, durchschnittliche MAPE {mape}%, "
                "kritische Alarme {critical_alerts}. Gesamt: {posture}."
            ),
            "posture": {
                "critical_alerts": "kritische Alarme vorhanden; dringende Pruefung empfohlen",
                "low_accuracy": "Prognosegenauigkeit niedrig; Modellkalibrierung empfohlen",
                "high_cost": "Ungleichgewichtskosten erhoeht; Positionsmanagement pruefen",
                "normal": "innerhalb operativer Grenzen; routinemaessige Ueberwachung ausreichend",
            },
            "conclusion": (
                "Fazit: {posture} Prioritaere Aktion: {action}. "
                "Periodenkosten {cost} TL, durchschnittliches Risiko {risk}/100, DQ-Score {dq}."
            ),
            "insufficient": "Unzureichende Daten",
            "ai_brief_title": "KI-Management-Briefing",
            "score_financial": "Finanzielle Gesundheit",
            "score_operational": "Operative Gesundheit",
            "score_forecast": "Prognosekonfidenz",
            "score_data": "Datenqualitaet",
            "score_model": "Modellzuverlaessigkeit",
            "score_risk": "Risikolage",
            "score_alerts": "Kritische Alarme",
            "score_overall": "Gesamtgesundheit",
            "priority_high": "Hoch",
            "priority_medium": "Mittel",
            "priority_low": "Niedrig",
            "trend_up": "Steigend",
            "trend_down": "Fallend",
            "trend_flat": "Stabil",
            "status_open": "Offen",
            "level_warn": "Warnung",
            "level_crit": "Kritisch",
            "level_ok": "Normal",
            "sim_flag": "Simulation / informativ",
            "weekly_summary": (
                "Fuer {asset_id} wurden {weeks} Wochenperioden analysiert. "
                "Insgesamt {runs} Pipeline-Datensaetze."
            ),
            "weekly_empty": "Keine analysierbaren Wochendaten fuer {asset_id} gefunden.",
            "type_executive": "Managementbericht",
            "type_operational": "Betriebsbericht",
            "type_forecast": "Prognosebericht",
            "type_financial": "Finanzbericht",
            "type_risk": "Risikobericht",
            "type_technical": "Technischer Bericht",
            "adaptive_hint": "Empfohlener Bericht fuer Workspace ({workspace}): {report_type}.",
            "changes_insufficient": "Nicht genuegend Periodendaten fuer den Vergleich.",
            "changes_summary": (
                "Gegenueber Vorperiode: Kosten {cost_delta}%, MAPE {mape_delta}, Risiko {risk_delta}. "
                "Neue kritische Alarme: {new_alerts}, geschlossen: {closed_alerts}."
            ),
            "ask_mape": "Durchschnittliche MAPE {mape}% ({label}). Letzte MAPE {latest}%.",
            "ask_mape_why": (
                "Warum MAPE sich aenderte: Vorperiode Ø {prior}% -> aktuelle Periode Ø {recent}% "
                "(Delta {mape_delta} Pkt.). Periodendurchschnitt {mape}% ({label}), zuletzt {latest}%. "
                "Plausible Treiber: {drivers} Beobachten: {watch}. Periodenzusammenfassung: {changes}"
            ),
            "ask_cost": "Gesamte Ungleichgewichtskosten {total} TL (Trend: {trend}). Vermeidbar geschaetzt: {avoidable} TL.",
            "ask_cost_why": (
                "Warum Kosten sich aenderten: Gesamt {total} TL (Trend: {trend}), vermeidbar {avoidable} TL; "
                "Kosten-Aenderung zur Vorperiode {cost_delta}%. Plausible Treiber: {drivers} "
                "Periodenvergleich: {changes}"
            ),
            "ask_risk": "Durchschnittliches Risiko {score}/100 ({level}). Top-Regel: {rule}.",
            "ask_risk_why": (
                "Warum Risiko sich aenderte: Durchschnitt {score}/100 ({level}), Top-Regel: {rule}; "
                "Risiko-Aenderung zur Vorperiode {risk_delta}. Plausible Treiber: {drivers} "
                "Periodenvergleich: {changes}"
            ),
            "ask_action": "Empfohlene Aktion: {action}",
            "ask_default": "Zusammenfassung: {summary} Fazit: {conclusion}",
            "ask_why_default": (
                "Das klarste Periodensignal fuer diese Frage: {changes} "
                "Plausible Treiber: {drivers} Zusammenfassung: {summary} Fazit: {conclusion}"
            ),
            "ask_off_topic": (
                "Diese Frage bezieht sich nicht auf die Berichtsdaten. "
                "Fragen Sie nach MAPE, Kosten, Risiko oder Aktionen."
            ),
            "ask_driver_up": "Steigende KPIs ({items}).",
            "ask_driver_down": "Fallende KPIs ({items}).",
            "ask_driver_rule": "Top-Regel: {rule}.",
            "ask_driver_simulation": "Simulation/synthetische Daten koennen das Signal beeinflussen.",
            "ask_driver_event": "Top-Ereignis: {event}.",
            "ask_driver_alerts": "Anstieg neuer kritischer Alarme: {count}.",
            "ask_driver_none": "Kein zusaetzliches Treibersignal im Pack; Periodendeltas und letzte Werte beobachten.",
            "type_focus_executive": "Management-Ansicht mit Fokus auf Finanzen, Risiko, Prognose und Aktionen.",
            "type_focus_operational": "Betriebsansicht mit Fokus auf Alarme, Regeln und Feldaktionen.",
            "type_focus_forecast": "Prognoseansicht mit Fokus auf MAPE, Modellkonfidenz und Trends.",
            "type_focus_financial": "Finanzansicht mit Fokus auf Ungleichgewichtskosten, Trends und Portfoliovergleich.",
            "type_focus_risk": "Risikoansicht mit Fokus auf Score, Regeln und empfohlene Aktionen.",
            "type_focus_technical": "Technische Ansicht mit Fokus auf Datenqualitaet und Modellzuverlaessigkeit.",
            "pack_title": "{report_type} — {asset_id}",
            "portfolio_fallback": (
                "Portfolio ({count} Anlagen): Gesamtkosten {cost:,.0f} TL, "
                "Ø MAPE {mape:.1f}%, kritische Alarme {critical}."
            ),
        },
        "export": {
            "pdf_title": "AeroVantage — Managementbericht",
            "pdf_doc_type": "Operativer Intelligenzbericht fuer das Management",
            "pdf_brand": "AeroVantage",
            "pdf_tagline": "Operationale Intelligenz",
            "section_meta": "Dokumentinformationen",
            "section_kpis": "Wichtige Leistungskennzahlen",
            "section_summary": "Management-Zusammenfassung",
            "section_ai_brief": "KI-Management-Briefing",
            "section_scorecards": "Scorecards",
            "section_financial": "Finanzielle Intelligenz",
            "section_forecast": "Prognose-Intelligenz",
            "section_operational": "Operative Intelligenz",
            "section_risk": "Risiko-Intelligenz",
            "section_data": "Daten-Intelligenz",
            "section_model": "Modell-Intelligenz",
            "section_recommendations": "KI-Empfehlungen",
            "section_actions": "Aktionszentrum",
            "section_trends": "Trendanalyse",
            "section_benchmark": "Benchmark",
            "section_conclusion": "Management-Fazit",
            "section_changes": "Aenderungsuebersicht",
            "plant": "Anlage",
            "period": "Zeitraum",
            "period_days": "Tage",
            "cost": "Gesamte Ungleichgewichtskosten",
            "mape": "Durchschnittliche MAPE",
            "critical_alerts": "Kritische Alarme",
            "generated_at": "Erstellt am (UTC)",
            "document_id": "Dokument-Nr.",
            "locale": "Sprache",
            "metric": "Kennzahl",
            "value": "Wert",
            "status": "Status",
            "status_summary": "Statuszusammenfassung",
            "priority": "Prioritaet",
            "action": "Aktion",
            "owner": "Verantwortlich",
            "top_event": "Wichtigstes Ereignis",
            "top_risk": "Wichtigstes Risiko",
            "avg_daily_cost": "Durchschn. Tageskosten",
            "cost_trend": "Kostentrend",
            "avoidable_cost": "Vermeidbare Kosten (gesch.)",
            "revenue_risk": "Erloesrisiko",
            "latest_mape": "Aktuelle MAPE",
            "confidence": "Konfidenz",
            "critical_count": "Kritische Alarme",
            "warning_count": "Warnungen",
            "active_rules": "Aktive Regeln",
            "pipeline_runs": "Pipeline-Laeufe",
            "avg_risk": "Durchschn. Risiko",
            "latest_risk": "Aktuelles Risiko",
            "max_risk": "Max. Risiko",
            "top_rule": "Wichtigste Regel",
            "trust_score": "Vertrauensscore",
            "latest_dq": "Aktueller DQ-Score",
            "gate": "Gate",
            "drift": "Drift",
            "model_version": "Modellversion",
            "physics_fallback": "Physics-Fallback",
            "coverage": "Abdeckung",
            "cost_spark": "Kostentrend",
            "mape_spark": "MAPE-Trend",
            "risk_spark": "Risiko-Trend",
            "prior_avg_cost": "Vorperiode Durchschn. Kosten",
            "recent_avg_cost": "Aktuelle Periode Durchschn. Kosten",
            "vs_prior_pct": "ggueber Vorperiode %",
            "portfolio_mape": "Portfolio-MAPE",
            "portfolio_cost": "Portfolio-Kosten",
            "changes_summary": "Aenderungsuebersicht",
            "report_type": "Berichtstyp",
            "confidential": "Vertraulich — Nur fuer den internen Gebrauch. Nicht weitergeben.",
            "page": "Seite",
            "footer_brand": "AeroVantage Operationale Intelligenz",
            "csv_field": "Feld",
            "csv_value": "Wert",
            "excel_executive": "Management",
            "excel_history": "Verlauf",
            "excel_sections": "Abschnitte",
        },
    },
}
