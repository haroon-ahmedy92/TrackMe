from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import RemoteActionKind, RemoteActionState


class CommandQueueRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    incident_id: UUID | None = None
    action_kind: RemoteActionKind
    reason: str = Field(min_length=2, max_length=250)
    lost_mode_until: datetime | None = None
    recovery_message: str | None = Field(default=None, max_length=280)
    delayed_until: datetime | None = None
    expires_at: datetime | None = None
    elevated_confirmation: bool = False
    acknowledge_wipe_tradeoff: bool = False


class CommandEnvelopeResponse(BaseModel):
    remote_action_id: UUID
    org_id: UUID
    device_id: UUID
    incident_id: UUID | None
    action_kind: RemoteActionKind
    state: RemoteActionState
    reason: str
    payload: dict
    signature: str
    signature_algorithm: str
    requested_by_sub: str
    requested_at: datetime
    expires_at: datetime | None


class DevicePushTokenRegisterRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    key_id: str = Field(min_length=4, max_length=80)
    push_token: str = Field(min_length=32, max_length=255)
    app_version: str | None = Field(default=None, max_length=40)


class DevicePushTokenResponse(BaseModel):
    push_token_id: UUID
    org_id: UUID
    device_id: UUID
    key_id: str
    is_active: bool
    last_seen_at: datetime


class DeviceCommandSyncRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    key_id: str = Field(min_length=4, max_length=80)


class CommandAckRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    key_id: str = Field(min_length=4, max_length=80)
    status: RemoteActionState
    error_message: str | None = Field(default=None, max_length=250)
    metadata: dict = Field(default_factory=dict)


class CommandAckResponse(BaseModel):
    remote_action_id: UUID
    status: RemoteActionState
    updated_at: datetime


class CommandRetryResponse(BaseModel):
    processed: int
    sent: int
    failed: int
    expired: int
