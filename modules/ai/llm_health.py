"""LLM / Gemini sağlık ping — Data Hub health ile aynı yüzeyde izlenir."""

from __future__ import annotations

from typing import Any, Optional

import requests
from requests import Session

from core.config import Settings, get_settings
from core.logger import get_logger

_GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_PING_TIMEOUT_SECONDS = 8


class LlmHealthClient:
    """Aktif LLM sağlayıcısının erişilebilirlik / mod özeti."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        session: Optional[Session] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._session = session or requests.Session()
        self._logger = get_logger("modules.ai.llm_health")

    def ping(self) -> dict[str, Any]:
        provider = (self._settings.llm_provider or "mock").strip().lower()
        api_key = self._settings.llm_api_key.get_secret_value()

        if provider == "mock":
            return {
                "status": "ok",
                "client": "llm",
                "mode": "mock",
                "source": "playbook",
                "provider": "mock",
                "live": "false",
                "label": "Playbook (mock)",
                "confidence": "mock",
            }

        if not api_key:
            return {
                "status": "degraded",
                "client": "llm",
                "mode": "mock",
                "source": f"{provider}-missing-key",
                "provider": provider,
                "live": "false",
                "label": f"{provider} (key missing)",
                "confidence": "mock",
                "reason": "api_key_missing",
            }

        if provider == "gemini":
            return self._ping_gemini(api_key)
        if provider == "openai":
            return self._ping_openai_configured(api_key)

        return {
            "status": "degraded",
            "client": "llm",
            "mode": "mock",
            "source": f"unknown-provider:{provider}",
            "provider": provider,
            "live": "false",
            "label": f"Unknown provider ({provider})",
            "reason": "unsupported_provider",
        }

    def _ping_gemini(self, api_key: str) -> dict[str, Any]:
        headers: dict[str, str] = {"Accept": "application/json"}
        params: dict[str, str] = {}
        if api_key.startswith("AQ."):
            headers["x-goog-api-key"] = api_key
        else:
            params["key"] = api_key
        try:
            response = self._session.get(
                _GEMINI_MODELS_URL,
                params=params or None,
                headers=headers,
                timeout=_PING_TIMEOUT_SECONDS,
            )
            if response.status_code >= 400:
                detail = ""
                try:
                    detail = str(response.json().get("error", {}).get("message", ""))[:120]
                except Exception:  # noqa: BLE001
                    detail = (response.text or "")[:120]
                self._logger.warning(
                    "Gemini health ping failed: status=%s detail=%s",
                    response.status_code,
                    detail,
                )
                return {
                    "status": "degraded",
                    "client": "llm",
                    "mode": "fallback",
                    "source": "gemini",
                    "provider": "gemini",
                    "live": "false",
                    "label": "Gemini (unreachable)",
                    "confidence": "degraded",
                    "reason": f"http_{response.status_code}",
                }
            models = response.json().get("models") or []
            return {
                "status": "ok",
                "client": "llm",
                "mode": "live",
                "source": "gemini",
                "provider": "gemini",
                "live": "true",
                "label": "Gemini live",
                "confidence": "live",
                "reason": "ok",
                "model_count": len(models),
            }
        except requests.RequestException as exc:
            self._logger.warning("Gemini health ping network error: %s", exc)
            return {
                "status": "degraded",
                "client": "llm",
                "mode": "fallback",
                "source": "gemini",
                "provider": "gemini",
                "live": "false",
                "label": "Gemini (network error)",
                "confidence": "degraded",
                "reason": "network_error",
            }

    def _ping_openai_configured(self, api_key: str) -> dict[str, Any]:
        # Ağ çağrısı yok — key varlığı live kabul (kota tüketmemek için)
        return {
            "status": "ok",
            "client": "llm",
            "mode": "live",
            "source": "openai",
            "provider": "openai",
            "live": "true",
            "label": "OpenAI configured",
            "confidence": "live",
            "reason": "key_present",
        }


def llm_meta_from_ai_source(source: str) -> dict[str, Any]:
    """Pipeline AI yanıt source alanından telemetry girdisi."""
    normalized = (source or "unknown").strip().lower()
    if normalized == "gemini":
        return {
            "mode": "live",
            "reason": "ok",
            "source": "gemini",
            "provider": "gemini",
            "live": "true",
            "label": "Gemini live",
            "confidence": "live",
        }
    if normalized == "openai":
        return {
            "mode": "live",
            "reason": "ok",
            "source": "openai",
            "provider": "openai",
            "live": "true",
            "label": "OpenAI live",
            "confidence": "live",
        }
    if normalized == "fallback":
        return {
            "mode": "fallback",
            "reason": "llm_fallback",
            "source": "fallback",
            "provider": "playbook",
            "live": "false",
            "label": "Playbook fallback",
            "confidence": "degraded",
        }
    return {
        "mode": "mock",
        "reason": "playbook",
        "source": "playbook",
        "provider": "mock",
        "live": "false",
        "label": "Playbook",
        "confidence": "mock",
    }
