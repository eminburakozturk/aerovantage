"""Raporlama API rotaları."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.storage import PipelineStorage
from modules.portfolio_aggregator.service import PortfolioAggregatorService
from modules.reporting.export import (
    export_executive_csv,
    export_executive_excel,
    export_executive_pdf,
    export_history_csv,
)
from modules.reporting.schemas import ExecutiveReportResponse
from modules.reporting.service import ReportingService

router = APIRouter()
_reporting_service = ReportingService()
_portfolio_service = PortfolioAggregatorService()
_storage = PipelineStorage()


class ReportAskRequest(BaseModel):
    asset_id: str = Field(..., min_length=1, description="Santral kimliği")
    question: str = Field(..., min_length=2, description="Rapor sorusu")
    days: int = Field(default=30, ge=1, le=365)
    locale: str = Field(default="tr")
    report_type: str = Field(default="executive")


@router.get("/executive", response_model=ExecutiveReportResponse)
def get_executive_report(
    asset_id: str = Query(..., description="Santral kimliği (örn. RES-BAL-01)"),
    days: int = Query(default=30, ge=1, le=365, description="Analiz edilecek kayıt sayısı"),
    locale: str = Query(default="tr", description="Rapor dili: tr, en, de"),
    report_type: str = Query(default="executive", description="Rapor tipi"),
    workspace: str | None = Query(default=None, description="Adaptive öneri için workspace"),
) -> dict[str, Any]:
    """Yönetici özeti raporunu pipeline geçmişinden üretir."""
    return _reporting_service.generate_executive_report(
        asset_id=asset_id,
        days_back=days,
        locale=locale,
        report_type=report_type,
        workspace=workspace,
    )


@router.get("/suggest-type")
def suggest_report_type(
    workspace: str = Query(default="reports", description="Çalışma alanı"),
) -> dict[str, str]:
    """Workspace'e göre önerilen rapor tipi (Adaptive Report Intelligence)."""
    suggested = _reporting_service.suggested_report_type(workspace)
    return {"workspace": workspace, "report_type": suggested}


@router.post("/ask")
def ask_about_report(body: ReportAskRequest) -> dict[str, Any]:
    """Rapor paketine dayalı soru-cevap (LLM varsa Gemini/OpenAI, yoksa şablon)."""
    return _reporting_service.ask_about_report(
        asset_id=body.asset_id,
        question=body.question,
        days_back=body.days,
        locale=body.locale,
        report_type=body.report_type,
    )


@router.get("/kpi")
def get_system_kpi(
    days: int = Query(default=30, ge=1, le=365, description="Analiz edilecek kayıt sayısı"),
) -> dict[str, Any]:
    """Sistem geneli MAPE, uptime ve API availability KPI'larını döndürür."""
    return _reporting_service.get_system_kpi(days_back=days)


@router.get("/portfolio")
def get_portfolio_report(
    asset_ids: str = Query(
        ...,
        description="Virgülle ayrılmış santral kimlikleri (örn. RES-BAL-01,RES-BND-02)",
    ),
    days: int = Query(default=30, ge=1, le=365, description="Analiz edilecek kayıt sayısı"),
    locale: str = Query(default="tr", description="Rapor dili: tr, en, de"),
) -> dict[str, Any]:
    """Seçili santraller için birleştirilmiş portföy raporu üretir."""
    parsed_asset_ids = [item.strip() for item in asset_ids.split(",") if item.strip()]
    if not parsed_asset_ids:
        raise HTTPException(status_code=400, detail="asset_ids parametresi boş olamaz")

    try:
        return _portfolio_service.get_aggregated_report(
            asset_ids=parsed_asset_ids,
            days=days,
            locale=locale,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/weekly")
def get_weekly_report(
    asset_id: str = Query(..., description="Santral kimliği"),
    weeks: int = Query(default=4, ge=1, le=12, description="Hafta sayısı"),
    locale: str = Query(default="tr", description="Rapor dili: tr, en, de"),
) -> dict[str, Any]:
    """Haftalık agregasyon raporu üretir."""
    return _reporting_service.generate_weekly_report(asset_id=asset_id, weeks_back=weeks, locale=locale)


@router.get("/export/pdf")
def export_pdf(
    asset_id: str = Query(..., description="Santral kimliği"),
    days: int = Query(default=30, ge=1, le=365),
    locale: str = Query(default="tr", description="Rapor dili: tr, en, de"),
    report_type: str = Query(default="executive", description="Rapor tipi"),
) -> Response:
    """Yönetici raporunu PDF olarak indirir."""
    report = _reporting_service.generate_executive_report(
        asset_id=asset_id,
        days_back=days,
        locale=locale,
        report_type=report_type,
    )
    try:
        content = export_executive_pdf(report, locale=locale)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_type}-{asset_id}.pdf"'},
    )


@router.get("/export/excel")
def export_excel(
    asset_id: str = Query(..., description="Santral kimliği"),
    days: int = Query(default=30, ge=1, le=365),
    locale: str = Query(default="tr", description="Rapor dili: tr, en, de"),
    report_type: str = Query(default="executive", description="Rapor tipi"),
) -> Response:
    """Yönetici raporu ve geçmişi Excel olarak indirir."""
    report = _reporting_service.generate_executive_report(
        asset_id=asset_id,
        days_back=days,
        locale=locale,
        report_type=report_type,
    )
    history = _storage.get_recent_runs(limit=days, asset_id=asset_id, dedupe=True)
    try:
        content = export_executive_excel(report, history, locale=locale)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="report-{asset_id}.xlsx"'},
    )


@router.get("/export/csv")
def export_csv(
    asset_id: str = Query(..., description="Santral kimliği"),
    days: int = Query(default=30, ge=1, le=365),
) -> Response:
    """Pipeline geçmişini CSV olarak indirir."""
    history = _storage.get_recent_runs(limit=days, asset_id=asset_id, dedupe=True)
    content = export_history_csv(history)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="history-{asset_id}.csv"'},
    )


@router.get("/export/executive-csv")
def export_executive_csv_route(
    asset_id: str = Query(..., description="Santral kimliği"),
    days: int = Query(default=30, ge=1, le=365),
    locale: str = Query(default="tr", description="Rapor dili: tr, en, de"),
    report_type: str = Query(default="executive", description="Rapor tipi"),
) -> Response:
    """Yönetici raporunu CSV olarak indirir."""
    report = _reporting_service.generate_executive_report(
        asset_id=asset_id,
        days_back=days,
        locale=locale,
        report_type=report_type,
    )
    content = export_executive_csv(report, locale=locale)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{report_type}-{asset_id}.csv"'},
    )

