from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Mode


class LocationSignalMethod(str, Enum):
    FUSED = 'fused'
    GPS = 'gps'
    NETWORK = 'network'
    IP_DERIVED = 'ip_derived'


class LocationSignalInput(BaseModel):
    method: LocationSignalMethod
    latitude: float
    longitude: float
    accuracy_meters: float = Field(gt=0)
    captured_at: datetime
    is_approximate: bool
    method_label: str = Field(min_length=1, max_length=120)


class TelemetryCheckInRequest(BaseModel):
    device_id: UUID
    mode: Mode
    checkin_at: datetime
    battery_percent: int | None = Field(default=None, ge=0, le=100)
    telemetry_signature: str | None = None
    telemetry_algorithm: str | None = None
    telemetry_key_id: str | None = None
    integrity_token: str | None = None
    signals: list[LocationSignalInput] = Field(default_factory=list)


class TelemetryCheckInResponse(BaseModel):
    accepted: bool
    selected_method_label: str | None = None
    selected_confidence_score: int | None = None
    selected_is_approximate: bool | None = None
