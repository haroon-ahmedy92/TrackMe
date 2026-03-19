from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AbuseReport,
    AuditLog,
    DeprovisionRequest,
    DeprovisionStatus,
    Device,
    DeviceAccessPolicy,
    DeviceOwnershipBinding,
    Enrollment,
    EnrollmentStatus,
    TenantSettings,
)
from app.schemas.compliance import AbuseReportCreateRequest, RetentionPolicyUpdateRequest


class ComplianceService:
    async def get_or_create_settings(self, session: AsyncSession, *, org_id: UUID) -> TenantSettings:
        settings = (
            await session.execute(select(TenantSettings).where(TenantSettings.org_id == org_id))
        ).scalar_one_or_none()
        if settings is not None:
            return settings

        settings = TenantSettings(
            org_id=org_id,
            location_event_days=self.default_location_event_days,
            audit_log_days=self.default_audit_log_days,
            incident_evidence_days=self.default_incident_evidence_days,
            locate_reason_min_length=self.default_locate_reason_min_length,
            require_incident_for_locate=False,
            lock_requires_active_incident=True,
            wipe_requires_policy_approval=True,
            wipe_requires_confirmed_stolen=True,
            high_risk_actions_require_two_person=True,
            evidence_export_requires_permission=True,
            updated_by_sub=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(settings)
        await session.flush()
        return settings

    async def update_retention_policy(
        self,
        session: AsyncSession,
        *,
        payload: RetentionPolicyUpdateRequest,
        actor_sub: str,
    ) -> TenantSettings:
        settings = await self.get_or_create_settings(session, org_id=payload.org_id)
        settings.location_event_days = payload.location_event_days
        settings.audit_log_days = payload.audit_log_days
        settings.incident_evidence_days = payload.incident_evidence_days
        settings.locate_reason_min_length = payload.locate_reason_min_length
        settings.require_incident_for_locate = payload.require_incident_for_locate
        settings.lock_requires_active_incident = payload.lock_requires_active_incident
        settings.wipe_requires_policy_approval = payload.wipe_requires_policy_approval
        settings.wipe_requires_confirmed_stolen = payload.wipe_requires_confirmed_stolen
        settings.high_risk_actions_require_two_person = payload.high_risk_actions_require_two_person
        settings.evidence_export_requires_permission = payload.evidence_export_requires_permission
        settings.updated_by_sub = actor_sub
        settings.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return settings

    async def list_access_history(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        limit: int = 50,
    ) -> list[AuditLog]:
        await self._assert_device_belongs(session, org_id=org_id, device_id=device_id)
        actions = [
            'LOCATION_LOOKUP_REQUESTED',
            'LOCATION_LOOKUP_DENIED',
            'LOCATION_LOOKUP_RESULT',
            'ACCESS_POLICY_UPDATED',
            'DEVICE_DEPROVISIONED',
            'ENROLLMENT_REVOKED',
        ]
        rows = (
            await session.execute(
                select(AuditLog)
                .where(
                    AuditLog.org_id == org_id,
                    AuditLog.entity_id == str(device_id),
                    AuditLog.action.in_(actions),
                )
                .order_by(AuditLog.occurred_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return list(rows)

    async def create_abuse_report(
        self,
        session: AsyncSession,
        *,
        payload: AbuseReportCreateRequest,
        reported_by_sub: str,
    ) -> AbuseReport:
        if payload.device_id is not None:
            await self._assert_device_belongs(session, org_id=payload.org_id, device_id=payload.device_id)
        report = AbuseReport(
            org_id=payload.org_id,
            device_id=payload.device_id,
            category=payload.category,
            description=payload.description,
            contact_email=payload.contact_email,
            reported_by_sub=reported_by_sub,
            status='submitted',
            created_at=datetime.now(timezone.utc),
        )
        session.add(report)
        await session.flush()
        return report

    async def deprovision_device(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        requested_by_sub: str,
        reason: str,
    ) -> DeprovisionRequest:
        await self._assert_device_belongs(session, org_id=org_id, device_id=device_id)
        now = datetime.now(timezone.utc)

        enrollment = (
            await session.execute(
                select(Enrollment)
                .where(
                    Enrollment.org_id == org_id,
                    Enrollment.device_id == device_id,
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                )
                .order_by(Enrollment.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if enrollment is not None:
            enrollment.status = EnrollmentStatus.REVOKED
            enrollment.revoked_at = now

        binding = (
            await session.execute(
                select(DeviceOwnershipBinding)
                .where(
                    DeviceOwnershipBinding.org_id == org_id,
                    DeviceOwnershipBinding.device_id == device_id,
                    DeviceOwnershipBinding.is_active.is_(True),
                )
                .order_by(DeviceOwnershipBinding.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if binding is not None:
            binding.is_active = False
            binding.ended_at = now

        policy = (
            await session.execute(
                select(DeviceAccessPolicy).where(
                    DeviceAccessPolicy.org_id == org_id,
                    DeviceAccessPolicy.device_id == device_id,
                )
            )
        ).scalar_one_or_none()
        if policy is not None:
            policy.owner_can_locate = False
            policy.admin_can_locate = False
            policy.require_access_review = True
            policy.updated_at = now

        request = DeprovisionRequest(
            org_id=org_id,
            device_id=device_id,
            requested_by_sub=requested_by_sub,
            reason=reason,
            status=DeprovisionStatus.COMPLETED,
            created_at=now,
            completed_at=now,
        )
        session.add(request)
        await session.flush()
        return request

    async def _assert_device_belongs(self, session: AsyncSession, *, org_id: UUID, device_id: UUID) -> Device:
        device = (
            await session.execute(select(Device).where(Device.id == device_id))
        ).scalar_one_or_none()
        if device is None:
            raise ValueError('Unknown device_id')
        if device.organization_id != org_id:
            raise ValueError('Device does not belong to tenant org.')
        return device

    @property
    def default_location_event_days(self) -> int:
        return 30

    @property
    def default_audit_log_days(self) -> int:
        return 90

    @property
    def default_incident_evidence_days(self) -> int:
        return 60

    @property
    def default_locate_reason_min_length(self) -> int:
        return 8
