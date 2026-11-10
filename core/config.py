"""Application configuration loaded securely from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["mock", "gemini", "openai"]


class Settings(BaseSettings):
    """Central configuration for AeroVantage."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="AeroVantage", description="Application display name")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Root log level",
    )
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent,
        description="Absolute path to project root",
    )

    epias_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="EPİAŞ legacy Bearer API key (TGT yoksa yedek)",
    )
    epias_username: SecretStr = Field(
        default=SecretStr(""),
        description="EPİAŞ Şeffaflık Platformu kullanıcı adı (TGT auth)",
    )
    epias_password: SecretStr = Field(
        default=SecretStr(""),
        description="EPİAŞ Şeffaflık Platformu şifresi (TGT auth)",
    )
    epias_cas_url: str = Field(
        default="https://giris.epias.com.tr/cas/v1/tickets",
        description="EPİAŞ CAS TGT alma endpoint'i",
    )
    epias_tgt_ttl_minutes: int = Field(
        default=90,
        ge=5,
        le=120,
        description="Önbelleğe alınan TGT geçerlilik süresi (dakika)",
    )
    epias_base_url: str = Field(
        default="https://seffaflik.epias.com.tr/electricity-service/v1",
        description="EPİAŞ transparency platform base URL",
    )
    epias_use_mock: bool = Field(
        default=False,
        description="Return mock EPİAŞ data until live endpoint is connected",
    )

    weather_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Meteoroloji servisi API anahtarı",
    )
    weather_use_mock: bool = Field(
        default=False,
        description="Return mock weather data until live API is connected",
    )

    scada_api_url: str = Field(
        default="",
        description="SCADA REST veya InfluxDB bağlantı adresi (örn. http://scada.local/api)",
    )
    scada_use_mock: bool = Field(
        default=True,
        description="Return mock SCADA data until live source is connected",
    )

    llm_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="LLM sağlayıcı API anahtarı",
    )
    llm_provider: LLMProvider = Field(
        default="mock",
        description="LLM sağlayıcısı: mock, gemini veya openai",
    )

    api_secret_key: SecretStr = Field(
        default=SecretStr(""),
        description="Bearer API anahtarı (/api/v1/*). Ortamda API_SECRET_KEY zorunlu; boş varsayılan yok.",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton)."""
    return Settings()


settings = get_settings()
