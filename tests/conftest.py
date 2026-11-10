"""Paylaşılan test fixture'ları."""

from __future__ import annotations

import pytest

from core.config import get_settings

TEST_API_SECRET_KEY = "test-aerovantage-integration-key"


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tüm testlerde tutarlı ve deterministik ortam değişkenleri kullan."""
    monkeypatch.setenv("API_SECRET_KEY", TEST_API_SECRET_KEY)
    monkeypatch.setenv("EPIAS_USE_MOCK", "true")
    monkeypatch.setenv("WEATHER_USE_MOCK", "true")
    monkeypatch.setenv("SCADA_USE_MOCK", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Yetkili API istekleri için Bearer başlığı."""
    return {"Authorization": f"Bearer {TEST_API_SECRET_KEY}"}
