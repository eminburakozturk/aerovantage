"""AeroVantage operasyonel karar destek dashboard'u — yalnızca API okur."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Optional

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_ROOT = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/pipeline/trigger-pipeline").split(
    "/api/"
)[0]
PIPELINE_URL = f"{API_ROOT}/api/v1/pipeline/trigger-pipeline"
HISTORY_URL = f"{API_ROOT}/api/v1/pipeline/history"
ASSETS_URL = f"{API_ROOT}/api/v1/assets"
REPORTING_URL = f"{API_ROOT}/api/v1/reporting/executive"
PORTFOLIO_REPORTING_URL = f"{API_ROOT}/api/v1/reporting/portfolio"
API_HEALTH_URL = f"{API_ROOT}/health"
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "").strip()
if not API_SECRET_KEY:
    raise RuntimeError("API_SECRET_KEY environment variable is required (no default).")
REQUEST_TIMEOUT_SECONDS = 120


def api_auth_headers() -> dict[str, str]:
    """Yetkili API istekleri için Bearer başlığı."""
    return {"Authorization": f"Bearer {API_SECRET_KEY}"}


def check_api_health() -> tuple[bool, str]:
    """API ayakta mi kontrol eder."""
    try:
        response = requests.get(API_HEALTH_URL, timeout=3)
        if response.status_code == 200:
            return True, "API baglantisi OK"
        return False, f"API yanit kodu: {response.status_code}"
    except requests.RequestException as exc:
        return False, str(exc)


def fetch_assets() -> list[dict[str, Any]]:
    """Portföy santral listesini API'den çeker."""
    response = requests.get(ASSETS_URL, timeout=REQUEST_TIMEOUT_SECONDS, headers=api_auth_headers())
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30)
def fetch_pipeline_history(limit: int = 10) -> list[dict[str, Any]]:
    """Pipeline audit log kayıtlarını API'den çeker (30 sn cache)."""
    response = requests.get(
        HISTORY_URL,
        params={"limit": limit},
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers=api_auth_headers(),
    )
    response.raise_for_status()
    return response.json()


def trigger_pipeline(asset_id: str, target_date: date) -> dict[str, Any]:
    """Event Timeline pipeline'ını seçilen santral için tetikler."""
    response = requests.post(
        PIPELINE_URL,
        json={
            "asset_id": asset_id,
            "target_date": target_date.isoformat(),
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers=api_auth_headers(),
    )
    response.raise_for_status()
    return response.json()


def fetch_executive_report(asset_id: str, days: int = 30) -> dict[str, Any]:
    """Yönetici özeti raporunu reporting API'den çeker."""
    response = requests.get(
        REPORTING_URL,
        params={"asset_id": asset_id, "days": days},
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers=api_auth_headers(),
    )
    response.raise_for_status()
    return response.json()


def fetch_portfolio_report(asset_ids: list[str], days: int = 30) -> dict[str, Any]:
    """Portföy birleşik raporunu reporting API'den çeker."""
    response = requests.get(
        PORTFOLIO_REPORTING_URL,
        params={"asset_ids": ",".join(asset_ids), "days": days},
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers=api_auth_headers(),
    )
    response.raise_for_status()
    return response.json()


def build_hourly_dataframe(hours: list[dict[str, Any]]) -> pd.DataFrame:
    """Saatlik API yanıtını grafik için DataFrame'e dönüştürür."""
    rows = []
    for hour in hours:
        timestamp = hour["timestamp"]
        if isinstance(timestamp, str):
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            hour_label = f"{parsed.hour:02d}:00"
        else:
            hour_label = str(timestamp)

        rows.append(
            {
                "Saat": hour_label,
                "Tahmin (MW)": hour["forecast_mw"],
                "Gerçekleşen (MW)": hour["actual_mw"],
                "PTF (TL/MWh)": hour["ptf_price"],
            }
        )
    return pd.DataFrame(rows)


def format_history_dataframe(history: list[dict[str, Any]]) -> pd.DataFrame:
    """Audit log kayıtlarını özet tablo formatına dönüştürür."""
    rows = []
    for run in history:
        alert_status = run.get("alert_status") or {}
        rows.append(
            {
                "saved_at": run.get("saved_at"),
                "asset_id": run.get("asset_id"),
                "risk_score": run.get("risk_score"),
                "total_imbalance_cost_tl": run.get("total_imbalance_cost_tl"),
                "severity": alert_status.get("severity"),
            }
        )
    return pd.DataFrame(rows)


def render_results(pipeline_response: dict[str, Any]) -> None:
    """Pipeline yanıtını metrik, AI insight ve grafiklerle gösterir."""
    metadata = pipeline_response.get("metadata", {})
    asset_name = metadata.get("asset_name", pipeline_response.get("asset_id", "Santral"))
    risk_score = int(metadata.get("risk_score") or 0)
    total_cost = float(metadata.get("total_imbalance_cost_tl") or 0)
    mape_percentage = float(metadata.get("mape_percentage") or 0)
    alert_status = metadata.get("alert_status") or {}
    alert_severity = alert_status.get("severity", "")
    alert_message = alert_status.get("message", "")
    notifications = metadata.get("notifications", [])
    is_high_risk = risk_score > 50
    is_mape_high = mape_percentage >= 10.0
    is_critical = alert_severity == "CRITICAL" or risk_score > 75

    st.caption(f"Santral: **{asset_name}** ({metadata.get('asset_id', '')})")

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric(
        "Risk Skoru",
        f"{risk_score} / 100",
        delta="Yuksek" if is_high_risk else "Normal",
        delta_color="inverse" if is_high_risk else "normal",
    )
    metric_col2.metric("Toplam Dengesizlik Maliyeti", f"{total_cost:,.2f} TL")
    metric_col3.metric(
        "Tahmin Hata Payi (MAPE)",
        f"%{mape_percentage:.2f}",
        delta="Normal" if not is_mape_high else "Yuksek",
        delta_color="normal" if not is_mape_high else "inverse",
    )

    if alert_severity == "CRITICAL" and alert_message and not notifications:
        st.error(alert_message)
    elif alert_severity == "WARNING" and alert_message and not notifications:
        st.warning(alert_message)

    ai_insight = metadata.get("ai_insight", "")
    if ai_insight:
        st.markdown("**AI Karar Destek Asistanı**")
        if is_high_risk:
            st.warning(ai_insight)
        else:
            st.info(ai_insight)

    for notification in notifications:
        title = notification.get("title", "Bildirim")
        message = notification.get("message", "")
        level = str(notification.get("level", "INFO")).upper()
        content = f"**{title}**\n\n{message}"
        if level == "CRITICAL":
            st.error(content)
        elif level == "WARNING":
            st.warning(content)
        else:
            st.info(content)

    if not notifications:
        action_plan = metadata.get("action_plan", "")
        if action_plan:
            st.markdown("**Önerilen Aksiyon**")
            if is_critical:
                st.error(action_plan)
            elif is_high_risk:
                st.warning(action_plan)
            else:
                st.info(action_plan)

    hours = metadata.get("hours", [])
    if not hours:
        return

    chart_df = build_hourly_dataframe(hours).set_index("Saat")

    st.subheader("Saatlik Uretim (MW)")
    st.line_chart(chart_df[["Tahmin (MW)", "Gerçekleşen (MW)"]], height=320)

    st.subheader("Saatlik PTF (TL/MWh)")
    st.line_chart(chart_df[["PTF (TL/MWh)"]], height=240)


def render_instant_analysis_tab(api_ok: bool) -> None:
    """Anlık analiz sekmesi — pipeline tetikleme ve sonuçlar."""
    if "pipeline_data" not in st.session_state:
        st.session_state.pipeline_data: Optional[dict[str, Any]] = None
    if "fetch_error" not in st.session_state:
        st.session_state.fetch_error: Optional[str] = None

    assets: list[dict[str, Any]] = []
    if api_ok:
        try:
            assets = fetch_assets()
        except requests.RequestException as exc:
            st.error(f"Santral listesi alinamadi: {exc}")

    asset_options = {asset["name"]: asset["id"] for asset in assets}
    form_col1, form_col2, form_col3 = st.columns([2, 1, 1])

    with form_col1:
        selected_names = st.multiselect(
            "Santral Seciniz",
            options=list(asset_options.keys()) if asset_options else [],
            key="select_assets_instant",
        )
        selected_asset_ids = [asset_options[name] for name in selected_names]
        selected_asset_id = selected_asset_ids[0] if len(selected_asset_ids) == 1 else None

    with form_col2:
        target_date = st.date_input("Tarih", value=date.today(), key="input_date")

    with form_col3:
        st.write("")
        st.write("")
        analyze = st.button(
            "Analizi Getir",
            type="primary",
            key="btn_analyze",
            disabled=len(selected_asset_ids) != 1,
        )

    if len(selected_asset_ids) > 1:
        st.caption("Anlik analiz tek santral icindir. Coklu secimde Yonetici Ozeti sekmesinden Portfoy Raporu kullanin.")

    if analyze:
        if not api_ok:
            st.session_state.pipeline_data = None
            st.session_state.fetch_error = "API kapali. Once install.bat ve AeroVantage-Tray.bat calistirin."
        elif not selected_asset_id:
            st.session_state.pipeline_data = None
            st.session_state.fetch_error = "Gecerli bir santral secin."
        else:
            try:
                with st.spinner(
                    "Operasyonel Zeka Boru Hatti Tetikleniyor... (08.00 - 08.05)"
                ):
                    st.session_state.pipeline_data = trigger_pipeline(
                        selected_asset_id,
                        target_date,
                    )
                st.session_state.fetch_error = None
                fetch_pipeline_history.clear()
            except requests.ConnectionError:
                st.session_state.pipeline_data = None
                st.session_state.fetch_error = f"API'ye baglanilamadi: {PIPELINE_URL}"
            except requests.HTTPError as exc:
                st.session_state.pipeline_data = None
                st.session_state.fetch_error = (
                    f"API hatasi {exc.response.status_code}: {exc.response.text}"
                )
            except requests.RequestException as exc:
                st.session_state.pipeline_data = None
                st.session_state.fetch_error = f"Istek basarisiz: {exc}"

    if st.session_state.fetch_error:
        st.error(st.session_state.fetch_error)
    elif st.session_state.pipeline_data is None:
        st.info("Santral secip **Analizi Getir** butonuna basin.")
    else:
        render_results(st.session_state.pipeline_data)


def render_history_tab(api_ok: bool) -> None:
    """Geçmiş kayıtlar sekmesi — audit log tablosu."""
    header_col, refresh_col = st.columns([4, 1])
    with header_col:
        st.markdown("Son pipeline çalıştırma kayıtları (audit log).")
    with refresh_col:
        if st.button("Yenile", key="btn_refresh_history"):
            fetch_pipeline_history.clear()
            st.rerun()

    if not api_ok:
        st.warning("API kapali. Gecmis kayitlar yuklenemiyor.")
        return

    try:
        history = fetch_pipeline_history(limit=10)
    except requests.RequestException as exc:
        st.error(f"Gecmis kayitlar alinamadi: {exc}")
        return

    if not history:
        st.info("Henuz kayitli pipeline calistirmasi yok.")
        return

    history_df = format_history_dataframe(history)
    st.dataframe(history_df, use_container_width=True, hide_index=True)


def render_executive_report_tab(api_ok: bool) -> None:
    """Yönetici özeti sekmesi — 30 günlük rapor ve portföy raporu."""
    if "executive_report" not in st.session_state:
        st.session_state.executive_report: Optional[dict[str, Any]] = None
    if "portfolio_report" not in st.session_state:
        st.session_state.portfolio_report: Optional[dict[str, Any]] = None
    if "executive_report_error" not in st.session_state:
        st.session_state.executive_report_error: Optional[str] = None

    assets: list[dict[str, Any]] = []
    if api_ok:
        try:
            assets = fetch_assets()
        except requests.RequestException as exc:
            st.error(f"Santral listesi alinamadi: {exc}")

    asset_options = {asset["name"]: asset["id"] for asset in assets}
    control_col1, control_col2, control_col3 = st.columns([2, 1, 1])

    with control_col1:
        selected_names = st.multiselect(
            "Santral Seciniz",
            options=list(asset_options.keys()) if asset_options else [],
            key="select_assets_report",
        )
        selected_asset_ids = [asset_options[name] for name in selected_names]

    with control_col2:
        st.write("")
        st.write("")
        fetch_report = st.button(
            "Son 30 Gunluk Raporu Cek",
            type="primary",
            key="btn_fetch_executive_report",
            disabled=len(selected_asset_ids) != 1,
        )

    with control_col3:
        st.write("")
        st.write("")
        fetch_portfolio = st.button(
            "Portfoy Raporu",
            type="primary",
            key="btn_fetch_portfolio_report",
            disabled=len(selected_asset_ids) < 2,
        )

    if fetch_report:
        if not api_ok:
            st.session_state.executive_report = None
            st.session_state.portfolio_report = None
            st.session_state.executive_report_error = "API kapali. Once install.bat ve AeroVantage-Tray.bat calistirin."
        elif len(selected_asset_ids) != 1:
            st.session_state.executive_report = None
            st.session_state.portfolio_report = None
            st.session_state.executive_report_error = "Tek santral secin."
        else:
            try:
                with st.spinner("Yonetici ozeti raporu hazirlaniyor..."):
                    st.session_state.executive_report = fetch_executive_report(
                        selected_asset_ids[0],
                        days=30,
                    )
                    st.session_state.portfolio_report = None
                st.session_state.executive_report_error = None
            except requests.ConnectionError:
                st.session_state.executive_report = None
                st.session_state.executive_report_error = (
                    f"API'ye baglanilamadi: {REPORTING_URL}"
                )
            except requests.HTTPError as exc:
                st.session_state.executive_report = None
                st.session_state.executive_report_error = (
                    f"API hatasi {exc.response.status_code}: {exc.response.text}"
                )
            except requests.RequestException as exc:
                st.session_state.executive_report = None
                st.session_state.executive_report_error = f"Istek basarisiz: {exc}"

    if fetch_portfolio:
        if not api_ok:
            st.session_state.executive_report = None
            st.session_state.portfolio_report = None
            st.session_state.executive_report_error = "API kapali. Once install.bat ve AeroVantage-Tray.bat calistirin."
        elif len(selected_asset_ids) < 2:
            st.session_state.executive_report = None
            st.session_state.portfolio_report = None
            st.session_state.executive_report_error = "Portfoy raporu icin en az iki santral secin."
        else:
            try:
                with st.spinner("Portfoy raporu hazirlaniyor..."):
                    st.session_state.portfolio_report = fetch_portfolio_report(
                        selected_asset_ids,
                        days=30,
                    )
                    st.session_state.executive_report = None
                st.session_state.executive_report_error = None
            except requests.ConnectionError:
                st.session_state.portfolio_report = None
                st.session_state.executive_report_error = (
                    f"API'ye baglanilamadi: {PORTFOLIO_REPORTING_URL}"
                )
            except requests.HTTPError as exc:
                st.session_state.portfolio_report = None
                st.session_state.executive_report_error = (
                    f"API hatasi {exc.response.status_code}: {exc.response.text}"
                )
            except requests.RequestException as exc:
                st.session_state.portfolio_report = None
                st.session_state.executive_report_error = f"Istek basarisiz: {exc}"

    if st.session_state.executive_report_error:
        st.error(st.session_state.executive_report_error)
        return

    portfolio_report = st.session_state.portfolio_report
    if portfolio_report is not None:
        st.caption(
            f"Portfoy: **{', '.join(portfolio_report.get('asset_ids', []))}** | "
            f"Dönem: {portfolio_report.get('period_days', 30)} gun"
        )
        summary = portfolio_report.get("summary", "")
        if summary:
            st.info(summary)

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric(
            "Toplam Dengesizlik Maliyeti",
            f"{float(portfolio_report.get('total_cost') or 0):,.2f} TL",
        )
        metric_col2.metric(
            "Ortalama Hata Payi (MAPE)",
            f"%{float(portfolio_report.get('avg_mape') or 0):.2f}",
        )
        metric_col3.metric(
            "Kritik Uyari Sayisi",
            int(portfolio_report.get("critical_alert_count") or 0),
        )

        portfolio_json = json.dumps(portfolio_report, ensure_ascii=False, indent=2)
        st.download_button(
            label="portfolio_report.json indir",
            data=portfolio_json,
            file_name="portfolio_report.json",
            mime="application/json",
            key="btn_download_portfolio_report",
        )
        return

    report = st.session_state.executive_report
    if report is None:
        st.info(
            "Tek santral icin **Son 30 Gunluk Raporu Cek**, "
            "birden fazla santral icin **Portfoy Raporu** butonunu kullanin."
        )
        return

    st.caption(
        f"Rapor: **{report.get('asset_id', '')}** | "
        f"Dönem: {report.get('period_days', 30)} gun | "
        f"Olusturulma: {report.get('generated_at', '')}"
    )

    executive_summary = report.get("executive_summary", "")
    if executive_summary:
        st.info(executive_summary)

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric(
        "Toplam Dengesizlik Maliyeti",
        f"{float(report.get('total_imbalance_cost_tl') or 0):,.2f} TL",
    )
    metric_col2.metric(
        "Ortalama Hata Payi (MAPE)",
        f"%{float(report.get('average_mape') or 0):.2f}",
    )
    metric_col3.metric(
        "Kritik Uyari Sayisi",
        int(report.get("critical_alerts_count") or 0),
    )

    report_json = json.dumps(report, ensure_ascii=False, indent=2)
    st.download_button(
        label="executive_report.json indir",
        data=report_json,
        file_name="executive_report.json",
        mime="application/json",
        key="btn_download_executive_report",
    )


def main() -> None:
    st.set_page_config(page_title="AeroVantage", layout="wide", initial_sidebar_state="expanded")
    st.title("AeroVantage - Operasyonel Karar Destek")

    with st.sidebar:
        st.header("Sistem")
        api_ok, api_msg = check_api_health()
        st.markdown(f"**API:** {'Calisiyor' if api_ok else 'Kapali'}")
        if not api_ok:
            st.caption(api_msg)
            st.code(
                "python -m uvicorn api.main:app --host 127.0.0.1 --port 8000",
                language="powershell",
            )

    tab_instant, tab_history, tab_executive = st.tabs(
        ["Anlık Analiz", "Geçmiş Kayıtlar", "Yönetici Özeti (Rapor)"]
    )

    with tab_instant:
        render_instant_analysis_tab(api_ok)

    with tab_history:
        render_history_tab(api_ok)

    with tab_executive:
        render_executive_report_tab(api_ok)


if __name__ == "__main__":
    main()
