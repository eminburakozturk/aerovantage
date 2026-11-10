"""Data Integration Hub — dış veri kaynağı şemaları."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator, model_validator

from core.schemas import AeroVantageSchema, Timestamp
from modules.data_hub.errors import DataValidationError

_MIN_TEMPERATURE_C = -60.0
_MAX_TEMPERATURE_C = 60.0
_MAX_WIND_SPEED_MPS = 80.0
_MIN_AIR_PRESSURE_HPA = 800.0
_MAX_AIR_PRESSURE_HPA = 1100.0
_MIN_PTF_TL = Decimal("0")
_MAX_PTF_TL = Decimal("100000")
_MAX_GENERATION_MW = 10_000.0
_TURKEY_TZ = ZoneInfo("Europe/Istanbul")


def _delivery_day_parts(timestamp: datetime) -> tuple[date, int]:
    """UTC saklanan saatlik kaydı Türkiye teslimat günü/saatine çevirir."""
    if timestamp.tzinfo is None:
        local = timestamp.replace(tzinfo=_TURKEY_TZ)
    else:
        local = timestamp.astimezone(_TURKEY_TZ)
    return local.date(), local.hour


def validate_mw_range(value: Any, field_name: str = "generated_mw") -> float:
    """Üretim gücü (MW) için 0–10.000 aralık doğrulaması."""
    value = _reject_none(field_name, value)
    mw = float(value)
    if mw < 0 or mw > _MAX_GENERATION_MW:
        raise DataValidationError(
            f"{field_name} 0 ile {_MAX_GENERATION_MW} MW arasında olmalıdır"
        )
    return mw


def _reject_none(field_name: str, value: Any) -> Any:
    if value is None:
        raise DataValidationError(f"{field_name} alanı boş (None) olamaz")
    return value


def _validate_24h_hour_coverage(hours: list[Any], field_name: str) -> None:
    parsed_hours: list[int] = []
    for item in hours:
        hour_value = getattr(item, "hour", None)
        if hour_value is None:
            raise DataValidationError(f"{field_name} saat alanı eksik")
        parsed_hours.append(int(hour_value))
    unique = sorted(set(parsed_hours))
    if len(unique) != 24:
        raise DataValidationError(
            f"{field_name} tam 24 farklı saat içermelidir (bulunan={len(unique)})"
        )
    if unique != list(range(24)):
        raise DataValidationError(f"{field_name} saat kapsamı 0-23 tam aralığında olmalıdır")


class WeatherData(AeroVantageSchema):
    """Tek saatlik meteorolojik gözlem/tahmin kaydı."""

    timestamp: datetime = Field(..., description="Veri zaman damgası (UTC)")
    temperature: float = Field(..., description="Hava sıcaklığı (°C)")
    wind_speed: float = Field(..., ge=0, description="Rüzgar hızı (m/s)")
    wind_direction: float = Field(..., ge=0, lt=360, description="Rüzgar yönü (derece)")
    air_pressure: float = Field(..., gt=0, description="Atmosfer basıncı (hPa)")

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, value: Any) -> Any:
        value = _reject_none("timestamp", value)
        if not isinstance(value, datetime):
            raise DataValidationError("timestamp geçerli bir datetime olmalıdır")
        return value

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_temperature(cls, value: Any) -> float:
        value = _reject_none("temperature", value)
        temperature = float(value)
        if not _MIN_TEMPERATURE_C <= temperature <= _MAX_TEMPERATURE_C:
            raise DataValidationError(
                f"temperature {_MIN_TEMPERATURE_C} ile {_MAX_TEMPERATURE_C} °C arasında olmalıdır"
            )
        return temperature

    @field_validator("wind_speed", mode="before")
    @classmethod
    def validate_wind_speed(cls, value: Any) -> float:
        value = _reject_none("wind_speed", value)
        wind_speed = float(value)
        if wind_speed < 0 or wind_speed > _MAX_WIND_SPEED_MPS:
            raise DataValidationError(
                f"wind_speed 0 ile {_MAX_WIND_SPEED_MPS} m/s arasında olmalıdır"
            )
        return wind_speed

    @field_validator("wind_direction", mode="before")
    @classmethod
    def validate_wind_direction(cls, value: Any) -> float:
        value = _reject_none("wind_direction", value)
        direction = float(value) % 360
        if direction < 0 or direction >= 360:
            raise DataValidationError("wind_direction 0-360 derece aralığında olmalıdır")
        return direction

    @field_validator("air_pressure", mode="before")
    @classmethod
    def validate_air_pressure(cls, value: Any) -> float:
        value = _reject_none("air_pressure", value)
        pressure = float(value)
        if not _MIN_AIR_PRESSURE_HPA <= pressure <= _MAX_AIR_PRESSURE_HPA:
            raise DataValidationError(
                f"air_pressure {_MIN_AIR_PRESSURE_HPA}-{_MAX_AIR_PRESSURE_HPA} hPa aralığında olmalıdır"
            )
        return pressure


class WeatherForecastResponse(AeroVantageSchema):
    """Belirli konum ve tarih için saatlik meteorolojik tahmin seti."""

    latitude: float = Field(..., ge=-90, le=90, description="Enlem")
    longitude: float = Field(..., ge=-180, le=180, description="Boylam")
    target_date: date = Field(..., description="Tahmin teslimat tarihi")
    hours: List[WeatherData] = Field(..., min_length=1, description="Saatlik meteoroloji verileri")
    source: str = Field(default="weather", description="Veri kaynağı")

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def validate_coordinates(cls, value: Any) -> float:
        if value is None:
            raise DataValidationError("koordinat alanı boş (None) olamaz")
        return float(value)

    @field_validator("target_date", mode="before")
    @classmethod
    def validate_target_date(cls, value: Any) -> date:
        value = _reject_none("target_date", value)
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            return date.fromisoformat(value)
        raise DataValidationError("target_date geçerli bir tarih olmalıdır")

    @field_validator("hours", mode="before")
    @classmethod
    def validate_hours(cls, value: Any) -> list[Any]:
        if value is None:
            raise DataValidationError("hours alanı boş (None) olamaz")
        if not isinstance(value, list) or not value:
            raise DataValidationError("hours en az bir saatlik kayıt içermelidir")
        return value

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, value: Any) -> str:
        value = _reject_none("source", value)
        source = str(value).strip()
        if not source:
            raise DataValidationError("source boş olamaz")
        return source

    @model_validator(mode="after")
    def validate_hourly_weather_records(self) -> WeatherForecastResponse:
        if len(self.hours) != 24:
            raise DataValidationError("hours listesi tam 24 saatlik kayıt içermelidir")
        seen_hours: set[int] = set()
        for hour in self.hours:
            local_date, hour_idx = _delivery_day_parts(hour.timestamp)
            if local_date != self.target_date:
                raise DataValidationError("hours kayıtları target_date ile aynı gün olmalıdır")
            if hour_idx in seen_hours:
                raise DataValidationError(f"hours içinde tekrarlı saat tespit edildi: {hour_idx}")
            seen_hours.add(hour_idx)
        if seen_hours != set(range(24)):
            raise DataValidationError("hours saat kapsamı 0-23 tam aralığında olmalıdır")
        return self


class HourlyPTF(AeroVantageSchema):
    """Tek saatlik PTF (Piyasa Takas Fiyatı) kaydı."""

    hour: int = Field(..., ge=0, le=23, description="Teslimat saati (0–23)")
    ptf: Decimal = Field(..., ge=0, description="Piyasa Takas Fiyatı (TL/MWh)")

    @field_validator("hour", mode="before")
    @classmethod
    def validate_hour(cls, value: Any) -> int:
        value = _reject_none("hour", value)
        hour = int(value)
        if hour < 0 or hour > 23:
            raise DataValidationError("hour 0-23 aralığında olmalıdır")
        return hour

    @field_validator("ptf", mode="before")
    @classmethod
    def validate_ptf(cls, value: Any) -> Decimal:
        value = _reject_none("ptf", value)
        ptf = Decimal(str(value))
        if ptf < _MIN_PTF_TL or ptf > _MAX_PTF_TL:
            raise DataValidationError(
                f"ptf {_MIN_PTF_TL}-{_MAX_PTF_TL} TL/MWh aralığında olmalıdır"
            )
        return ptf


class DayAheadPTFResponse(AeroVantageSchema):
    """Bir teslimat gününe ait saatlik GOP/PTF veri seti."""

    delivery_date: date = Field(..., description="Teslimat tarihi")
    currency: str = Field(default="TRY", description="Para birimi")
    unit: str = Field(default="TL/MWh", description="Fiyat birimi")
    hours: List[HourlyPTF] = Field(..., min_length=1, description="Saatlik PTF listesi")
    fetched_at: Timestamp = Field(
        default_factory=Timestamp,
        description="Verinin alındığı zaman",
    )
    source: str = Field(default="epias", description="Veri kaynağı")

    @field_validator("delivery_date", mode="before")
    @classmethod
    def validate_delivery_date(cls, value: Any) -> date:
        value = _reject_none("delivery_date", value)
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            return date.fromisoformat(value)
        raise DataValidationError("delivery_date geçerli bir tarih olmalıdır")

    @field_validator("hours", mode="before")
    @classmethod
    def validate_hours(cls, value: Any) -> list[Any]:
        if value is None:
            raise DataValidationError("hours alanı boş (None) olamaz")
        if not isinstance(value, list) or not value:
            raise DataValidationError("hours en az bir saatlik PTF kaydı içermelidir")
        return value

    @field_validator("currency", "unit", "source", mode="before")
    @classmethod
    def validate_non_empty_text(cls, value: Any) -> str:
        value = _reject_none("metin_alanı", value)
        text = str(value).strip()
        if not text:
            raise DataValidationError("metin alanı boş olamaz")
        return text

    @model_validator(mode="after")
    def validate_hourly_coverage(self) -> DayAheadPTFResponse:
        _validate_24h_hour_coverage(self.hours, "PTF hours")
        return self


class HourlySMF(AeroVantageSchema):
    """Tek saatlik SMF (Sistem Marjinal Fiyat) kaydı."""

    hour: int = Field(..., ge=0, le=23, description="Teslimat saati (0–23)")
    smf: Decimal = Field(..., ge=0, description="Sistem Marjinal Fiyat (TL/MWh)")

    @field_validator("hour", mode="before")
    @classmethod
    def validate_hour(cls, value: Any) -> int:
        value = _reject_none("hour", value)
        hour = int(value)
        if hour < 0 or hour > 23:
            raise DataValidationError("hour 0-23 aralığında olmalıdır")
        return hour

    @field_validator("smf", mode="before")
    @classmethod
    def validate_smf(cls, value: Any) -> Decimal:
        value = _reject_none("smf", value)
        smf = Decimal(str(value))
        if smf < _MIN_PTF_TL or smf > _MAX_PTF_TL:
            raise DataValidationError(
                f"smf {_MIN_PTF_TL}-{_MAX_PTF_TL} TL/MWh aralığında olmalıdır"
            )
        return smf


class SystemMarginalPriceResponse(AeroVantageSchema):
    """Bir teslimat gününe ait saatlik SMF veri seti."""

    delivery_date: date = Field(..., description="Teslimat tarihi")
    currency: str = Field(default="TRY", description="Para birimi")
    unit: str = Field(default="TL/MWh", description="Fiyat birimi")
    hours: List[HourlySMF] = Field(..., min_length=1, description="Saatlik SMF listesi")
    fetched_at: Timestamp = Field(default_factory=Timestamp, description="Verinin alındığı zaman")
    source: str = Field(default="epias", description="Veri kaynağı")

    @model_validator(mode="after")
    def validate_hourly_coverage(self) -> SystemMarginalPriceResponse:
        _validate_24h_hour_coverage(self.hours, "SMF hours")
        return self
