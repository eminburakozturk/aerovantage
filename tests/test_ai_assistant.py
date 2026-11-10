"""AI asistanı — mock, LLM, action_plan ve fallback testleri."""

from __future__ import annotations

from unittest.mock import MagicMock

import requests

from core.config import Settings
from modules.ai.assistant import AIDecisionAssistant
from modules.ai.schemas import AIResponse


def test_mock_provider_returns_action_plan() -> None:
    assistant = AIDecisionAssistant(settings=Settings(llm_provider="mock"))
    result = assistant.generate_explanation(
        {
            "risk_score": 60,
            "total_imbalance_cost_tl": 4000,
            "forecast_mw": 30,
            "wind_speed_mps": 10,
        }
    )
    assert isinstance(result, AIResponse)
    assert result.insight.startswith("AI Analizi:")
    assert result.action_plan == "Pozisyonu azalt"


def test_llm_network_error_falls_back_to_playbook() -> None:
    session = MagicMock()
    session.post.side_effect = requests.Timeout("timeout")
    assistant = AIDecisionAssistant(
        settings=Settings(llm_provider="openai", llm_api_key="test-key"),
        session=session,
    )
    result = assistant.generate_explanation({"risk_score": 10, "forecast_mw": 5})
    assert "Sistem uyarısı: AI servisine ulaşılamadı" in result.insight
    assert result.action_plan


def test_openai_provider_parses_action_plan_json() -> None:
    session = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"insight": "Operasyon ekibini bilgilendirin.", '
                        '"action_plan": "Yedek kaynağı devreye al"}'
                    )
                }
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    session.post.return_value = mock_response

    assistant = AIDecisionAssistant(
        settings=Settings(llm_provider="openai", llm_api_key="test-key"),
        session=session,
    )
    result = assistant.generate_explanation({"risk_score": 45, "forecast_mw": 20})
    assert result.insight == "Operasyon ekibini bilgilendirin."
    assert result.action_plan == "Yedek kaynağı devreye al"
    session.post.assert_called_once()


if __name__ == "__main__":
    test_mock_provider_returns_action_plan()
    test_llm_network_error_falls_back_to_playbook()
    test_openai_provider_parses_action_plan_json()
    print("ALL_AI_ASSISTANT_TESTS_PASSED")
