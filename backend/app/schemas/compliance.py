from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RetentionPolicyResponse(BaseModel):
    location_event_days: int
    audit_log_days: int
    incident_evidence_days: int


class PrivacyDefaultsResponse(BaseModel):
    explicit_consent_required: bool = True
    visible_app_required: bool = True
    background_location_requires_explanation: bool = True
    owner_access_history_visible: bool = True
    approximate_locations_clearly_labeled: bool = True
    short_retention_default: bool = True


class PlatformSettingsResponse(BaseModel):
    org_id: UUID
    timezone: str
    default_map_provider: str
    retention_policy: RetentionPolicyResponse
    privacy_defaults: PrivacyDefaultsResponse
    updated_at: datetime | None = None
    updated_by_sub: str | None = None


class RetentionPolicyUpdateRequest(BaseModel):
    org_id: UUID
    location_event_days: int = Field(ge=7, le=365)
    audit_log_days: int = Field(ge=30, le=730)
    incident_evidence_days: int = Field(ge=14, le=730)
    reason: str = Field(min_length=8, max_length=280)


class AccessHistoryEntryResponse(BaseModel):
    audit_log_id: UUID
    actor_sub: str
    action: str
    occurred_at: datetime
    reason: str | None = None
    result: str | None = None
    metadata: dict = Field(default_factory=dict)


class AbuseReportCreateRequest(BaseModel):
    org_id: UUID
    device_id: UUID | None = None
    category: str = Field(min_length=3, max_length=64)
    description: str = Field(min_length=8, max_length=2000)
    contact_email: str | None = Field(default=None, max_length=200)


class AbuseReportResponse(BaseModel):
    abuse_report_id: UUID
    org_id: UUID
    device_id: UUID | None
    category: str
    description: str
    contact_email: str | None
    reported_by_sub: str
    status: str
    created_at: datetime


class DeprovisionDeviceRequest(BaseModel):
    reason: str = Field(min_length=8, max_length=280)


class DeprovisionDeviceResponse(BaseModel):
    deprovision_request_id: UUID
    org_id: UUID
    device_id: UUID
    requested_by_sub: str
    status: str
    reason: str
    created_at: datetime
    completed_at: datetime | None
