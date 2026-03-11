from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import IncidentState


class IncidentRecordOut(BaseModel):
    incident_id: UUID
    device_id: UUID
    ticket_reference: str
    state: IncidentState
    recovery_message: str
    wipe_scheduled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class IncidentTimelineEventOut(BaseModel):
    id: UUID
    incident_id: UUID
    state: IncidentState
    action: str
    summary: str
    metadata: dict
    occurred_at: datetime


class MarkDeviceLostRequest(BaseModel):
    device_id: UUID
    ticket_reference: str = Field(min_length=2, max_length=80)
    recovery_message: str = Field(min_length=2, max_length=280)
    lost_mode_window_hours: int = Field(default=12, ge=1, le=48)


class ConfirmStolenRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=250)
    elevated_confirmation: bool


class RemoteLockDecisionRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=250)


class RemoteWipeDecisionRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=250)
    elevated_confirmation: bool
    confirm_wipe_intent: bool
    acknowledge_tradeoff: bool
    delay_minutes: int = Field(default=0, ge=0, le=7 * 24 * 60)


class IncidentResolutionRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=250)
