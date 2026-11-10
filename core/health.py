"""Sistem ve Data Hub + LLM sağlık izleme."""

from __future__ import annotations

from typing import Any

from core.logger import get_logger
from modules.ai.llm_health import LlmHealthClient
from modules.data_hub.epias import EpiasClient
from modules.data_hub.scada import ScadaClient
from modules.data_hub.weather import WeatherClient


class HealthMonitor:
    """Data Hub + LLM istemcilerinin erişilebilirlik durumunu izler."""

    def __init__(self) -> None:
        self._logger = get_logger("core.health")

    def check_data_hub(self) -> dict[str, dict[str, Any]]:
        """Tüm Data Hub + LLM ping sonuçlarını döndürür."""
        clients = {
            "weather": WeatherClient(),
            "epias": EpiasClient(),
            "scada": ScadaClient(),
            "gemini": LlmHealthClient(),
        }
        results = {name: client.ping() for name, client in clients.items()}
        # Sağlık anahtarı UI'da "gemini" — provider openai ise etiket yine ping'den gelir
        self._logger.info("Data Hub + LLM saglik kontrolu: %s", results)
        return results

    def get_overall_status(self) -> dict[str, Any]:
        """Genel sistem sağlık özeti."""
        data_hub = self.check_data_hub()
        all_ok = all(result.get("status") == "ok" for result in data_hub.values())
        return {
            "status": "ok" if all_ok else "degraded",
            "data_hub": data_hub,
        }
