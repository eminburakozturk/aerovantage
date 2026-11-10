"""Pipeline API rotaları — manuel olay akışı tetikleme."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from modules.data_hub.errors import DataQualityGateError
from modules.forecast.production.model_reliability import ModelReliabilityGateError
from modules.recommendation.decision_reliability import DecisionReliabilityGateError
from core.pipeline import EventPipeline
from core.storage import PipelineStorage

router = APIRouter()
_pipeline = EventPipeline()
_storage = PipelineStorage()


class PipelineTriggerRequest(BaseModel):
    """Pipeline tetikleme isteği."""

    asset_id: str = Field(..., description="Santral kimliği (örn. RES-BAL-01)")
    target_date: Optional[date] = Field(
        default=None,
        description="Hedef tarih (varsayılan: bugün)",
    )


class PipelineTriggerResponse(BaseModel):
    """Pipeline tetikleme yanıtı."""

    status: str
    asset_id: str
    target_date: date
    steps_completed: list[str]
    metadata: dict[str, Any]


@router.post("/trigger-pipeline", response_model=PipelineTriggerResponse)
def trigger_pipeline(
    body: PipelineTriggerRequest,
    locale: str = Query(default="tr", description="Cikti dili: tr, en, de"),
) -> PipelineTriggerResponse:
    """Günlük Event Timeline pipeline'ını seçilen santral için tetikler."""
    from core.i18n import localize_pipeline_run, normalize_locale

    try:
        result = _pipeline.execute_daily_pipeline(
            asset_id=body.asset_id,
            target_date=body.target_date,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataQualityGateError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Data quality gate failed",
                "data_quality": exc.report.to_dict(),
            },
        ) from exc
    except ModelReliabilityGateError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Model reliability gate failed",
                "model_reliability": exc.report.to_dict(),
            },
        ) from exc
    except DecisionReliabilityGateError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Decision reliability gate failed",
                "decision_reliability": exc.report.to_dict(),
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline hatasi: {exc}",
        ) from exc

    metadata = result.metadata or {}
    loc = normalize_locale(locale)
    if loc != "tr" and isinstance(metadata, dict):
        metadata = localize_pipeline_run(loc, metadata)

    return PipelineTriggerResponse(
        status="completed",
        asset_id=result.asset_id,
        target_date=result.target_date,
        steps_completed=result.steps_completed,
        metadata=metadata,
    )


@router.get("/history")
def get_pipeline_history(
    limit: int = 10,
    locale: str = Query(default="tr", description="Cikti dili: tr, en, de"),
) -> list[dict[str, Any]]:
    """Son pipeline çalıştırma kayıtlarını (audit log) döndürür."""
    from core.i18n import localize_pipeline_run, normalize_locale

    loc = normalize_locale(locale)
    runs = _storage.get_recent_runs(limit=limit)
    if loc == "tr":
        return runs
    return [localize_pipeline_run(loc, run) for run in runs]
