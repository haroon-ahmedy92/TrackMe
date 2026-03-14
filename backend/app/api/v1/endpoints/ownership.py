from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.db.models import AccessReviewStatus

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_log_service, get_ownership_access_service
from app.core.security import Principal, Role, require_roles
from app.db.base import get_db_session
from app.schemas.ownership import (
    AccessReviewCreateRequest,
    AccessReviewDecisionRequest,
    AccessReviewResponse,
    DeviceAccessPolicyResponse,
    DeviceAccessPolicyUpdateRequest,
    DeviceIdentityVerifyRequest,
    DeviceIdentityVerifyResponse,
    EnrollmentRevokeRequest,
    LocateDeviceRequest,
    LocateDeviceResponse,
    OwnershipBindingResponse,
    OwnershipTransferDecisionRequest,
    OwnershipTransferRequest,
    OwnershipTransferResponse,
    PairingCompleteRequest,
    PairingTokenIssueRequest,
    PairingTokenIssueResponse,
)
from app.services.audit_log_service import AuditLogService
from app.services.ownership_access_service import OwnershipAccessService

router = APIRouter(prefix='/ownership', tags=['ownership'])


@router.post('/pairing-tokens', response_model=PairingTokenIssueResponse)
async def issue_pairing_token(
    payload: PairingTokenIssueRequest,
    principal: Principal = Depends(require_roles(Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> PairingTokenIssueResponse:
    _assert_org_access(principal, payload.org_id)
    try:
        token_record, token = await ownership_service.issue_pairing_token(
            session,
            payload,
            issued_by_sub=principal.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='ENROLLMENT_TOKEN_ISSUED',
        entity_type='pairing_token',
        entity_id=str(token_record.id),
        metadata={
            'device_id': str(payload.device_id) if payload.device_id else None,
            'owner_subject': payload.owner_subject,
            'ownership_type': payload.ownership_type.value,
            'enrollment_type': payload.enrollment_type.value,
            'expires_at': token_record.expires_at.isoformat(),
        },
    )
    await session.commit()
    pairing_uri = f'trackme://pair?token={token}'
    return PairingTokenIssueResponse(
        pairing_token_id=token_record.id,
        org_id=token_record.org_id,
        device_id=token_record.device_id,
        token=token,
        token_hint=token_record.token_hint,
        pairing_uri=pairing_uri,
        expires_at=token_record.expires_at,
    )


@router.post('/pairings/complete', response_model=OwnershipBindingResponse)
async def complete_pairing(
    payload: PairingCompleteRequest,
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> OwnershipBindingResponse:
    try:
        device, enrollment, binding, policy, device_key, token_record, owner_subject = await ownership_service.complete_pairing(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    actor_sub = f'device:{payload.key_id}'
    for action, entity_type, entity_id, metadata in [
        (
            'DEVICE_PAIRED',
            'device',
            str(device.id),
            {
                'pairing_token_id': str(token_record.id),
                'device_key_id': device_key.key_id,
                'ownership_type': binding.ownership_type.value,
                'owner_subject': owner_subject,
            },
        ),
        (
            'ENROLLMENT_APPROVED',
            'enrollment',
            str(enrollment.id),
            {
                'device_id': str(device.id),
                'consent_version': enrollment.consent_version,
            },
        ),
        (
            'OWNERSHIP_BOUND',
            'ownership_binding',
            str(binding.id),
            {
                'device_id': str(device.id),
                'owner_subject': owner_subject,
                'proof_kind': binding.proof_kind.value,
            },
        ),
        (
            'DEVICE_KEY_REGISTERED',
            'device_key',
            str(device_key.id),
            {
                'device_id': str(device.id),
                'key_id': device_key.key_id,
                'algorithm': device_key.algorithm,
            },
        ),
        (
            'ACCESS_POLICY_CREATED',
            'device_access_policy',
            str(policy.id),
            {
                'device_id': str(device.id),
                'owner_can_locate': policy.owner_can_locate,
                'admin_can_locate': policy.admin_can_locate,
                'require_access_review': policy.require_access_review,
            },
        ),
    ]:
        await audit_log_service.append(
            session,
            org_id=str(binding.org_id),
            actor_sub=actor_sub,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )

    await session.commit()
    return _binding_response(binding, owner_subject)


@router.get('/devices/{device_id}/binding', response_model=OwnershipBindingResponse)
async def get_active_binding(
    device_id: UUID,
    org_id: UUID,
    principal: Principal = Depends(require_roles(Role.OWNER, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN, Role.SECURITY, Role.SECURITY_OPERATOR)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
) -> OwnershipBindingResponse:
    _assert_org_access(principal, org_id)
    binding = await ownership_service.get_active_binding(session, device_id)
    if binding is None or binding.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Active ownership binding not found')
    owner_subject = await ownership_service.get_owner_subject(session, binding)
    _assert_binding_visibility(principal, owner_subject)
    return _binding_response(binding, owner_subject)


@router.get('/devices/{device_id}/access-policy', response_model=DeviceAccessPolicyResponse)
async def get_access_policy(
    device_id: UUID,
    org_id: UUID,
    principal: Principal = Depends(require_roles(Role.OWNER, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN, Role.SECURITY, Role.SECURITY_OPERATOR)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
) -> DeviceAccessPolicyResponse:
    _assert_org_access(principal, org_id)
    binding = await ownership_service.get_active_binding(session, device_id)
    owner_subject = await ownership_service.get_owner_subject(session, binding)
    _assert_binding_visibility(principal, owner_subject)
    policy = await ownership_service.get_policy(session, device_id)
    if policy is None or policy.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Access policy not found')
    return _policy_response(policy)


@router.put('/devices/{device_id}/access-policy', response_model=DeviceAccessPolicyResponse)
async def update_access_policy(
    device_id: UUID,
    org_id: UUID,
    payload: DeviceAccessPolicyUpdateRequest,
    principal: Principal = Depends(require_roles(Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> DeviceAccessPolicyResponse:
    _assert_org_access(principal, org_id)
    try:
        policy = await ownership_service.update_access_policy(session, org_id=org_id, device_id=device_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await audit_log_service.append(
        session,
        org_id=str(org_id),
        actor_sub=principal.subject,
        action='ACCESS_POLICY_UPDATED',
        entity_type='device_access_policy',
        entity_id=str(policy.id),
        metadata={
            'device_id': str(device_id),
            'owner_can_locate': policy.owner_can_locate,
            'admin_can_locate': policy.admin_can_locate,
            'security_operator_can_review': policy.security_operator_can_review,
            'require_access_review': policy.require_access_review,
        },
    )
    await session.commit()
    return _policy_response(policy)


@router.post('/devices/{device_id}/transfers', response_model=OwnershipTransferResponse)
async def request_transfer(
    device_id: UUID,
    org_id: UUID,
    payload: OwnershipTransferRequest,
    principal: Principal = Depends(require_roles(Role.OWNER, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> OwnershipTransferResponse:
    _assert_org_access(principal, org_id)
    binding = await ownership_service.get_active_binding(session, device_id)
    owner_subject = await ownership_service.get_owner_subject(session, binding)
    if Role.OWNER in principal.roles and owner_subject != principal.subject:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Owner can only transfer devices they own')
    try:
        transfer = await ownership_service.request_transfer(
            session,
            org_id=org_id,
            device_id=device_id,
            requested_by_sub=principal.subject,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await audit_log_service.append(
        session,
        org_id=str(org_id),
        actor_sub=principal.subject,
        action='OWNERSHIP_TRANSFER_REQUESTED',
        entity_type='ownership_transfer',
        entity_id=str(transfer.id),
        metadata={
            'device_id': str(device_id),
            'new_owner_subject': payload.new_owner_subject,
            'new_ownership_type': payload.new_ownership_type.value,
            'reason': payload.reason,
        },
    )
    await session.commit()
    return _transfer_response(transfer)


@router.post('/transfers/{transfer_id}/decision', response_model=OwnershipTransferResponse)
async def decide_transfer(
    transfer_id: UUID,
    payload: OwnershipTransferDecisionRequest,
    principal: Principal = Depends(require_roles(Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> OwnershipTransferResponse:
    try:
        transfer = await ownership_service.decide_transfer(
            session,
            transfer_id=transfer_id,
            approver_sub=principal.subject,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    _assert_org_access(principal, transfer.org_id)
    await audit_log_service.append(
        session,
        org_id=str(transfer.org_id),
        actor_sub=principal.subject,
        action='OWNERSHIP_TRANSFER_APPROVED' if payload.approve else 'OWNERSHIP_TRANSFER_REJECTED',
        entity_type='ownership_transfer',
        entity_id=str(transfer.id),
        metadata={
            'device_id': str(transfer.device_id),
            'decision_reason': payload.decision_reason,
            'status': transfer.status.value,
        },
    )
    await session.commit()
    return _transfer_response(transfer)


@router.post('/devices/{device_id}/access-reviews', response_model=AccessReviewResponse)
async def create_access_review(
    device_id: UUID,
    org_id: UUID,
    payload: AccessReviewCreateRequest,
    principal: Principal = Depends(require_roles(Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> AccessReviewResponse:
    _assert_org_access(principal, org_id)
    try:
        review = await ownership_service.create_access_review(
            session,
            org_id=org_id,
            device_id=device_id,
            requested_by_sub=principal.subject,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await audit_log_service.append(
        session,
        org_id=str(org_id),
        actor_sub=principal.subject,
        action='ACCESS_REVIEW_REQUESTED',
        entity_type='access_review',
        entity_id=str(review.id),
        metadata={'device_id': str(device_id), 'rationale': payload.rationale},
    )
    await session.commit()
    return _review_response(review)


@router.get('/access-reviews', response_model=list[AccessReviewResponse])
async def list_access_reviews(
    org_id: UUID,
    device_id: UUID | None = None,
    review_status: AccessReviewStatus | None = None,
    principal: Principal = Depends(require_roles(Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN, Role.SECURITY, Role.SECURITY_OPERATOR)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
) -> list[AccessReviewResponse]:
    _assert_org_access(principal, org_id)
    reviews = await ownership_service.list_access_reviews(
        session,
        org_id=org_id,
        device_id=device_id,
        status=review_status,
    )
    return [_review_response(review) for review in reviews]


@router.post('/access-reviews/{access_review_id}/decision', response_model=AccessReviewResponse)
async def decide_access_review(
    access_review_id: UUID,
    payload: AccessReviewDecisionRequest,
    principal: Principal = Depends(require_roles(Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> AccessReviewResponse:
    try:
        review, _policy = await ownership_service.decide_access_review(
            session,
            access_review_id=access_review_id,
            reviewed_by_sub=principal.subject,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    _assert_org_access(principal, review.org_id)
    await audit_log_service.append(
        session,
        org_id=str(review.org_id),
        actor_sub=principal.subject,
        action='ACCESS_REVIEW_APPROVED' if payload.approve else 'ACCESS_REVIEW_REJECTED',
        entity_type='access_review',
        entity_id=str(review.id),
        metadata={'device_id': str(review.device_id), 'review_notes': payload.review_notes},
    )
    await session.commit()
    return _review_response(review)


@router.post('/enrollments/{enrollment_id}/revoke', response_model=OwnershipBindingResponse | dict)
async def revoke_enrollment(
    enrollment_id: UUID,
    payload: EnrollmentRevokeRequest,
    principal: Principal = Depends(require_roles(Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> OwnershipBindingResponse | dict:
    try:
        enrollment = await ownership_service.revoke_enrollment(session, enrollment_id=enrollment_id, _payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    _assert_org_access(principal, enrollment.org_id)
    binding = await ownership_service.get_active_binding(session, enrollment.device_id)
    owner_subject = await ownership_service.get_owner_subject(session, binding)
    await audit_log_service.append(
        session,
        org_id=str(enrollment.org_id),
        actor_sub=principal.subject,
        action='ENROLLMENT_REVOKED',
        entity_type='enrollment',
        entity_id=str(enrollment.id),
        metadata={'device_id': str(enrollment.device_id), 'reason': payload.reason},
    )
    await session.commit()
    if binding is None:
        return {'enrollment_id': str(enrollment.id), 'status': enrollment.status.value, 'owner_subject': owner_subject}
    return _binding_response(binding, owner_subject)


@router.post('/devices/{device_id}/locate', response_model=LocateDeviceResponse)
async def locate_device(
    request: Request,
    device_id: UUID,
    org_id: UUID,
    payload: LocateDeviceRequest,
    principal: Principal = Depends(require_roles(Role.OWNER, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> LocateDeviceResponse:
    _assert_org_access(principal, org_id)
    binding = await ownership_service.get_active_binding(session, device_id)
    owner_subject = await ownership_service.get_owner_subject(session, binding)
    policy = await ownership_service.get_policy(session, device_id)
    decision = ownership_service.authorize_locate(
        principal_roles={role.value for role in principal.roles},
        principal_subject=principal.subject,
        owner_subject=owner_subject,
        policy=policy,
    )
    action = 'LOCATION_LOOKUP_REQUESTED' if decision.allowed else 'LOCATION_LOOKUP_DENIED'
    await audit_log_service.append(
        session,
        org_id=str(org_id),
        actor_sub=principal.subject,
        action=action,
        entity_type='device',
        entity_id=str(device_id),
        metadata={
            'reason': payload.reason,
            'authorization_reason': decision.reason,
            'owner_subject': owner_subject,
            'result': 'denied' if not decision.allowed else 'requested',
            'device_id': str(device_id),
            'request_id': getattr(request.state, 'request_id', None),
        },
    )
    if not decision.allowed:
        await session.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Locate access denied')

    location = await ownership_service.locate_device(session, org_id=org_id, device_id=device_id)
    await audit_log_service.append(
        session,
        org_id=str(org_id),
        actor_sub=principal.subject,
        action='LOCATION_LOOKUP_RESULT',
        entity_type='device',
        entity_id=str(device_id),
        metadata={
            'reason': payload.reason,
            'result': 'no_location' if location is None else 'success',
            'device_id': str(device_id),
            'precision': location.precision.value if location else None,
            'confidence_score': location.confidence_score if location else None,
            'captured_at': location.captured_at.isoformat() if location else None,
            'request_id': getattr(request.state, 'request_id', None),
        },
    )
    await session.commit()
    return LocateDeviceResponse(
        device_id=device_id,
        org_id=org_id,
        requested_at=datetime.now(timezone.utc),
        precision=location.precision.value if location else None,
        confidence_score=location.confidence_score if location else None,
        is_approximate=bool(location.is_ip_approximate) if location else True,
        latitude=float(location.latitude) if location and location.latitude is not None else None,
        longitude=float(location.longitude) if location and location.longitude is not None else None,
        accuracy_meters=float(location.accuracy_meters) if location and location.accuracy_meters is not None else None,
        captured_at=location.captured_at if location else None,
        source_methods=list(location.source_methods.get('methods', [])) if location else [],
    )


@router.post('/device-identity/verify', response_model=DeviceIdentityVerifyResponse)
async def verify_device_identity(
    payload: DeviceIdentityVerifyRequest,
    principal: Principal = Depends(require_roles(Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN, Role.SECURITY, Role.SECURITY_OPERATOR)),
    session: AsyncSession = Depends(get_db_session),
    ownership_service: OwnershipAccessService = Depends(get_ownership_access_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> DeviceIdentityVerifyResponse:
    _assert_org_access(principal, payload.org_id)
    verified, enrollment_active, ownership_active = await ownership_service.verify_device_identity(session, payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='DEVICE_IDENTITY_VERIFIED',
        entity_type='device',
        entity_id=str(payload.device_id),
        metadata={'key_id': payload.key_id, 'verified': verified},
    )
    await session.commit()
    return DeviceIdentityVerifyResponse(
        verified=verified,
        org_id=payload.org_id,
        device_id=payload.device_id,
        key_id=payload.key_id,
        enrollment_active=enrollment_active,
        ownership_active=ownership_active,
        verified_at=datetime.now(timezone.utc),
    )


def _assert_org_access(principal: Principal, org_id: UUID) -> None:
    if Role.SUPER_ADMIN in principal.roles:
        return
    if principal.organization_id is None or principal.organization_id != str(org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')


def _assert_binding_visibility(principal: Principal, owner_subject: str | None) -> None:
    if Role.SUPER_ADMIN in principal.roles or Role.ADMIN in principal.roles or Role.ORG_ADMIN in principal.roles:
        return
    if Role.OWNER in principal.roles and owner_subject == principal.subject:
        return
    if Role.SECURITY in principal.roles or Role.SECURITY_OPERATOR in principal.roles:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Device access denied')


def _binding_response(binding, owner_subject: str | None) -> OwnershipBindingResponse:
    return OwnershipBindingResponse(
        ownership_binding_id=binding.id,
        org_id=binding.org_id,
        device_id=binding.device_id,
        owner_user_id=binding.owner_user_id,
        owner_subject=owner_subject,
        ownership_type=binding.ownership_type,
        proof_kind=binding.proof_kind,
        consent_version=binding.consent_version,
        consent_captured_at=binding.consent_captured_at,
        is_active=binding.is_active,
        created_at=binding.created_at,
        ended_at=binding.ended_at,
    )


def _policy_response(policy) -> DeviceAccessPolicyResponse:
    return DeviceAccessPolicyResponse(
        access_policy_id=policy.id,
        org_id=policy.org_id,
        device_id=policy.device_id,
        owner_can_locate=policy.owner_can_locate,
        admin_can_locate=policy.admin_can_locate,
        security_operator_can_review=policy.security_operator_can_review,
        require_access_review=policy.require_access_review,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def _transfer_response(transfer) -> OwnershipTransferResponse:
    return OwnershipTransferResponse(
        transfer_id=transfer.id,
        org_id=transfer.org_id,
        device_id=transfer.device_id,
        from_owner_user_id=transfer.from_owner_user_id,
        to_owner_user_id=transfer.to_owner_user_id,
        status=transfer.status,
        reason=transfer.reason,
        requested_by_sub=transfer.requested_by_sub,
        approved_by_sub=transfer.approved_by_sub,
        created_at=transfer.created_at,
        decided_at=transfer.decided_at,
    )


def _review_response(review) -> AccessReviewResponse:
    return AccessReviewResponse(
        access_review_id=review.id,
        org_id=review.org_id,
        device_id=review.device_id,
        requested_by_sub=review.requested_by_sub,
        reviewed_by_sub=review.reviewed_by_sub,
        status=review.status,
        rationale=review.rationale,
        review_notes=review.review_notes,
        created_at=review.created_at,
        reviewed_at=review.reviewed_at,
    )
