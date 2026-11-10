"""Yönetim API rotaları."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from core.config import get_settings

router = APIRouter()
_USERS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "users.json"


@router.get("/users")
def list_users() -> list[dict[str, Any]]:
    """Kayıtlı platform kullanıcılarını döndürür."""
    if not _USERS_FILE.exists():
        return []
    with _USERS_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


@router.get("/config")
def get_system_config() -> dict[str, Any]:
    """Sistem yapılandırma özetini döndürür (gizli anahtarlar hariç)."""
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "log_level": settings.log_level,
        "epias_use_mock": settings.epias_use_mock,
        "weather_use_mock": settings.weather_use_mock,
        "scada_use_mock": settings.scada_use_mock,
        "llm_provider": settings.llm_provider,
        "llm_api_key_configured": bool(settings.llm_api_key.get_secret_value()),
        "epias_api_key_configured": bool(settings.epias_api_key.get_secret_value()),
        "epias_credentials_configured": bool(
            settings.epias_username.get_secret_value()
            and settings.epias_password.get_secret_value()
        ),
    }
