from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AccessReview,
    AccessReviewStatus,
    Device,
    DeviceAccessPolicy,
    DeviceKey,
    DeviceOwnershipBinding,
    Enrollment,
    EnrollmentStatus,
    PairingToken,
    OwnershipProofKind,
    OwnershipTransfer,
    OwnershipTransferStatus,
    OwnershipType,
    User,
    UserRole,
    LocationEvent,
)
from app.schemas.ownership import (
    AccessReviewCreateRequest,
    AccessReviewDecisionRequest,
    DeviceAccessPolicyUpdateRequest,
    DeviceIdentityVerifyRequest,
    EnrollmentRevokeRequest,
    OwnershipTransferDecisionRequest,
    OwnershipTransferRequest,
    PairingCompleteRequest,
    PairingTokenIssueRequest,
)


@dataclass
class LocateAuthorizationResult:
    allowed: bool
    reason: str
    owner_subject: str | None


class OwnershipAccessService:
    def hash_pairing_token(self, token: str) -> str:
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    def parse_pairing_token(self, token_or_uri: str) -> str:
        if '://' not in token_or_uri:
            return token_or_uri.strip()
        parsed = urlparse(token_or_uri)
        query = parse_qs(parsed.query)
        token_values = query.get('token', [])
        if token_values:
            return token_values[0].strip()
        return token_or_uri.strip()

    async def issue_pairing_token(
        self,
        session: AsyncSession,
        payload: PairingTokenIssueRequest,
        *,
        issued_by_sub: str,
    ) -> tuple[PairingToken, str]:
        if payload.device_id is not None:
            device = await self.get_device(session, payload.device_id)
            if device.organization_id != payload.org_id:
                raise ValueError('Device does not belong to tenant org.')

        owner_user = await self._resolve_user_by_subject(session, payload.org_id, payload.owner_subject)
        raw_token = secrets.token_urlsafe(24)
        record = PairingToken(
            org_id=payload.org_id,
            device_id=payload.device_id,
            owner_user_id=owner_user.id if owner_user else None,
            enrollment_type=payload.enrollment_type,
            ownership_type=payload.ownership_type,
            token_hash=self.hash_pairing_token(raw_token),
            token_hint=raw_token[-6:],
            issued_by_sub=issued_by_sub,
            proof_kind=payload.proof_kind,
            consent_version=payload.consent_version,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=payload.expires_in_minutes),
            created_at=datetime.now(timezone.utc),
            consumed_at=None,
            revoked_at=None,
        )
        session.add(record)
        await session.flush()
        return record, raw_token

    async def complete_pairing(
        self,
        session: AsyncSession,
        payload: PairingCompleteRequest,
    ) -> tuple[Device, Enrollment, DeviceOwnershipBinding, DeviceAccessPolicy, DeviceKey, PairingToken, str | None]:
        raw_token = self.parse_pairing_token(payload.token or payload.qr_payload or '')
        token_hash = self.hash_pairing_token(raw_token)
        token = (
            await session.execute(select(PairingToken).where(PairingToken.token_hash == token_hash))
        ).scalar_one_or_none()
        if token is None:
            raise ValueError('Invalid pairing token.')
        now = datetime.now(timezone.utc)
        if token.revoked_at is not None:
            raise ValueError('Pairing token has been revoked.')
        if token.consumed_at is not None:
            raise ValueError('Pairing token has already been used.')
        if token.expires_at < now:
            raise ValueError('Pairing token has expired.')
        if not payload.public_key_pem.strip().startswith('-----BEGIN'):
            raise ValueError('public_key_pem must be PEM encoded.')

        device: Device
        if token.device_id is not None:
            device = await self.get_device(session, token.device_id)
            active_enrollment = await self.get_active_enrollment(session, device.id)
            if active_enrollment is not None:
                raise ValueError('Device is already actively enrolled.')
        else:
            device = Device(
                organization_id=token.org_id,
                alias=payload.alias,
                enrollment_type=token.enrollment_type,
                is_policy_managed=token.enrollment_type.value == 'org_managed',
                consent_version=token.consent_version,
                enrolled_at=now,
            )
            session.add(device)
            await session.flush()

        owner_user = await self._resolve_owner_for_pairing(session, token, payload)
        enrollment = Enrollment(
            org_id=token.org_id,
            device_id=device.id,
            status=EnrollmentStatus.ACTIVE,
            consent_version=token.consent_version,
            enrolled_by_sub=f'device:{payload.key_id}',
            created_at=now,
            revoked_at=None,
        )
        session.add(enrollment)
        await session.flush()

        binding = DeviceOwnershipBinding(
            org_id=token.org_id,
            device_id=device.id,
            owner_user_id=owner_user.id if owner_user else None,
            ownership_type=token.ownership_type,
            proof_kind=OwnershipProofKind.QR_CODE if payload.qr_payload else token.proof_kind,
            proof_reference=token.token_hint,
            consent_version=token.consent_version,
            consent_captured_at=now,
            bound_by_sub=f'device:{payload.key_id}',
            is_active=True,
            created_at=now,
            ended_at=None,
        )
        session.add(binding)
        await session.flush()

        existing_policy = await self.get_policy(session, device.id)
        if existing_policy is None:
            policy = DeviceAccessPolicy(
                org_id=token.org_id,
                device_id=device.id,
                owner_can_locate=token.ownership_type == OwnershipType.SINGLE_USER,
                admin_can_locate=True,
                security_operator_can_review=True,
                require_access_review=False,
                created_at=now,
                updated_at=now,
            )
            session.add(policy)
            await session.flush()
        else:
            policy = existing_policy
            policy.owner_can_locate = token.ownership_type == OwnershipType.SINGLE_USER
            policy.admin_can_locate = True
            policy.security_operator_can_review = True
            policy.updated_at = now

        await session.execute(
            update(DeviceKey)
            .where(DeviceKey.device_id == device.id, DeviceKey.is_active.is_(True))
            .values(is_active=False, rotated_at=now)
        )
        device_key = DeviceKey(
            org_id=token.org_id,
            device_id=device.id,
            key_id=payload.key_id,
            public_key_pem=payload.public_key_pem,
            algorithm=payload.algorithm,
            is_active=True,
            created_at=now,
            rotated_at=None,
        )
        session.add(device_key)
        token.consumed_at = now
        await session.flush()
        return device, enrollment, binding, policy, device_key, token, owner_user.subject if owner_user else None

    async def get_device(self, session: AsyncSession, device_id: UUID) -> Device:
        device = (await session.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
        if device is None:
            raise ValueError('Unknown device_id')
        return device

    async def get_active_enrollment(self, session: AsyncSession, device_id: UUID) -> Enrollment | None:
        return (
            await session.execute(
                select(Enrollment)
                .where(Enrollment.device_id == device_id, Enrollment.status == EnrollmentStatus.ACTIVE)
                .order_by(desc(Enrollment.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def get_active_binding(self, session: AsyncSession, device_id: UUID) -> DeviceOwnershipBinding | None:
        return (
            await session.execute(
                select(DeviceOwnershipBinding)
                .where(DeviceOwnershipBinding.device_id == device_id, DeviceOwnershipBinding.is_active.is_(True))
                .order_by(desc(DeviceOwnershipBinding.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def get_policy(self, session: AsyncSession, device_id: UUID) -> DeviceAccessPolicy | None:
        return (
            await session.execute(select(DeviceAccessPolicy).where(DeviceAccessPolicy.device_id == device_id))
        ).scalar_one_or_none()

    async def update_access_policy(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        payload: DeviceAccessPolicyUpdateRequest,
    ) -> DeviceAccessPolicy:
        await self._assert_device_org(session, device_id, org_id)
        policy = await self.get_policy(session, device_id)
        now = datetime.now(timezone.utc)
        if policy is None:
            policy = DeviceAccessPolicy(
                org_id=org_id,
                device_id=device_id,
                owner_can_locate=payload.owner_can_locate,
                admin_can_locate=payload.admin_can_locate,
                security_operator_can_review=payload.security_operator_can_review,
                require_access_review=payload.require_access_review,
                created_at=now,
                updated_at=now,
            )
            session.add(policy)
        else:
            policy.owner_can_locate = payload.owner_can_locate
            policy.admin_can_locate = payload.admin_can_locate
            policy.security_operator_can_review = payload.security_operator_can_review
            policy.require_access_review = payload.require_access_review
            policy.updated_at = now
        await session.flush()
        return policy

    async def request_transfer(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        requested_by_sub: str,
        payload: OwnershipTransferRequest,
    ) -> OwnershipTransfer:
        await self._assert_device_org(session, device_id, org_id)
        current_binding = await self.get_active_binding(session, device_id)
        if current_binding is None:
            raise ValueError('Device has no active ownership binding.')
        to_owner = await self._resolve_user_by_subject(session, org_id, payload.new_owner_subject)
        if payload.new_ownership_type == OwnershipType.SINGLE_USER and to_owner is None:
            raise ValueError('new_owner_subject is required for single-user ownership.')
        transfer = OwnershipTransfer(
            org_id=org_id,
            device_id=device_id,
            from_owner_user_id=current_binding.owner_user_id,
            to_owner_user_id=to_owner.id if to_owner else None,
            requested_by_sub=requested_by_sub,
            approved_by_sub=None,
            status=OwnershipTransferStatus.PENDING,
            reason=payload.reason,
            created_at=datetime.now(timezone.utc),
            decided_at=None,
        )
        session.add(transfer)
        await session.flush()
        return transfer

    async def decide_transfer(
        self,
        session: AsyncSession,
        *,
        transfer_id: UUID,
        approver_sub: str,
        payload: OwnershipTransferDecisionRequest,
    ) -> OwnershipTransfer:
        transfer = (
            await session.execute(select(OwnershipTransfer).where(OwnershipTransfer.id == transfer_id))
        ).scalar_one_or_none()
        if transfer is None:
            raise ValueError('Unknown transfer_id')
        if transfer.status != OwnershipTransferStatus.PENDING:
            raise ValueError('Transfer has already been decided.')
        now = datetime.now(timezone.utc)
        transfer.approved_by_sub = approver_sub
        transfer.decided_at = now
        if not payload.approve:
            transfer.status = OwnershipTransferStatus.REJECTED
            await session.flush()
            return transfer

        binding = await self.get_active_binding(session, transfer.device_id)
        if binding is None:
            raise ValueError('Device has no active ownership binding.')
        binding.is_active = False
        binding.ended_at = now

        new_binding = DeviceOwnershipBinding(
            org_id=transfer.org_id,
            device_id=transfer.device_id,
            owner_user_id=transfer.to_owner_user_id,
            ownership_type=OwnershipType.SINGLE_USER if transfer.to_owner_user_id else OwnershipType.ORGANIZATION_OWNED,
            proof_kind=OwnershipProofKind.TRANSFER_APPROVAL,
            proof_reference=str(transfer.id),
            consent_version=binding.consent_version,
            consent_captured_at=now,
            bound_by_sub=approver_sub,
            is_active=True,
            created_at=now,
            ended_at=None,
        )
        session.add(new_binding)
        transfer.status = OwnershipTransferStatus.APPROVED
        await session.flush()
        return transfer

    async def create_access_review(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        requested_by_sub: str,
        payload: AccessReviewCreateRequest,
    ) -> AccessReview:
        await self._assert_device_org(session, device_id, org_id)
        review = AccessReview(
            org_id=org_id,
            device_id=device_id,
            requested_by_sub=requested_by_sub,
            reviewed_by_sub=None,
            status=AccessReviewStatus.PENDING,
            rationale=payload.rationale,
            review_notes=None,
            created_at=datetime.now(timezone.utc),
            reviewed_at=None,
        )
        session.add(review)
        policy = await self.get_policy(session, device_id)
        if policy is not None:
            policy.require_access_review = True
            policy.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return review

    async def list_access_reviews(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID | None = None,
        status: AccessReviewStatus | None = None,
    ) -> list[AccessReview]:
        stmt = select(AccessReview).where(AccessReview.org_id == org_id)
        if device_id is not None:
            stmt = stmt.where(AccessReview.device_id == device_id)
        if status is not None:
            stmt = stmt.where(AccessReview.status == status)
        stmt = stmt.order_by(desc(AccessReview.created_at))
        return list((await session.execute(stmt)).scalars().all())

    async def decide_access_review(
        self,
        session: AsyncSession,
        *,
        access_review_id: UUID,
        reviewed_by_sub: str,
        payload: AccessReviewDecisionRequest,
    ) -> tuple[AccessReview, DeviceAccessPolicy | None]:
        review = (
            await session.execute(select(AccessReview).where(AccessReview.id == access_review_id))
        ).scalar_one_or_none()
        if review is None:
            raise ValueError('Unknown access_review_id')
        if review.status != AccessReviewStatus.PENDING:
            raise ValueError('Access review already decided.')
        review.status = AccessReviewStatus.APPROVED if payload.approve else AccessReviewStatus.REJECTED
        review.reviewed_by_sub = reviewed_by_sub
        review.review_notes = payload.review_notes
        review.reviewed_at = datetime.now(timezone.utc)
        policy = await self.get_policy(session, review.device_id)
        if policy is not None:
            policy.require_access_review = not payload.approve
            if not payload.approve:
                policy.admin_can_locate = False
            policy.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return review, policy

    async def revoke_enrollment(
        self,
        session: AsyncSession,
        *,
        enrollment_id: UUID,
        _payload: EnrollmentRevokeRequest,
    ) -> Enrollment:
        enrollment = (
            await session.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
        ).scalar_one_or_none()
        if enrollment is None:
            raise ValueError('Unknown enrollment_id')
        enrollment.status = EnrollmentStatus.REVOKED
        enrollment.revoked_at = datetime.now(timezone.utc)
        binding = await self.get_active_binding(session, enrollment.device_id)
        if binding is not None:
            binding.is_active = False
            binding.ended_at = datetime.now(timezone.utc)
        await session.flush()
        return enrollment

    async def locate_device(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
    ) -> LocationEvent | None:
        await self._assert_device_org(session, device_id, org_id)
        return (
            await session.execute(
                select(LocationEvent)
                .where(LocationEvent.org_id == org_id, LocationEvent.device_id == device_id)
                .order_by(desc(LocationEvent.captured_at))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def verify_device_identity(
        self,
        session: AsyncSession,
        payload: DeviceIdentityVerifyRequest,
    ) -> tuple[bool, bool, bool]:
        await self._assert_device_org(session, payload.device_id, payload.org_id)
        key = (
            await session.execute(
                select(DeviceKey).where(
                    DeviceKey.org_id == payload.org_id,
                    DeviceKey.device_id == payload.device_id,
                    DeviceKey.key_id == payload.key_id,
                    DeviceKey.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        enrollment = await self.get_active_enrollment(session, payload.device_id)
        binding = await self.get_active_binding(session, payload.device_id)
        return key is not None, enrollment is not None, binding is not None

    def authorize_locate(
        self,
        *,
        principal_roles: set[str],
        principal_subject: str,
        owner_subject: str | None,
        policy: DeviceAccessPolicy | None,
    ) -> LocateAuthorizationResult:
        if policy is None:
            return LocateAuthorizationResult(False, 'missing_access_policy', owner_subject)

        if 'super_admin' in principal_roles or 'org_admin' in principal_roles or 'admin' in principal_roles:
            if policy.admin_can_locate:
                return LocateAuthorizationResult(True, 'admin_allowed', owner_subject)
            return LocateAuthorizationResult(False, 'admin_policy_denied', owner_subject)

        if 'owner' in principal_roles:
            if owner_subject is None or owner_subject != principal_subject:
                return LocateAuthorizationResult(False, 'owner_binding_mismatch', owner_subject)
            if not policy.owner_can_locate:
                return LocateAuthorizationResult(False, 'owner_policy_denied', owner_subject)
            return LocateAuthorizationResult(True, 'owner_allowed', owner_subject)

        return LocateAuthorizationResult(False, 'role_not_allowed', owner_subject)

    async def get_owner_subject(self, session: AsyncSession, binding: DeviceOwnershipBinding | None) -> str | None:
        if binding is None or binding.owner_user_id is None:
            return None
        user = (await session.execute(select(User).where(User.id == binding.owner_user_id))).scalar_one_or_none()
        return user.subject if user else None

    async def _assert_device_org(self, session: AsyncSession, device_id: UUID, org_id: UUID) -> None:
        device = await self.get_device(session, device_id)
        if device.organization_id != org_id:
            raise ValueError('Device does not belong to tenant org.')

    async def _resolve_owner_for_pairing(
        self,
        session: AsyncSession,
        token: PairingToken,
        payload: PairingCompleteRequest,
    ) -> User | None:
        if token.ownership_type == OwnershipType.ORGANIZATION_OWNED:
            return None
        if token.owner_user_id is not None:
            owner = (await session.execute(select(User).where(User.id == token.owner_user_id))).scalar_one_or_none()
            if owner is None:
                raise ValueError('Token owner is missing.')
            if payload.owner_subject and payload.owner_subject != owner.subject:
                raise ValueError('owner_subject does not match token owner.')
            return owner
        if not payload.owner_subject:
            raise ValueError('owner_subject is required for single-user ownership.')
        owner = await self._resolve_user_by_subject(session, token.org_id, payload.owner_subject)
        if owner is None:
            raise ValueError('Unknown owner_subject for tenant org.')
        return owner

    async def _resolve_user_by_subject(self, session: AsyncSession, org_id: UUID, subject: str | None) -> User | None:
        if subject is None:
            return None
        return (
            await session.execute(
                select(User).where(User.org_id == org_id, User.subject == subject, User.is_active.is_(True))
            )
        ).scalar_one_or_none()
