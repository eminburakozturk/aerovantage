"""Knowledge Layer ve LLM destekli AI karar asistanı."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import requests
from requests import Session

from core.config import Settings, get_settings
from core.i18n import (
    DEFAULT_LOCALE,
    ai_fallback_prefix,
    localize_action_plan,
    normalize_locale,
    playbook_insight,
    select_playbook_id,
)
from core.logger import get_logger
from modules.ai.history import DecisionHistoryLogger
from modules.ai.schemas import AIResponse

_PLAYBOOK_PATH = Path(__file__).resolve().parent / "knowledge" / "playbook.json"
_SYSTEM_PROMPT_PATH = (
    Path(__file__).resolve().parent / "prompts" / "system_prompt_v1.txt"
)
_HIGH_IMBALANCE_COST_TL = 3_000.0
_LOW_IMBALANCE_COST_TL = 1_500.0
_HIGH_RISK_SCORE = 50
_LOW_RISK_SCORE = 30
_LLM_TIMEOUT_SECONDS = 30
_OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
_GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
# ListModels başarısız olursa denenecek yedekler
_GEMINI_MODELS_FALLBACK = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-flash-latest",
    "gemini-pro-latest",
)
# generateContent reklam eden ama metin JSON için uygun olmayan aileler
_GEMINI_EXCLUDE_TOKENS = (
    "tts",
    "-audio",
    "embedding",
    "aqa",
    "imagen",
    "veo",
    "robotics",
    "live-preview",
)
_JSON_BLOCK_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


class AIDecisionAssistant:
    """Playbook ve LLM tabanlı operasyonel karar destek asistanı."""

    def __init__(
        self,
        playbook_path: Path | None = None,
        system_prompt_path: Path | None = None,
        settings: Optional[Settings] = None,
        session: Optional[Session] = None,
        history_logger: Optional[DecisionHistoryLogger] = None,
    ) -> None:
        self._playbook_path = playbook_path or _PLAYBOOK_PATH
        self._system_prompt_path = system_prompt_path or _SYSTEM_PROMPT_PATH
        self._settings = settings or get_settings()
        self._session = session or requests.Session()
        self._history_logger = history_logger or DecisionHistoryLogger()
        self._logger = get_logger("modules.ai.assistant")
        self._playbook = self._load_playbook()
        self._gemini_model_ids_cache: list[str] | None = None

    def _load_playbook(self) -> list[dict[str, Any]]:
        """Kurumsal playbook JSON dosyasını yükler."""
        with self._playbook_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("playbook.json bir JSON array olmalıdır")
        return data

    def _load_system_prompt(self) -> str:
        """Sistem prompt dosyasını okur."""
        return self._system_prompt_path.read_text(encoding="utf-8").strip()

    def _find_playbook_entry(self, entry_id: str) -> dict[str, Any]:
        """ID ile playbook maddesi döndürür."""
        for entry in self._playbook:
            if entry.get("id") == entry_id:
                return entry
        return self._playbook[-1]

    def _select_playbook_id(self, risk_data: dict[str, Any]) -> str:
        """Risk verisine göre en uygun playbook maddesini seçer."""
        return select_playbook_id(risk_data)

    def resolve_playbook_action_plan(self, risk_data: dict[str, Any], locale: str | None = None) -> str:
        """Risk verisine göre beklenen playbook aksiyon planını döndürür."""
        return localize_action_plan(locale or DEFAULT_LOCALE, risk_data)

    def _generate_playbook_response(
        self, risk_data: dict[str, Any], locale: str | None = None
    ) -> AIResponse:
        """Playbook IF-ELSE mantığıyla mock AI yanıtı üretir."""
        loc = normalize_locale(locale or DEFAULT_LOCALE)
        entry_id = self._select_playbook_id(risk_data)
        action_plan = self.resolve_playbook_action_plan(risk_data, loc)
        insight = playbook_insight(loc, entry_id)

        response = AIResponse(
            insight=insight,
            action_plan=action_plan,
            source="mock",
        )
        self._logger.info(
            "Playbook yaniti uretildi: playbook_id=%s risk_score=%s action_plan=%s locale=%s",
            entry_id,
            risk_data.get("risk_score"),
            action_plan,
            loc,
        )
        return response

    def _save_history(self, response: AIResponse, risk_data: dict[str, Any], source: str) -> None:
        """Karar geçmişine insight ve action_plan kaydeder."""
        self._history_logger.record(
            response=response,
            risk_data=risk_data,
            source=source,
        )

    def generate_explanation(
        self, risk_data: dict[str, Any], locale: str | None = None
    ) -> AIResponse:
        """Risk verisine göre LLM veya playbook tabanlı açıklama ve aksiyon planı üretir."""
        provider = self._settings.llm_provider
        loc = normalize_locale(locale or DEFAULT_LOCALE)

        if provider == "mock":
            response = self._generate_playbook_response(risk_data, loc)
            self._save_history(response, risk_data, response.source)
            return response

        try:
            response = self._generate_llm_response(risk_data, provider)
            self._save_history(response, risk_data, response.source)
            return response
        except requests.Timeout as exc:
            self._logger.error("LLM zaman asimi: provider=%s error=%s", provider, exc)
            response = self._fallback_response(risk_data, loc)
            self._save_history(response, risk_data, "fallback")
            return response
        except requests.RequestException as exc:
            self._logger.error("LLM ag hatasi: provider=%s error=%s", provider, exc)
            response = self._fallback_response(risk_data, loc)
            self._save_history(response, risk_data, "fallback")
            return response
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            self._logger.error("LLM yanit parse hatasi: provider=%s error=%s", provider, exc)
            response = self._fallback_response(risk_data, loc)
            self._save_history(response, risk_data, "fallback")
            return response

    def _fallback_response(self, risk_data: dict[str, Any], locale: str | None = None) -> AIResponse:
        """LLM erişilemediğinde playbook fallback yanıtı döndürür."""
        loc = normalize_locale(locale or DEFAULT_LOCALE)
        playbook_response = self._generate_playbook_response(risk_data, loc)
        return AIResponse(
            insight=f"{ai_fallback_prefix(loc)} {playbook_response.insight}",
            action_plan=playbook_response.action_plan,
            source="fallback",
        )

    def _generate_llm_response(self, risk_data: dict[str, Any], provider: str) -> AIResponse:
        """Seçili LLM sağlayıcısından yapılandırılmış yanıt üretir."""
        api_key = self._settings.llm_api_key.get_secret_value()
        if not api_key:
            self._logger.warning("LLM API anahtari bos, playbook'a donuluyor")
            return self._fallback_response(risk_data)

        system_prompt = self._load_system_prompt()
        user_payload = json.dumps(risk_data, ensure_ascii=False, indent=2)
        user_text = (
            "Aşağıdaki santral risk verisini analiz et. Yanıtında insight ve "
            "zorunlu action_plan alanlarını içeren JSON döndür:\n"
            f"{user_payload}"
        )

        if provider == "openai":
            raw_response = self._call_openai(system_prompt, user_text, api_key)
        elif provider == "gemini":
            raw_response = self._call_gemini(system_prompt, user_text, api_key)
        else:
            return self._generate_playbook_response(risk_data)

        parsed = self._parse_llm_response(raw_response, risk_data)
        parsed = parsed.model_copy(update={"source": provider})
        self._logger.info(
            "LLM yaniti uretildi: provider=%s risk_score=%s action_plan=%s",
            provider,
            risk_data.get("risk_score"),
            parsed.action_plan,
        )
        return parsed

    def complete_text(
        self,
        system_prompt: str,
        user_text: str,
        *,
        max_output_tokens: int = 512,
        temperature: float = 0.2,
    ) -> str | None:
        """Serbest metin LLM tamamlaması. Anahtar/provider yoksa veya hata olursa None."""
        provider = self._settings.llm_provider
        if provider == "mock":
            return None

        api_key = self._settings.llm_api_key.get_secret_value()
        if not api_key:
            self._logger.warning("LLM API anahtari bos, complete_text atlandi")
            return None

        try:
            if provider == "openai":
                return self._call_openai(
                    system_prompt,
                    user_text,
                    api_key,
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                ).strip()
            if provider == "gemini":
                return self._call_gemini(
                    system_prompt,
                    user_text,
                    api_key,
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                ).strip()
        except requests.Timeout as exc:
            self._logger.error("complete_text zaman asimi: provider=%s error=%s", provider, exc)
        except requests.RequestException as exc:
            self._logger.error("complete_text ag hatasi: provider=%s error=%s", provider, exc)
        except (KeyError, ValueError, TypeError) as exc:
            self._logger.error("complete_text parse hatasi: provider=%s error=%s", provider, exc)
        return None

    def _parse_llm_response(self, raw_response: str, risk_data: dict[str, Any]) -> AIResponse:
        """LLM yanıtından insight ve zorunlu action_plan alanlarını ayıklar."""
        content = raw_response.strip()
        json_match = _JSON_BLOCK_PATTERN.search(content)
        if json_match:
            payload = json.loads(json_match.group())
            insight = str(payload.get("insight", "")).strip()
            action_plan = str(payload.get("action_plan", "")).strip()
            if insight and action_plan:
                return AIResponse(insight=insight, action_plan=action_plan)

        playbook = self._generate_playbook_response(risk_data)
        return AIResponse(
            insight=content or playbook.insight,
            action_plan=playbook.action_plan,
        )

    def _call_openai(
        self,
        system_prompt: str,
        user_text: str,
        api_key: str,
        *,
        max_output_tokens: int = 300,
        temperature: float = 0.2,
    ) -> str:
        """OpenAI Chat Completions API iskeleti."""
        response = self._session.post(
            _OPENAI_CHAT_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                "temperature": temperature,
                "max_tokens": max_output_tokens,
            },
            timeout=_LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"])

    def _gemini_auth(self, api_key: str) -> tuple[dict[str, str], dict[str, str]]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        params: dict[str, str] = {}
        if api_key.startswith("AQ."):
            headers["x-goog-api-key"] = api_key
        else:
            params["key"] = api_key
        return headers, params

    @staticmethod
    def _is_text_gemini_model(model_id: str) -> bool:
        lower = model_id.lower()
        return not any(token in lower for token in _GEMINI_EXCLUDE_TOKENS)

    def _list_gemini_generate_models(self, api_key: str) -> list[str]:
        """ListModels ile metin generateContent modellerini döndürür (cache'li)."""
        if self._gemini_model_ids_cache is not None:
            return self._gemini_model_ids_cache

        headers, params = self._gemini_auth(api_key)
        try:
            response = self._session.get(
                _GEMINI_MODELS_URL,
                params=params or None,
                headers=headers,
                timeout=_LLM_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            models = response.json().get("models") or []
        except requests.RequestException as exc:
            self._logger.warning("Gemini ListModels başarısız, fallback liste: %s", exc)
            self._gemini_model_ids_cache = list(_GEMINI_MODELS_FALLBACK)
            return self._gemini_model_ids_cache

        generate_ids: list[str] = []
        for item in models:
            methods = item.get("supportedGenerationMethods") or []
            if "generateContent" not in methods:
                continue
            name = str(item.get("name") or "")
            model_id = name.split("/", 1)[-1] if name else ""
            if model_id and self._is_text_gemini_model(model_id):
                generate_ids.append(model_id)

        if not generate_ids:
            self._gemini_model_ids_cache = list(_GEMINI_MODELS_FALLBACK)
            return self._gemini_model_ids_cache

        def _rank(model_id: str) -> tuple[int, str]:
            lower = model_id.lower()
            if "flash" in lower and "lite" not in lower:
                return (0, lower)
            if "flash" in lower:
                return (1, lower)
            if "pro" in lower:
                return (2, lower)
            return (3, lower)

        generate_ids.sort(key=_rank)
        preferred = [m for m in _GEMINI_MODELS_FALLBACK if m in generate_ids]
        rest = [m for m in generate_ids if m not in preferred]
        ordered = preferred + rest
        self._logger.info(
            "Gemini text modelleri: count=%s first=%s",
            len(ordered),
            ordered[:3],
        )
        self._gemini_model_ids_cache = ordered[:8]
        return self._gemini_model_ids_cache

    def _call_gemini(
        self,
        system_prompt: str,
        user_text: str,
        api_key: str,
        *,
        max_output_tokens: int = 300,
        temperature: float = 0.2,
    ) -> str:
        """Google Gemini generateContent API (AIza + AQ. auth key uyumlu)."""
        last_error: Exception | None = None
        tried: list[str] = []
        headers, params = self._gemini_auth(api_key)
        for model_name in self._list_gemini_generate_models(api_key):
            tried.append(model_name)
            url = f"{_GEMINI_MODELS_URL}/{model_name}:generateContent"
            try:
                response = self._session.post(
                    url,
                    params=params or None,
                    headers=headers,
                    json={
                        "systemInstruction": {"parts": [{"text": system_prompt}]},
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": user_text}],
                            }
                        ],
                        "generationConfig": {
                            "temperature": temperature,
                            "maxOutputTokens": max_output_tokens,
                        },
                    },
                    timeout=_LLM_TIMEOUT_SECONDS,
                )
                if response.status_code in {400, 403, 404}:
                    detail = ""
                    try:
                        detail = str(response.json().get("error", {}).get("message", ""))[:160]
                    except Exception:  # noqa: BLE001
                        detail = (response.text or "")[:160]
                    last_error = requests.HTTPError(
                        f"Gemini {response.status_code} model={model_name}: {detail or response.reason}"
                    )
                    self._logger.warning("%s", last_error)
                    continue
                response.raise_for_status()
                payload = response.json()
                return str(payload["candidates"][0]["content"]["parts"][0]["text"])
            except requests.RequestException as exc:
                last_error = exc
                continue
        raise requests.RequestException(
            f"Gemini isteği başarısız (denenen: {', '.join(tried)}): {last_error}"
        )
