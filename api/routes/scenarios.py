"""Senaryo analizi API rotaları."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from modules.scenario.schemas import ScenarioRequest
from modules.scenario.service import ScenarioService

router = APIRouter()
_scenarios = ScenarioService()


@router.post("/run")
def run_scenario(
    body: ScenarioRequest,
    locale: str = Query(default="tr", description="Cikti dili: tr, en, de"),
) -> dict[str, Any]:
    """What-if senaryo simülasyonu çalıştırır."""
    try:
        return _scenarios.run_scenario(body, locale=locale)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/history")
def get_scenario_history(
    limit: int = 20,
    locale: str = Query(default="tr", description="Cikti dili: tr, en, de"),
) -> list[dict[str, Any]]:
    """Son senaryo çalıştırmalarını döndürür."""
    return _scenarios.get_history(limit=limit, locale=locale)
