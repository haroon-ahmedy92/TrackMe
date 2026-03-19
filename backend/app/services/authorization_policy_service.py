from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, Role
from app.db.models import (
    Device,
    DeviceAccessPolicy,
    DeviceOwnershipBinding,
    Incident,
    IncidentCaseState,
    OwnershipType,
    PolicyActionType,
    RemoteActionKind,
    TenantSettings,
    User,
)
from app.schemas.compliance import RetentionPolicyUpdateRequest
from app.schemas.platform import IncidentEvidenceExportRequest, RemoteActionCreateRequest


@dataclass
class PolicyDecision:
    action_type: PolicyActionType
    allowed: bool
    requires_approval: bool
    reason_code: str
    reason: str
    required_approvals: int = 0
    owner_subject: str | None = None
    incident_state: IncidentCaseState | None = None
    context: dict = field(default_factory=dict)


class AuthorizationPolicyService:
    async def evaluate_locate(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        principal: Principal,
        reason: str,
    ) -> PolicyDecision:
        settings = await self._get_or_default_settings(session, org_id)
        device = await self._get_device(session, org_id=org_id, device_id=device_id)
        binding = await self._get_active_binding(session, org_id=org_id, device_id=device_id)
        owner_subject = await self._get_owner_subject(session, binding)
        policy = await self._get_or_default_policy(session, org_id=org_id, device_id=device_id, binding=binding)
        active_incident = await self._get_active_incident(session, org_id=org_id, device_id=device_id)

        if not self._has_valid_purpose(reason, settings.locate_reason_min_length):
            return self._deny(
                PolicyActionType.LOCATE,
                'invalid_purpose',
                f'Locate requests need a specific reason of at least {settings.locate_reason_min_length} characters.',
                owner_subject=owner_subject,
                incident_state=active_incident.state if active_incident else None,
            )

        if Role.OWNER in principal.roles:
            if owner_subject != principal.subject:
                return self._deny(
                    PolicyActionType.LOCATE,
                    'owner_binding_mismatch',
                    'Owners can only locate devices currently bound to them.',
                    owner_subject=owner_subject,
                    incident_state=active_incident.state if active_incident else None,
                )
            if not policy.owner_can_locate:
                return self._deny(
                    PolicyActionType.LOCATE,
                    'owner_locate_disabled',
                    'This tenant policy does not allow owner self-location for this device.',
                    owner_subject=owner_subject,
                    incident_state=active_incident.state if active_incident else None,
                )
        elif self._has_any_role(principal.roles, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN):
            if not policy.admin_can_locate:
                return self._deny(
                    PolicyActionType.LOCATE,
                    'admin_locate_disabled',
                    'Admin locate access is disabled by device policy.',
                    owner_subject=owner_subject,
                    incident_state=active_incident.state if active_incident else None,
                )
        else:
            return self._deny(
                PolicyActionType.LOCATE,
                'role_not_allowed',
                'Only authorized owners or admins can locate a device.',
                owner_subject=owner_subject,
                incident_state=active_incident.state if active_incident else None,
            )

        if settings.require_incident_for_locate or policy.require_incident_for_locate:
            if active_incident is None:
                return self._deny(
                    PolicyActionType.LOCATE,
                    'incident_required',
                    'This tenant requires an active recovery incident before a locate lookup can run.',
                    owner_subject=owner_subject,
                )

        return PolicyDecision(
            action_type=PolicyActionType.LOCATE,
            allowed=True,
            requires_approval=False,
            reason_code='locate_allowed',
            reason='Locate permitted by role, ownership, purpose, and tenant policy.',
            owner_subject=owner_subject,
            incident_state=active_incident.state if active_incident else None,
            context={'device_alias': device.alias},
        )

    async def evaluate_remote_action(
        self,
        session: AsyncSession,
        *,
        payload: RemoteActionCreateRequest,
        principal: Principal,
    ) -> PolicyDecision:
        settings = await self._get_or_default_settings(session, payload.org_id)
        device = await self._get_device(session, org_id=payload.org_id, device_id=payload.device_id)
        binding = await self._get_active_binding(session, org_id=payload.org_id, device_id=payload.device_id)
        owner_subject = await self._get_owner_subject(session, binding)
        policy = await self._get_or_default_policy(session, org_id=payload.org_id, device_id=payload.device_id, binding=binding)
        incident = await self._incident_from_payload_or_active(
            session,
            org_id=payload.org_id,
            device_id=payload.device_id,
            incident_id=payload.incident_id,
        )

        if not self._has_valid_purpose(payload.reason, settings.locate_reason_min_length):
            return self._deny(
                self._policy_action_for_remote_action(payload.action_kind),
                'invalid_purpose',
                f'Sensitive actions need a clear reason of at least {settings.locate_reason_min_length} characters.',
                owner_subject=owner_subject,
                incident_state=incident.state if incident else None,
            )

        if not device.is_policy_managed and payload.action_kind in {RemoteActionKind.LOCK, RemoteActionKind.WIPE}:
            return self._deny(
                self._policy_action_for_remote_action(payload.action_kind),
                'device_not_policy_managed',
                'Lock and wipe are allowed only on policy-managed devices.',
                owner_subject=owner_subject,
                incident_state=incident.state if incident else None,
            )

        if payload.action_kind in {RemoteActionKind.ENTER_LOST_MODE, RemoteActionKind.DISPLAY_RECOVERY_MESSAGE}:
            if not self._has_any_role(principal.roles, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN, Role.SECURITY):
                return self._deny(
                    self._policy_action_for_remote_action(payload.action_kind),
                    'role_not_allowed',
                    'Only authorized admins or security staff can issue recovery commands.',
                    owner_subject=owner_subject,
                    incident_state=incident.state if incident else None,
                )
            return PolicyDecision(
                action_type=self._policy_action_for_remote_action(payload.action_kind),
                allowed=True,
                requires_approval=False,
                reason_code='remote_action_allowed',
                reason='Recovery command is allowed for the current operator role.',
                owner_subject=owner_subject,
                incident_state=incident.state if incident else None,
            )

        if payload.action_kind == RemoteActionKind.LOCK:
            if not self._has_any_role(principal.roles, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN, Role.SECURITY):
                return self._deny(
                    PolicyActionType.LOCK,
                    'role_not_allowed',
                    'Only authorized admins or security staff can lock a device.',
                    owner_subject=owner_subject,
                    incident_state=incident.state if incident else None,
                )
            if not policy.admin_can_lock and not self._has_any_role(principal.roles, Role.SUPER_ADMIN):
                return self._deny(
                    PolicyActionType.LOCK,
                    'lock_disabled',
                    'Lock actions are disabled by device policy.',
                    owner_subject=owner_subject,
                    incident_state=incident.state if incident else None,
                )
            if settings.lock_requires_active_incident and incident is None:
                return self._deny(
                    PolicyActionType.LOCK,
                    'incident_required',
                    'This tenant requires an active incident before a lock command can be issued.',
                    owner_subject=owner_subject,
                )
            return PolicyDecision(
                action_type=PolicyActionType.LOCK,
                allowed=True,
                requires_approval=False,
                reason_code='lock_allowed',
                reason='Lock permitted by role, tenant policy, and device policy.',
                owner_subject=owner_subject,
                incident_state=incident.state if incident else None,
            )

        if payload.action_kind == RemoteActionKind.WIPE:
            if not self._has_any_role(principal.roles, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN):
                return self._deny(
                    PolicyActionType.WIPE,
                    'role_not_allowed',
                    'Only admin-level roles can request a wipe.',
                    owner_subject=owner_subject,
                    incident_state=incident.state if incident else None,
                )
            if not policy.admin_can_wipe and not self._has_any_role(principal.roles, Role.SUPER_ADMIN):
                return self._deny(
                    PolicyActionType.WIPE,
                    'wipe_disabled',
                    'Wipe is disabled by device policy.',
                    owner_subject=owner_subject,
                    incident_state=incident.state if incident else None,
                )
            if not payload.elevated_confirmation:
                return self._deny(
                    PolicyActionType.WIPE,
                    'elevated_confirmation_required',
                    'Wipe requires elevated confirmation from the requester.',
                    owner_subject=owner_subject,
                    incident_state=incident.state if incident else None,
                )
            if not payload.acknowledge_wipe_tradeoff:
                return self._deny(
                    PolicyActionType.WIPE,
                    'wipe_tradeoff_ack_required',
                    'Wipe requires acknowledgement that data protection can reduce recovery chances.',
                    owner_subject=owner_subject,
                    incident_state=incident.state if incident else None,
                )
            if settings.wipe_requires_confirmed_stolen:
                if incident is None or incident.state != IncidentCaseState.CONFIRMED_STOLEN:
                    return self._deny(
                        PolicyActionType.WIPE,
                        'confirmed_stolen_required',
                        'This tenant requires a confirmed stolen incident before wipe approval.',
                        owner_subject=owner_subject,
                        incident_state=incident.state if incident else None,
                    )
            required_approvals = 0
            if settings.wipe_requires_policy_approval:
                required_approvals = 2 if (settings.high_risk_actions_require_two_person or policy.require_two_person_wipe_approval) else 1
            return PolicyDecision(
                action_type=PolicyActionType.WIPE,
                allowed=True,
                requires_approval=required_approvals > 0,
                reason_code='wipe_requires_approval' if required_approvals > 0 else 'wipe_allowed',
                reason='Wipe is valid but must satisfy tenant approval policy before dispatch.' if required_approvals > 0 else 'Wipe allowed.',
                required_approvals=required_approvals,
                owner_subject=owner_subject,
                incident_state=incident.state if incident else None,
            )

        return self._deny(
            PolicyActionType.LOCK,
            'unsupported_action',
            'This remote action is not recognized by the policy engine.',
            owner_subject=owner_subject,
            incident_state=incident.state if incident else None,
        )

    async def evaluate_evidence_export(
        self,
        session: AsyncSession,
        *,
        incident: Incident,
        principal: Principal,
        payload: IncidentEvidenceExportRequest,
    ) -> PolicyDecision:
        if not hasattr(session, 'execute'):
            if not self._has_valid_purpose(payload.reason, 8):
                return self._deny(
                    PolicyActionType.EVIDENCE_EXPORT,
                    'invalid_purpose',
                    'Evidence exports need a specific documented purpose.',
                    incident_state=incident.state,
                )
            if self._has_any_role(principal.roles, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN, Role.SECURITY, Role.AUDITOR):
                return PolicyDecision(
                    action_type=PolicyActionType.EVIDENCE_EXPORT,
                    allowed=True,
                    requires_approval=False,
                    reason_code='evidence_export_allowed',
                    reason='Evidence export permitted by role and reason.',
                    incident_state=incident.state,
                )
            return self._deny(
                PolicyActionType.EVIDENCE_EXPORT,
                'export_not_permitted',
                'Evidence export is not permitted for this role.',
                incident_state=incident.state,
            )
        settings = await self._get_or_default_settings(session, incident.org_id)
        binding = await self._get_active_binding(session, org_id=incident.org_id, device_id=incident.device_id)
        owner_subject = await self._get_owner_subject(session, binding)
        policy = await self._get_or_default_policy(session, org_id=incident.org_id, device_id=incident.device_id, binding=binding)

        if not self._has_valid_purpose(payload.reason, settings.locate_reason_min_length):
            return self._deny(
                PolicyActionType.EVIDENCE_EXPORT,
                'invalid_purpose',
                f'Evidence exports need a specific documented purpose of at least {settings.locate_reason_min_length} characters.',
                owner_subject=owner_subject,
                incident_state=incident.state,
            )

        allowed = False
        if Role.OWNER in principal.roles and owner_subject == principal.subject and policy.owner_can_export_evidence:
            allowed = True
        elif self._has_any_role(principal.roles, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN) and policy.admin_can_export_evidence:
            allowed = True
        elif self._has_any_role(principal.roles, Role.SECURITY, Role.AUDITOR) and policy.security_can_export_evidence:
            allowed = True

        if not allowed:
            return self._deny(
                PolicyActionType.EVIDENCE_EXPORT,
                'export_not_permitted',
                'Evidence export is not permitted for this role under the current tenant and device policy.',
                owner_subject=owner_subject,
                incident_state=incident.state,
            )

        if settings.evidence_export_requires_permission and incident.state in {IncidentCaseState.NORMAL, IncidentCaseState.DECOMMISSIONED}:
            return self._deny(
                PolicyActionType.EVIDENCE_EXPORT,
                'incident_state_not_exportable',
                'Evidence export is restricted to active or historically relevant incidents.',
                owner_subject=owner_subject,
                incident_state=incident.state,
            )

        return PolicyDecision(
            action_type=PolicyActionType.EVIDENCE_EXPORT,
            allowed=True,
            requires_approval=False,
            reason_code='evidence_export_allowed',
            reason='Evidence export permitted by role, incident state, and tenant policy.',
            owner_subject=owner_subject,
            incident_state=incident.state,
        )

    async def evaluate_retention_update(
        self,
        session: AsyncSession,
        *,
        principal: Principal,
        payload: RetentionPolicyUpdateRequest,
    ) -> PolicyDecision:
        if not self._has_any_role(principal.roles, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN):
            return self._deny(
                PolicyActionType.RETENTION_UPDATE,
                'role_not_allowed',
                'Only admin-level roles can update tenant retention and access rules.',
            )
        if not self._has_valid_purpose(payload.reason, 8):
            return self._deny(
                PolicyActionType.RETENTION_UPDATE,
                'invalid_purpose',
                'Retention changes require a clear administrative reason.',
            )
        return PolicyDecision(
            action_type=PolicyActionType.RETENTION_UPDATE,
            allowed=True,
            requires_approval=False,
            reason_code='retention_update_allowed',
            reason='Retention and access policy update allowed for authorized admin role.',
        )

    async def _get_or_default_settings(self, session: AsyncSession, org_id: UUID) -> TenantSettings:
        if not hasattr(session, 'execute'):
            return TenantSettings(
                org_id=org_id,
                location_event_days=30,
                audit_log_days=90,
                incident_evidence_days=60,
                locate_reason_min_length=8,
                require_incident_for_locate=False,
                lock_requires_active_incident=True,
                wipe_requires_policy_approval=True,
                wipe_requires_confirmed_stolen=True,
                high_risk_actions_require_two_person=True,
                evidence_export_requires_permission=True,
            )
        settings = (await session.execute(select(TenantSettings).where(TenantSettings.org_id == org_id))).scalar_one_or_none()
        if settings is not None:
            return settings
        return TenantSettings(
            org_id=org_id,
            location_event_days=30,
            audit_log_days=90,
            incident_evidence_days=60,
            locate_reason_min_length=8,
            require_incident_for_locate=False,
            lock_requires_active_incident=True,
            wipe_requires_policy_approval=True,
            wipe_requires_confirmed_stolen=True,
            high_risk_actions_require_two_person=True,
            evidence_export_requires_permission=True,
        )

    async def _get_device(self, session: AsyncSession, *, org_id: UUID, device_id: UUID) -> Device:
        device = (await session.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
        if device is None or device.organization_id != org_id:
            raise ValueError('Device does not belong to tenant org.')
        return device

    async def _get_active_binding(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
    ) -> DeviceOwnershipBinding | None:
        binding = (
            await session.execute(
                select(DeviceOwnershipBinding)
                .where(
                    DeviceOwnershipBinding.org_id == org_id,
                    DeviceOwnershipBinding.device_id == device_id,
                    DeviceOwnershipBinding.is_active.is_(True),
                )
                .order_by(desc(DeviceOwnershipBinding.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        return binding

    async def _get_owner_subject(self, session: AsyncSession, binding: DeviceOwnershipBinding | None) -> str | None:
        if binding is None or binding.owner_user_id is None:
            return None
        user = (await session.execute(select(User).where(User.id == binding.owner_user_id))).scalar_one_or_none()
        return user.subject if user else None

    async def _get_or_default_policy(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        binding: DeviceOwnershipBinding | None,
    ) -> DeviceAccessPolicy:
        policy = (await session.execute(select(DeviceAccessPolicy).where(DeviceAccessPolicy.device_id == device_id))).scalar_one_or_none()
        if policy is not None:
            return policy
        ownership_type = binding.ownership_type if binding else OwnershipType.ORGANIZATION_OWNED
        return DeviceAccessPolicy(
            org_id=org_id,
            device_id=device_id,
            owner_can_locate=ownership_type == OwnershipType.SINGLE_USER,
            admin_can_locate=True,
            security_operator_can_review=True,
            require_access_review=False,
            owner_can_export_evidence=ownership_type == OwnershipType.SINGLE_USER,
            admin_can_export_evidence=True,
            security_can_export_evidence=True,
            admin_can_lock=True,
            admin_can_wipe=True,
            require_incident_for_locate=False,
            require_two_person_wipe_approval=True,
        )

    async def _get_active_incident(self, session: AsyncSession, *, org_id: UUID, device_id: UUID) -> Incident | None:
        return (
            await session.execute(
                select(Incident)
                .where(
                    Incident.org_id == org_id,
                    Incident.device_id == device_id,
                    Incident.state.in_(
                        [
                            IncidentCaseState.SUSPECTED_LOST,
                            IncidentCaseState.CONFIRMED_STOLEN,
                        ]
                    ),
                )
                .order_by(desc(Incident.updated_at))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _incident_from_payload_or_active(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        incident_id: UUID | None,
    ) -> Incident | None:
        if incident_id is not None:
            incident = (await session.execute(select(Incident).where(Incident.id == incident_id))).scalar_one_or_none()
            if incident is None or incident.org_id != org_id or incident.device_id != device_id:
                raise ValueError('Incident does not belong to tenant/device context.')
            return incident
        return await self._get_active_incident(session, org_id=org_id, device_id=device_id)

    def _has_valid_purpose(self, reason: str, min_length: int) -> bool:
        cleaned = reason.strip()
        if len(cleaned) < min_length:
            return False
        lowered = cleaned.lower()
        invalid_values = {'test', 'check', 'n/a', 'na', 'none', 'locate', 'urgent'}
        return lowered not in invalid_values

    def _has_any_role(self, roles: Iterable[Role], *required: Role) -> bool:
        role_set = set(roles)
        return any(role in role_set for role in required)

    def _policy_action_for_remote_action(self, action_kind: RemoteActionKind) -> PolicyActionType:
        if action_kind == RemoteActionKind.WIPE:
            return PolicyActionType.WIPE
        if action_kind == RemoteActionKind.LOCK:
            return PolicyActionType.LOCK
        if action_kind == RemoteActionKind.ENTER_LOST_MODE:
            return PolicyActionType.ENTER_LOST_MODE
        return PolicyActionType.DISPLAY_RECOVERY_MESSAGE

    def _deny(
        self,
        action_type: PolicyActionType,
        reason_code: str,
        reason: str,
        *,
        owner_subject: str | None = None,
        incident_state: IncidentCaseState | None = None,
    ) -> PolicyDecision:
        return PolicyDecision(
            action_type=action_type,
            allowed=False,
            requires_approval=False,
            reason_code=reason_code,
            reason=reason,
            owner_subject=owner_subject,
            incident_state=incident_state,
        )
