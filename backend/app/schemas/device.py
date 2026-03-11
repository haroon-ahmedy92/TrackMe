from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class EnrollmentType(str, Enum):
    OWNER_ENROLLED = 'owner_enrolled'
    ORG_MANAGED = 'org_managed'


class DeviceEnrollmentRequest(BaseModel):
    alias: str = Field(min_length=1, max_length=120)
    enrollment_type: EnrollmentType
    consent_version: str = Field(min_length=1, max_length=40)
    organization_id: UUID | None = None
    is_policy_managed: bool = False


class DeviceEnrollmentResponse(BaseModel):
    device_id: UUID
    enrolled_at: datetime
