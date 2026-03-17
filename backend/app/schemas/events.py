from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventTopic(str, Enum):
    LOCATION_UPDATED = 'location.updated'
    GEOFENCE_TRANSITION = 'geofence.transition'
    INCIDENT_STATE_CHANGED = 'incident.state_changed'
    COMMAND_ACKNOWLEDGED = 'command.acknowledged'
    SUSPICIOUS_ACCESS_ALERT = 'suspicious_access.alert'
    INCIDENT_OFFLINE_CHECK = 'incident.offline_check'
    COMMAND_PENDING_CHECK = 'command.pending_check'


class PlatformEventEnvelope(BaseModel):
    topic: EventTopic
    org_id: UUID | None = None
    entity_type: str
    entity_id: str
    producer: str
    occurred_at: datetime
    idempotency_key: str = Field(min_length=8, max_length=160)
    payload: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, Any] = Field(default_factory=dict)
    available_at: datetime | None = None


class LocationUpdatedPayload(BaseModel):
    location_event_id: UUID
    device_id: UUID
    mode: str
    captured_at: datetime
    precision: str
    confidence_score: int | None = None
    rule_matches: list[str] = Field(default_factory=list)
    suspicious_alerts: list[str] = Field(default_factory=list)


class GeofenceTransitionPayload(BaseModel):
    geofence_event_id: UUID
    geofence_id: UUID
    device_id: UUID
    event_type: str
    alert_emitted: bool
    precision: str
    confidence_score: int | None = None


class IncidentStateChangedPayload(BaseModel):
    incident_id: UUID
    device_id: UUID
    state: str
    action: str
    lost_mode_until: datetime | None = None
    active_incident: bool = True


class CommandAcknowledgedPayload(BaseModel):
    remote_action_id: UUID
    device_id: UUID
    incident_id: UUID | None = None
    status: str
    attempt_count: int
    expires_at: datetime | None = None
    error_message: str | None = None


class SuspiciousAccessAlertPayload(BaseModel):
    device_id: UUID
    actor_sub: str
    result: str
    reason: str | None = None
    request_id: str | None = None
    lookup_count: int = 0
    denied_count: int = 0
    distinct_device_count: int = 0
    unusual_activity: bool = False


class IncidentOfflineCheckPayload(BaseModel):
    incident_id: UUID
    device_id: UUID
    expected_latest_captured_at: datetime | None = None
    threshold_minutes: int


class CommandPendingCheckPayload(BaseModel):
    remote_action_id: UUID
    device_id: UUID
    incident_id: UUID | None = None
    retry_after_seconds: int
