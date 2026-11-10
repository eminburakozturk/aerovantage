"""LLM health ping tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.config import Settings
from modules.ai.assistant import AIDecisionAssistant
from modules.ai.llm_health import LlmHealthClient, llm_meta_from_ai_source


def test_llm_meta_gemini_live() -> None:
    meta = llm_meta_from_ai_source("gemini")
    assert meta["mode"] == "live"
    assert meta["source"] == "gemini"


def test_llm_meta_fallback() -> None:
    meta = llm_meta_from_ai_source("fallback")
    assert meta["mode"] == "fallback"


def test_gemini_ping_live_with_models() -> None:
    session = MagicMock()
    session.get.return_value.status_code = 200
    session.get.return_value.json.return_value = {"models": [{"name": "models/gemini-2.5-flash"}]}
    client = LlmHealthClient(
        settings=Settings(llm_provider="gemini", llm_api_key="AQ.test"),
        session=session,
    )
    ping = client.ping()
    assert ping["mode"] == "live"
    assert ping["status"] == "ok"
    assert ping["source"] == "gemini"


def test_gemini_excludes_tts_models() -> None:
    assert AIDecisionAssistant._is_text_gemini_model("gemini-2.5-flash") is True
    assert AIDecisionAssistant._is_text_gemini_model("gemini-2.5-flash-preview-tts") is False
    assert AIDecisionAssistant._is_text_gemini_model("text-embedding-004") is False
