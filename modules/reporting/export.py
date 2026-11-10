"""Rapor dışa aktarma yardımcıları — R1 kurumsal Intelligence PDF/Excel."""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from typing import Any

from core.i18n import export_labels, normalize_locale

try:
    from fpdf.enums import XPos, YPos
except ImportError:  # pragma: no cover
    XPos = None  # type: ignore[misc, assignment]
    YPos = None  # type: ignore[misc, assignment]

# Kurumsal palet (koyu lacivert / teal)
_NAVY = (15, 35, 65)
_TEAL = (0, 120, 130)
_SLATE = (70, 85, 100)
_LINE = (200, 210, 220)
_ROW_ALT = (245, 248, 250)
_WHITE = (255, 255, 255)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOGO_CANDIDATES = (
    _REPO_ROOT / "frontend" / "public" / "brand" / "logo-mark.png",
    _REPO_ROOT / "frontend" / "public" / "brand" / "primary.png",
)

_FONT_CANDIDATES = (
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
)


def export_executive_csv(report: dict[str, Any], locale: str = "tr") -> bytes:
    """Yönetici raporunu CSV olarak döndürür (üst seviye skaler alanlar)."""
    labels = export_labels(locale)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([labels["csv_field"], labels["csv_value"]])
    skip = {
        "scorecards",
        "ai_brief",
        "financial",
        "forecast",
        "operational",
        "risk",
        "data_intelligence",
        "model_intelligence",
        "recommendations",
        "actions",
        "trends",
        "benchmark",
    }
    for key, value in report.items():
        if key in skip:
            continue
        writer.writerow([key, value])
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def export_history_csv(history: list[dict[str, Any]]) -> bytes:
    """Pipeline geçmişini CSV olarak döndürür."""
    buffer = io.StringIO()
    fieldnames = [
        "target_date",
        "asset_id",
        "asset_name",
        "risk_score",
        "mape_percentage",
        "total_daily_mw",
        "total_imbalance_cost_tl",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in history or []:
        writer.writerow(row)
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _ascii_safe(text: str) -> str:
    replacements = {
        "ş": "s",
        "Ş": "S",
        "ğ": "g",
        "Ğ": "G",
        "ü": "u",
        "Ü": "U",
        "ö": "o",
        "Ö": "O",
        "ç": "c",
        "Ç": "C",
        "ı": "i",
        "İ": "I",
        "ä": "ae",
        "Ä": "Ae",
        "ß": "ss",
        "₺": "TL",
        "—": "-",
        "–": "-",
        "→": "->",
    }
    out = str(text)
    for src, dst in replacements.items():
        out = out.replace(src, dst)
    return out.encode("ascii", errors="replace").decode("ascii")


def _resolve_font_paths() -> tuple[Path | None, Path | None]:
    regular = next((p for p in _FONT_CANDIDATES if p.exists()), None)
    bold = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arialbd.ttf"
    if regular is None:
        return None, None
    if not bold.exists():
        bold = regular
    return regular, bold


def _resolve_logo() -> Path | None:
    return next((p for p in _LOGO_CANDIDATES if p.exists()), None)


def _fmt_generated_at(value: Any) -> str:
    if value is None:
        return "—"
    text = str(value)
    if "T" in text:
        return text.replace("T", " ")[:19] + (" UTC" if text.endswith("Z") or "+" in text[10:] else "")
    return text[:19]


def _fmt_cost(value: Any) -> str:
    try:
        return f"{float(value):,.2f} TL"
    except (TypeError, ValueError):
        return str(value)


def _fmt_mape(value: Any) -> str:
    try:
        return f"%{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _sparkline(values: list[Any], width: int = 24) -> str:
    nums = []
    for v in values[-width:]:
        try:
            nums.append(float(v))
        except (TypeError, ValueError):
            continue
    if not nums:
        return "—"
    lo, hi = min(nums), max(nums)
    span = (hi - lo) or 1.0
    # Arial Unicode spark glyph'leri eksik olabilir — ASCII bar kullan
    blocks = ".:-=+*#"
    return "".join(blocks[min(6, int((n - lo) / span * 6))] for n in nums)


def export_executive_pdf(report: dict[str, Any], locale: str = "tr") -> bytes:
    """Yönetici Intelligence Pack'i kurumsal PDF olarak döndürür."""
    labels = export_labels(locale)
    locale = normalize_locale(locale)
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise RuntimeError("fpdf2 paketi gerekli: pip install fpdf2") from exc

    regular_font, bold_font = _resolve_font_paths()
    logo_path = _resolve_logo()
    use_unicode = regular_font is not None

    class CorporateReportPdf(FPDF):
        def header(self) -> None:
            self.set_fill_color(*_NAVY)
            self.rect(0, 0, 210, 26, style="F")
            self.set_fill_color(*_TEAL)
            self.rect(0, 26, 210, 1.1, style="F")

            text_x = 18.0
            if logo_path is not None:
                try:
                    self.image(str(logo_path), x=15, y=5, h=15)
                    text_x = 34.0
                except Exception:
                    text_x = 18.0

            brand = labels["pdf_brand"] if use_unicode else _ascii_safe(labels["pdf_brand"])
            tagline = labels["pdf_tagline"] if use_unicode else _ascii_safe(labels["pdf_tagline"])
            self.set_xy(text_x, 6)
            self.set_text_color(*_WHITE)
            self.set_font(self._av_font, "B", 13)
            # fpdf2 default new_x=RIGHT — never rely on deprecated ln= for cursor home.
            brand_w = self.w - text_x - self.r_margin
            if XPos is not None and YPos is not None:
                self.cell(brand_w, 7, brand, new_x=XPos.LEFT, new_y=YPos.NEXT)
            else:
                self.cell(brand_w, 7, brand)
                self.set_xy(text_x, self.get_y() + 7)
            self.set_xy(text_x, self.get_y())
            self.set_font(self._av_font, "", 8)
            self.set_text_color(180, 200, 210)
            if XPos is not None and YPos is not None:
                self.cell(brand_w, 5, tagline, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            else:
                self.cell(brand_w, 5, tagline)
            self.set_text_color(0, 0, 0)
            self.set_y(34)
            self.set_x(self.l_margin)

        def footer(self) -> None:
            self.set_y(-16)
            self.set_draw_color(*_LINE)
            self.set_line_width(0.3)
            self.line(18, self.get_y(), 192, self.get_y())
            self.set_y(-13)
            self.set_x(self.l_margin)
            self.set_text_color(*_SLATE)
            self.set_font(self._av_font, "", 7)
            left = labels["confidential"] if use_unicode else _ascii_safe(labels["confidential"])
            page_lbl = labels["page"] if use_unicode else _ascii_safe(labels["page"])
            if XPos is not None and YPos is not None:
                self.cell(110, 5, left, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.cell(0, 5, f"{page_lbl} {self.page_no()}/{{nb}}", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            else:
                self.cell(110, 5, left, align="L")
                self.cell(0, 5, f"{page_lbl} {self.page_no()}/{{nb}}", align="R")
            self.set_x(self.l_margin)
            self.set_text_color(0, 0, 0)

    pdf = CorporateReportPdf(orientation="P", unit="mm", format="A4")
    pdf._av_font = "Helvetica"  # type: ignore[attr-defined]
    if use_unicode and regular_font is not None and bold_font is not None:
        pdf.add_font("AVSans", "", str(regular_font))
        pdf.add_font("AVSans", "B", str(bold_font))
        pdf._av_font = "AVSans"  # type: ignore[attr-defined]

    def t(text: Any) -> str:
        value = "" if text is None else str(text)
        return value if use_unicode else _ascii_safe(value)

    def cursor_home() -> None:
        """Force X to left margin without changing Y.

        Critical: fpdf2 multi_cell/cell default new_x=RIGHT. If X is already at the
        right edge, multi_cell(epw, ...) still paints from that X and clips
        (classic focus bug: 'Finans, risk' / 'Risk view f' near x≈547pt).
        """
        pdf.set_x(pdf.l_margin)

    def write_block(width: float | None, height: float, text: str, *, align: str = "L") -> None:
        """Write a full-width text block starting at the left margin."""
        usable = float(pdf.epw)
        w = usable if width is None else min(float(width), usable)
        cursor_home()
        kwargs: dict[str, Any] = {"align": align}
        if XPos is not None and YPos is not None:
            kwargs["new_x"] = XPos.LMARGIN
            kwargs["new_y"] = YPos.NEXT
        pdf.multi_cell(w, height, text, **kwargs)
        cursor_home()

    def section_title(title: str) -> None:
        if pdf.get_y() > 248:
            pdf.add_page()
        cursor_home()
        pdf.ln(4)
        cursor_home()
        pdf.set_text_color(*_NAVY)
        pdf.set_font(pdf._av_font, "B", 11)  # type: ignore[attr-defined]
        write_block(None, 6, t(title))
        pdf.set_draw_color(*_TEAL)
        pdf.set_line_width(0.45)
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.l_margin + 52, y)
        pdf.ln(3)
        cursor_home()
        pdf.set_text_color(0, 0, 0)

    def kv_table(rows: list[tuple[str, str]]) -> None:
        col_label, col_value = 66, 108
        row_h = 7.0
        line_h = 5.0
        pdf.set_draw_color(*_LINE)
        pdf.set_line_width(0.25)
        usable: list[tuple[str, str]] = []
        for label, value in rows:
            value_s = "" if value is None else str(value).strip()
            if not value_s or value_s == "—":
                continue
            usable.append((str(label), value_s))
        for i, (label, value) in enumerate(usable):
            if pdf.get_y() > 255:
                pdf.add_page()
            cursor_home()
            fill = i % 2 == 1
            label_t = f"  {t(label)}"
            value_t = t(value)

            pdf.set_font(pdf._av_font, "", 9)  # type: ignore[attr-defined]
            label_fits = pdf.get_string_width(label_t) <= col_label - 2
            pdf.set_font(pdf._av_font, "B", 9)  # type: ignore[attr-defined]
            value_fits = pdf.get_string_width(value_t) <= col_value - 3

            if label_fits and value_fits:
                if fill:
                    pdf.set_fill_color(*_ROW_ALT)
                pdf.set_font(pdf._av_font, "", 9)  # type: ignore[attr-defined]
                pdf.set_text_color(*_SLATE)
                cursor_home()
                if XPos is not None and YPos is not None:
                    pdf.cell(col_label, row_h, label_t, border="B", fill=fill, new_x=XPos.RIGHT, new_y=YPos.TOP)
                    pdf.set_text_color(20, 30, 40)
                    pdf.set_font(pdf._av_font, "B", 9)  # type: ignore[attr-defined]
                    pdf.cell(
                        col_value,
                        row_h,
                        value_t,
                        border="B",
                        fill=fill,
                        new_x=XPos.LMARGIN,
                        new_y=YPos.NEXT,
                    )
                else:
                    pdf.cell(col_label, row_h, label_t, border="B", fill=fill)
                    pdf.set_text_color(20, 30, 40)
                    pdf.set_font(pdf._av_font, "B", 9)  # type: ignore[attr-defined]
                    pdf.cell(col_value, row_h, value_t, border="B", fill=fill)
                    pdf.ln(row_h)
                cursor_home()
            else:
                x0 = pdf.l_margin
                y0 = pdf.get_y()
                page0 = pdf.page_no()
                pdf.set_font(pdf._av_font, "", 9)  # type: ignore[attr-defined]
                label_height = float(
                    pdf.multi_cell(
                        col_label,
                        line_h,
                        label_t,
                        align="L",
                        dry_run=True,
                        output="HEIGHT",
                    )
                )
                cursor_home()
                pdf.set_font(pdf._av_font, "B", 9)  # type: ignore[attr-defined]
                value_height = float(
                    pdf.multi_cell(
                        col_value,
                        line_h,
                        value_t,
                        align="L",
                        dry_run=True,
                        output="HEIGHT",
                    )
                )
                cursor_home()
                block_h = max(label_height, value_height, row_h) + 1.2
                if fill:
                    pdf.set_fill_color(*_ROW_ALT)
                    pdf.rect(x0, y0, col_label + col_value, block_h, style="F")
                mc_kwargs: dict[str, Any] = {"align": "L", "border": 0, "fill": False}
                if XPos is not None and YPos is not None:
                    mc_kwargs["new_x"] = XPos.RIGHT
                    mc_kwargs["new_y"] = YPos.TOP
                pdf.set_xy(x0, y0)
                pdf.set_text_color(*_SLATE)
                pdf.set_font(pdf._av_font, "", 9)  # type: ignore[attr-defined]
                pdf.multi_cell(col_label, line_h, label_t, **mc_kwargs)
                pdf.set_xy(x0 + col_label, y0)
                pdf.set_text_color(20, 30, 40)
                pdf.set_font(pdf._av_font, "B", 9)  # type: ignore[attr-defined]
                if XPos is not None and YPos is not None:
                    mc_kwargs["new_x"] = XPos.LMARGIN
                    mc_kwargs["new_y"] = YPos.TOP
                pdf.multi_cell(col_value, line_h, value_t, **mc_kwargs)
                y_end = y0 + block_h
                if pdf.page_no() == page0:
                    pdf.set_draw_color(*_LINE)
                    pdf.line(x0, y_end, x0 + col_label + col_value, y_end)
                    pdf.set_xy(x0, y_end)
                else:
                    pdf.set_x(x0)
                cursor_home()
        pdf.set_text_color(0, 0, 0)
        cursor_home()
        pdf.ln(2)
        cursor_home()

    def scorecard_value(card: dict[str, Any]) -> str:
        value = str(card.get("value") if card.get("value") is not None else "—").strip() or "—"
        level_txt = str(card.get("level_label") or card.get("level") or "").strip()
        if not level_txt or level_txt.casefold() == value.casefold():
            return value
        if value.casefold().endswith(f"({level_txt.casefold()})"):
            return value
        return f"{value} ({level_txt})"

    def body_text(text: str) -> None:
        pdf.set_text_color(35, 45, 55)
        pdf.set_font(pdf._av_font, "", 10)  # type: ignore[attr-defined]
        write_block(None, 5.8, t(text or "—"), align="L")
        pdf.set_text_color(0, 0, 0)
        cursor_home()
        pdf.ln(2)
        cursor_home()

    visible = report.get("visible_sections")
    visible_set = set(visible) if isinstance(visible, list) and visible else None

    def section_ok(key: str) -> bool:
        if visible_set is None:
            return True
        if key in {"meta", "summary", "conclusion"}:
            return True
        return key in visible_set

    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.set_margins(left=18, top=36, right=18)
    pdf.alias_nb_pages()
    pdf.add_page()
    cursor_home()

    pdf.set_text_color(*_NAVY)
    pdf.set_font(pdf._av_font, "B", 16)  # type: ignore[attr-defined]
    brief_title = (report.get("ai_brief") or {}).get("title")
    write_block(None, 8, t(brief_title or labels["pdf_doc_type"]))
    # Teal focus/subtitle — must always start at l_margin with full epw
    # (TR: "Finans, risk, tahmin...", EN: "Risk view focused...").
    cursor_home()
    pdf.set_text_color(*_TEAL)
    pdf.set_font(pdf._av_font, "", 10)  # type: ignore[attr-defined]
    focus = (report.get("ai_brief") or {}).get("focus")
    focus_text = t(focus or labels["pdf_title"])
    write_block(None, 5.5, focus_text)
    cursor_home()
    pdf.set_draw_color(*_TEAL)
    pdf.set_line_width(0.6)
    line_y = pdf.get_y() + 1
    pdf.line(pdf.l_margin, line_y, pdf.l_margin + 60, line_y)
    pdf.ln(6)
    cursor_home()
    pdf.set_text_color(0, 0, 0)

    asset_id = str(report.get("asset_id", "—"))
    period_days = report.get("period_days", "—")
    period_text = f"{period_days} {labels['period_days']}"

    if section_ok("meta"):
        section_title(labels["section_meta"])
        kv_table(
            [
                (labels["plant"], asset_id),
                (labels["period"], period_text),
                (labels["generated_at"], _fmt_generated_at(report.get("generated_at"))),
                (labels["document_id"], str(report.get("report_id", "—"))),
                (labels["locale"], locale.upper()),
                (labels["report_type"], str(report.get("report_type") or "executive")),
            ]
        )

    if section_ok("summary"):
        section_title(labels["section_summary"])
        body_text(str(report.get("executive_summary", "") or "—"))

    changes = report.get("changes_since_last") or {}
    if section_ok("changes") and changes:
        section_title(labels["section_changes"])
        body_text(str(changes.get("summary") or labels["changes_summary"]))

    ai_brief = report.get("ai_brief") or {}
    if section_ok("ai_brief") and ai_brief:
        section_title(labels["section_ai_brief"])
        status_summary = str(ai_brief.get("status_summary") or "").strip()
        if not status_summary or status_summary == "—":
            status_summary = str(report.get("executive_summary") or "").strip()
        brief_rows: list[tuple[str, str]] = [
            (labels["metric"], str(ai_brief.get("title") or "—")),
        ]
        if status_summary and status_summary != "—":
            brief_rows.append((labels["status_summary"], status_summary))
        brief_rows.extend(
            [
                (labels["top_event"], str(ai_brief.get("top_event") or "—")),
                (labels["top_risk"], str(ai_brief.get("top_risk") or "—")),
                (labels["cost"], str(ai_brief.get("financial_impact") or "—")),
                (labels["action"], str(ai_brief.get("recommended_action") or "—")),
                (
                    labels["confidence"],
                    str(ai_brief.get("confidence") if ai_brief.get("confidence") is not None else "—"),
                ),
            ]
        )
        kv_table(brief_rows)

    scorecards = report.get("scorecards") or []
    if section_ok("scorecards") and scorecards:
        section_title(labels["section_scorecards"])
        kv_table(
            [
                (
                    str(c.get("label") or c.get("id") or "—"),
                    scorecard_value(c) if isinstance(c, dict) else "—",
                )
                for c in scorecards
                if isinstance(c, dict)
            ]
        )
    elif section_ok("scorecards") and not scorecards:
        section_title(labels["section_kpis"])
        kv_table(
            [
                (labels["cost"], _fmt_cost(report.get("total_imbalance_cost_tl", 0))),
                (labels["mape"], _fmt_mape(report.get("average_mape", 0))),
                (labels["critical_alerts"], str(report.get("critical_alerts_count", 0))),
            ]
        )

    financial = report.get("financial") or {}
    if section_ok("financial") and financial:
        section_title(labels["section_financial"])
        kv_table(
            [
                (labels["cost"], _fmt_cost(financial.get("total_cost_tl"))),
                (labels["avg_daily_cost"], _fmt_cost(financial.get("average_daily_cost_tl"))),
                (
                    labels["cost_trend"],
                    str(financial.get("cost_trend_label") or financial.get("cost_trend") or "—"),
                ),
                (labels["avoidable_cost"], _fmt_cost(financial.get("avoidable_cost_estimate_tl"))),
                (labels["revenue_risk"], _fmt_cost(financial.get("revenue_risk_tl"))),
            ]
        )

    forecast = report.get("forecast") or {}
    if section_ok("forecast") and forecast:
        section_title(labels["section_forecast"])
        kv_table(
            [
                (labels["mape"], _fmt_mape(forecast.get("average_mape"))),
                (labels["latest_mape"], _fmt_mape(forecast.get("latest_mape"))),
                ("RMSE", str(forecast.get("rmse") or "—")),
                ("MAE", str(forecast.get("mae") or "—")),
                (labels["confidence"], str(forecast.get("confidence") if forecast.get("confidence") is not None else "—")),
            ]
        )

    operational = report.get("operational") or {}
    if section_ok("operational") and operational:
        section_title(labels["section_operational"])
        kv_table(
            [
                (labels["critical_count"], str(operational.get("critical_count", 0))),
                (labels["warning_count"], str(operational.get("warning_count", 0))),
                (labels["active_rules"], str(operational.get("active_rules", 0))),
                (labels["pipeline_runs"], str(operational.get("pipeline_runs", 0))),
            ]
        )

    risk = report.get("risk") or {}
    if section_ok("risk") and risk:
        section_title(labels["section_risk"])
        kv_table(
            [
                (labels["avg_risk"], str(risk.get("average_score", "—"))),
                (labels["latest_risk"], str(risk.get("latest_score", "—"))),
                (labels["max_risk"], str(risk.get("max_score", "—"))),
                (labels["status"], str(risk.get("level_label") or risk.get("level") or "—")),
                (labels["top_rule"], str(risk.get("top_rule") or "—")),
            ]
        )

    data_intel = report.get("data_intelligence") or {}
    if section_ok("data") and data_intel:
        section_title(labels["section_data"])
        kv_table(
            [
                (labels["trust_score"], str(data_intel.get("trust_score") or data_intel.get("average_score") or "—")),
                (labels["latest_dq"], str(data_intel.get("latest_score") or "—")),
                (labels["gate"], str(data_intel.get("gate_passed"))),
            ]
        )

    model_intel = report.get("model_intelligence") or {}
    if section_ok("model") and model_intel:
        section_title(labels["section_model"])
        kv_table(
            [
                (labels["confidence"], str(model_intel.get("confidence") if model_intel.get("confidence") is not None else "—")),
                (labels["drift"], str(model_intel.get("drift_detected") or "—")),
                (labels["model_version"], str(model_intel.get("model_version") or "—")),
                (labels["physics_fallback"], str(model_intel.get("physics_fallback"))),
                (labels["coverage"], str(model_intel.get("coverage") or "—")),
            ]
        )

    recommendations = report.get("recommendations") or []
    if section_ok("recommendations") and recommendations:
        section_title(labels["section_recommendations"])
        for idx, rec in enumerate(recommendations[:8], start=1):
            prio = rec.get("priority_label") or rec.get("priority") or ""
            body_text(f"{idx}. {rec.get('title') or '—'} [{prio}]")

    actions = report.get("actions") or []
    if section_ok("actions") and actions:
        section_title(labels["section_actions"])
        kv_table(
            [
                (
                    str(a.get("id") or "—"),
                    f"{a.get('title') or '—'} | {a.get('priority_label') or a.get('priority') or ''} | {a.get('status') or ''}",
                )
                for a in actions[:8]
            ]
        )

    trends = report.get("trends") or {}
    if section_ok("trends") and trends:
        section_title(labels["section_trends"])
        kv_table(
            [
                (labels["cost_spark"], _sparkline(trends.get("cost_sparkline") or [])),
                (labels["mape_spark"], _sparkline(trends.get("mape_sparkline") or [])),
                (labels["risk_spark"], _sparkline(trends.get("risk_sparkline") or [])),
            ]
        )

    benchmark = report.get("benchmark") or {}
    if section_ok("benchmark") and benchmark:
        section_title(labels["section_benchmark"])
        portfolio_cost = benchmark.get("portfolio_avg_cost_tl")
        kv_table(
            [
                (labels["prior_avg_cost"], _fmt_cost(benchmark.get("prior_period_avg_cost_tl"))),
                (labels["recent_avg_cost"], _fmt_cost(benchmark.get("recent_period_avg_cost_tl"))),
                (labels["vs_prior_pct"], str(benchmark.get("vs_prior_cost_pct"))),
                (labels["portfolio_mape"], str(benchmark.get("portfolio_avg_mape") or "—")),
                (
                    labels["portfolio_cost"],
                    _fmt_cost(portfolio_cost) if portfolio_cost is not None else "—",
                ),
            ]
        )

    conclusion = str(report.get("conclusion") or "")
    if section_ok("conclusion") and conclusion:
        section_title(labels["section_conclusion"])
        body_text(conclusion)

    pdf.ln(6)
    cursor_home()
    pdf.set_text_color(*_SLATE)
    pdf.set_font(pdf._av_font, "", 8)  # type: ignore[attr-defined]
    write_block(None, 5, t(labels["footer_brand"]))

    raw = pdf.output()
    if isinstance(raw, (bytes, bytearray)):
        content = bytes(raw)
    elif isinstance(raw, str):
        content = raw.encode("latin-1", errors="replace")
    else:
        content = bytes(raw)
    if not content:
        raise RuntimeError("PDF üretimi boş sonuç döndürdü")
    if not content.startswith(b"%PDF"):
        raise RuntimeError("PDF üretimi geçersiz çıktı")
    return content


def export_executive_excel(
    report: dict[str, Any],
    history: list[dict[str, Any]],
    locale: str = "tr",
) -> bytes:
    """Yönetici raporu ve geçmişi Excel olarak döndürür."""
    labels = export_labels(locale)
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError("openpyxl paketi gerekli: pip install openpyxl") from exc

    wb = Workbook()
    ws = wb.active
    ws.title = labels["excel_executive"][:31]
    ws.append([labels["csv_field"], labels["csv_value"]])
    scalar_skip = {
        "scorecards",
        "ai_brief",
        "financial",
        "forecast",
        "operational",
        "risk",
        "data_intelligence",
        "model_intelligence",
        "recommendations",
        "actions",
        "trends",
        "benchmark",
        "changes_since_last",
        "visible_sections",
    }
    scalar_labels = {
        "asset_id": labels["plant"],
        "period_days": labels["period"],
        "generated_at": labels["generated_at"],
        "report_id": labels["document_id"],
        "locale": labels["locale"],
        "report_type": labels["report_type"],
        "total_imbalance_cost_tl": labels["cost"],
        "average_mape": labels["mape"],
        "critical_alerts_count": labels["critical_alerts"],
        "executive_summary": labels["section_summary"],
        "conclusion": labels["section_conclusion"],
    }
    for key, value in report.items():
        if key in scalar_skip:
            continue
        ws.append([scalar_labels.get(key, key), str(value)])

    ws_sec = wb.create_sheet(labels.get("excel_sections", "Sections")[:31])
    ws_sec.append([labels["metric"], labels["value"], labels.get("status", "status")])
    for card in report.get("scorecards") or []:
        ws_sec.append([card.get("label"), card.get("value"), card.get("level_label")])
    for rec in report.get("recommendations") or []:
        ws_sec.append(
            [
                labels.get("section_recommendations", "recommendation"),
                rec.get("title"),
                rec.get("priority_label") or rec.get("priority"),
            ]
        )
    for act in report.get("actions") or []:
        ws_sec.append([act.get("id"), act.get("title"), act.get("priority_label")])

    ws2 = wb.create_sheet(labels["excel_history"][:31])
    headers = ["target_date", "asset_id", "risk_score", "mape_percentage", "total_imbalance_cost_tl"]
    ws2.append(headers)
    for row in history:
        ws2.append([row.get(h, "") for h in headers])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
