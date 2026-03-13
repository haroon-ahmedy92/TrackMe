from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import (
    EnrollmentType,
    OwnershipProofKind,
    OwnershipTransferStatus,
    OwnershipType,
    AccessReviewStatus,
)


class PairingTokenIssueRequest(BaseModel):
    org_id: UUID
    device_id: UUID | None = None
    owner_subject: str | None = Field(default=None, min_length=2, max_length=150)
    enrollment_type: EnrollmentType
    ownership_type: OwnershipType
    consent_version: str = Field(min_length=1, max_length=40)
    expires_in_minutes: int = Field(default=30, ge=5, le=1440)
    proof_kind: OwnershipProofKind = OwnershipProofKind.ENROLLMENT_TOKEN


class PairingTokenIssueResponse(BaseModel):
    pairing_token_id: UUID
    org_id: UUID
    device_id: UUID | None
    token: str
    token_hint: str
    pairing_uri: str
    expires_at: datetime


class PairingCompleteRequest(BaseModel):
    token: str = Field(min_length=12, max_length=512)
    alias: str = Field(min_length=1, max_length=120)
    owner_subject: str | None = Field(default=None, min_length=2, max_length=150)
    public_key_pem: str = Field(min_length=16)
    key_id: str = Field(min_length=2, max_length=80)
    algorithm: str = Field(min_length=3, max_length=32)
    qr_payload: str | None = Field(default=None, max_length=512)


class OwnershipBindingResponse(BaseModel):
    ownership_binding_id: UUID
    org_id: UUID
    device_id: UUID
    owner_user_id: UUID | None
    owner_subject: str | None = None
    ownership_type: OwnershipType
    proof_kind: OwnershipProofKind
    consent_version: str
    consent_captured_at: datetime
    is_active: bool
    created_at: datetime
    ended_at: datetime | None


class DeviceAccessPolicyUpdateRequest(BaseModel):
    owner_can_locate: bool = True
    admin_can_locate: bool = True
    security_operator_can_review: bool = True
    require_access_review: bool = False


class DeviceAccessPolicyResponse(BaseModel):
    access_policy_id: UUID
    org_id: UUID
    device_id: UUID
    owner_can_locate: bool
    admin_can_locate: bool
    security_operator_can_review: bool
    require_access_review: bool
    created_at: datetime
    updated_at: datetime


class OwnershipTransferRequest(BaseModel):
    new_owner_subject: str | None = Field(default=None, min_length=2, max_length=150)
    new_ownership_type: OwnershipType
    reason: str = Field(min_length=4, max_length=280)


class OwnershipTransferDecisionRequest(BaseModel):
    approve: bool
    decision_reason: str = Field(min_length=4, max_length=280)


class OwnershipTransferResponse(BaseModel):
    transfer_id: UUID
    org_id: UUID
    device_id: UUID
    from_owner_user_id: UUID | None
    to_owner_user_id: UUID | None
    status: OwnershipTransferStatus
    reason: str
    requested_by_sub: str
    approved_by_sub: str | None
    created_at: datetime
    decided_at: datetime | None


class AccessReviewCreateRequest(BaseModel):
    rationale: str = Field(min_length=4, max_length=280)


class AccessReviewDecisionRequest(BaseModel):
    approve: bool
    review_notes: str = Field(min_length=4, max_length=280)


class AccessReviewResponse(BaseModel):
    access_review_id: UUID
    org_id: UUID
    device_id: UUID
    requested_by_sub: str
    reviewed_by_sub: str | None
    status: AccessReviewStatus
    rationale: str
    review_notes: str | None
    created_at: datetime
    reviewed_at: datetime | None


class EnrollmentRevokeRequest(BaseModel):
    reason: str = Field(min_length=4, max_length=280)


class LocateDeviceResponse(BaseModel):
    device_id: UUID
    org_id: UUID
    requested_at: datetime
    precision: str | None
    confidence_score: int | None
    is_approximate: bool
    latitude: float | None
    longitude: float | None
    accuracy_meters: float | None
    captured_at: datetime | None
    source_methods: list[str] = Field(default_factory=list)


class DeviceIdentityVerifyRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    key_id: str = Field(min_length=2, max_length=80)


class DeviceIdentityVerifyResponse(BaseModel):
    verified: bool
    org_id: UUID
    device_id: UUID
    key_id: str
    enrollment_active: bool
    ownership_active: bool
    verified_at: datetime
