"""AI API rotaları."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from core.config import get_settings
from modules.ai.assistant import AIDecisionAssistant
from modules.ai.context_briefing import ContextBriefingService
from modules.ai.history import DecisionHistoryLogger

router = APIRouter()
_history = DecisionHistoryLogger()
_assistant = AIDecisionAssistant()
_briefing = ContextBriefingService()


@router.get("/briefing")
def get_context_briefing(
    context: str = Query(default="dashboard", description="Calisma alani baglami"),
    asset_id: str = Query(..., description="Santral kimligi"),
    days: int = Query(default=7, ge=1, le=90),
    locale: str = Query(default="tr", description="Cikti dili: tr, en, de"),
) -> dict[str, Any]:
    """Sayfa baglamina gore yonetici ve teknik AI brifingi dondurur."""
    return _briefing.generate(context=context, asset_id=asset_id, days=days, locale=locale)


@router.get("/history")
def get_ai_history(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
    """AI karar geçmişini döndürür."""
    return _history.get_recent(limit=limit)


@router.get("/models")
def get_ai_models() -> dict[str, Any]:
    """Yapılandırılmış AI model ve sağlayıcı bilgisini döndürür."""
    settings = get_settings()
    provider = settings.llm_provider
    api_key_configured = bool(settings.llm_api_key.get_secret_value())
    models = {
        "mock": {"name": "Playbook Engine", "version": "v1", "type": "rule-based"},
        "openai": {"name": "gpt-4o-mini", "version": "2024", "type": "llm"},
        "gemini": {"name": "gemini-auto", "version": "list-models", "type": "llm"},
    }
    active = models.get(provider, models["mock"])
    live_ready = provider in ("openai", "gemini") and api_key_configured
    mode = "live" if live_ready else "playbook"
    readiness = "ready" if live_ready else ("needs_api_key" if provider != "mock" else "playbook_default")
    return {
        "active_provider": provider,
        "active_model": active,
        "available_providers": list(models.keys()),
        "models": models,
        "api_key_configured": api_key_configured,
        "playbook_entries": len(_assistant._playbook),
        "mode": mode,
        "readiness": readiness,
        "live_ready": live_ready,
        "cutover_hint": (
            "LLM live"
            if live_ready
            else "Set LLM_PROVIDER=openai|gemini and LLM_API_KEY in .env, then restart backend"
        ),
    }
