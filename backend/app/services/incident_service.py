from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Device,
    IncidentRecord,
    IncidentState,
    IncidentTimelineEvent,
    RemoteActionRequest,
    RemoteActionStatus,
    RemoteActionType,
)
from app.schemas.common import IncidentState as IncidentStateSchema
from app.schemas.incident import (
    ConfirmStolenRequest,
    IncidentResolutionRequest,
    MarkDeviceLostRequest,
    RemoteLockDecisionRequest,
    RemoteWipeDecisionRequest,
)
from app.services.audit_service import AuditService
from app.services.incident_audit_events import (
    INCIDENT_CANCELLED,
    INCIDENT_CONFIRMED_STOLEN,
    INCIDENT_DECOMMISSIONED,
    INCIDENT_MARKED_LOST,
    INCIDENT_RECOVERED,
    INCIDENT_REMOTE_LOCK_DECISION,
    INCIDENT_REMOTE_WIPE_DELAYED,
    INCIDENT_REMOTE_WIPE_EXECUTED,
)
from app.services.incident_state_machine import IncidentStateMachine
from app.services.notification_service import NotificationMessage, NotificationService


class IncidentService:
    def __init__(
        self,
        state_machine: IncidentStateMachine,
        notification_service: NotificationService,
    ) -> None:
        self.state_machine = state_machine
        self.notification_service = notification_service

    async def mark_lost(
        self,
        session: AsyncSession,
        payload: MarkDeviceLostRequest,
        actor_sub: str,
        organization_id: str | None,
        audit_service: AuditService,
    ) -> IncidentRecord:
        device = await self._get_device(session, payload.device_id)
        self._assert_actor_org_access(organization_id, device.organization_id)
        now = datetime.now(timezone.utc)
        next_state = self.state_machine.transition(
            current=IncidentStateSchema.NORMAL,
            trigger='mark_suspected_lost',
        )
        incident = IncidentRecord(
            device_id=device.id,
            ticket_reference=payload.ticket_reference,
            state=IncidentState(next_state.value),
            recovery_message=payload.recovery_message,
            created_at=now,
            updated_at=now,
        )
        session.add(incident)
        await session.flush()

        await self._append_timeline(
            session=session,
            incident=incident,
            action='MARK_SUSPECTED_LOST',
            summary='Device marked as suspected lost',
            metadata={
                'ticket_reference': payload.ticket_reference,
                'lost_mode_window_hours': payload.lost_mode_window_hours,
            },
        )
        await audit_service.append_event(
            session=session,
            actor_sub=actor_sub,
            organization_id=organization_id,
            action=INCIDENT_MARKED_LOST,
            entity_type='incident',
            entity_id=str(incident.id),
            metadata={
                'device_id': str(device.id),
                'ticket_reference': payload.ticket_reference,
            },
        )
        await self._notify_escalation(
            title='Recovery Incident Started',
            body=payload.recovery_message,
        )
        await session.commit()
        return incident

    async def confirm_stolen(
        self,
        session: AsyncSession,
        incident_id: UUID,
        payload: ConfirmStolenRequest,
        actor_sub: str,
        organization_id: str | None,
        audit_service: AuditService,
    ) -> IncidentRecord:
        incident = await self._get_incident(session, incident_id)
        device = await self._get_device(session, incident.device_id)
        self._assert_actor_org_access(organization_id, device.organization_id)
        next_state = self.state_machine.transition(
            current=IncidentStateSchema(incident.state.value),
            trigger='confirm_stolen',
            elevated_confirmed=payload.elevated_confirmation,
        )
        incident.state = IncidentState(next_state.value)
        incident.updated_at = datetime.now(timezone.utc)
        incident.elevated_confirmed_by = actor_sub

        await self._append_timeline(
            session=session,
            incident=incident,
            action='CONFIRM_STOLEN',
            summary='Incident confirmed stolen after elevated confirmation',
            metadata={'reason': payload.reason},
        )
        await audit_service.append_event(
            session=session,
            actor_sub=actor_sub,
            organization_id=organization_id,
            action=INCIDENT_CONFIRMED_STOLEN,
            entity_type='incident',
            entity_id=str(incident.id),
            metadata={'reason': payload.reason},
        )
        await self._notify_escalation(
            title='Confirmed Stolen Device',
            body=f'Incident {incident.id} requires urgent response.',
        )
        await session.commit()
        return incident

    async def request_remote_lock(
        self,
        session: AsyncSession,
        incident_id: UUID,
        payload: RemoteLockDecisionRequest,
        actor_sub: str,
        organization_id: str | None,
        audit_service: AuditService,
    ) -> RemoteActionRequest:
        incident = await self._get_incident(session, incident_id)
        device = await self._get_device(session, incident.device_id)
        self._assert_actor_org_access(organization_id, device.organization_id)
        if not device.is_policy_managed:
            raise PermissionError('Remote lock is allowed only for policy-managed devices.')
        if not self.state_machine.can_request_lock(IncidentStateSchema(incident.state.value)):
            raise ValueError('Remote lock decision is invalid for current incident state.')

        action = RemoteActionRequest(
            device_id=device.id,
            incident_id=incident.id,
            action_type=RemoteActionType.LOCK,
            status=RemoteActionStatus.PENDING,
            ticket_reference=incident.ticket_reference,
            requested_by=actor_sub,
            reason=payload.reason,
            requested_at=datetime.now(timezone.utc),
        )
        session.add(action)
        await session.flush()

        await self._append_timeline(
            session=session,
            incident=incident,
            action='REMOTE_LOCK_REQUESTED',
            summary='Remote lock decision executed',
            metadata={'reason': payload.reason, 'action_id': str(action.id)},
        )
        await audit_service.append_event(
            session=session,
            actor_sub=actor_sub,
            organization_id=organization_id,
            action=INCIDENT_REMOTE_LOCK_DECISION,
            entity_type='incident',
            entity_id=str(incident.id),
            metadata={'action_id': str(action.id), 'reason': payload.reason},
        )
        await session.commit()
        return action

    async def request_remote_wipe(
        self,
        session: AsyncSession,
        incident_id: UUID,
        payload: RemoteWipeDecisionRequest,
        actor_sub: str,
        organization_id: str | None,
        audit_service: AuditService,
    ) -> tuple[IncidentRecord, RemoteActionRequest | None]:
        incident = await self._get_incident(session, incident_id)
        device = await self._get_device(session, incident.device_id)
        self._assert_actor_org_access(organization_id, device.organization_id)
        if not device.is_policy_managed:
            raise PermissionError('Remote wipe is allowed only for policy-managed devices.')
        if not self.state_machine.can_request_wipe(IncidentStateSchema(incident.state.value)):
            raise ValueError('Remote wipe decision is invalid for current incident state.')
        if not payload.elevated_confirmation:
            raise ValueError('Elevated confirmation is required for remote wipe.')
        if not payload.confirm_wipe_intent:
            raise ValueError('Explicit wipe intent confirmation is required.')
        if not payload.acknowledge_tradeoff:
            raise ValueError('Wipe tradeoff acknowledgement is required.')

        now = datetime.now(timezone.utc)
        action_request: RemoteActionRequest | None = None

        if payload.delay_minutes > 0:
            execute_at = now + timedelta(minutes=payload.delay_minutes)
            incident.wipe_scheduled_at = execute_at
            incident.wipe_reason = payload.reason
            incident.updated_at = now
            await self._append_timeline(
                session=session,
                incident=incident,
                action='REMOTE_WIPE_DELAYED',
                summary='Remote wipe scheduled with delay',
                metadata={
                    'delay_minutes': payload.delay_minutes,
                    'execute_at': execute_at.isoformat(),
                    'reason': payload.reason,
                    'tradeoff': 'Wiping may protect data but reduce recovery chances.',
                },
            )
            await audit_service.append_event(
                session=session,
                actor_sub=actor_sub,
                organization_id=organization_id,
                action=INCIDENT_REMOTE_WIPE_DELAYED,
                entity_type='incident',
                entity_id=str(incident.id),
                metadata={
                    'delay_minutes': payload.delay_minutes,
                    'execute_at': execute_at.isoformat(),
                    'reason': payload.reason,
                },
            )
            await session.commit()
            return incident, None

        next_state = self.state_machine.transition(
            current=IncidentStateSchema(incident.state.value),
            trigger='mark_wiped',
            elevated_confirmed=True,
        )
        incident.state = IncidentState(next_state.value)
        incident.wipe_scheduled_at = None
        incident.wipe_reason = payload.reason
        incident.updated_at = now
        action_request = RemoteActionRequest(
            device_id=device.id,
            incident_id=incident.id,
            action_type=RemoteActionType.WIPE,
            status=RemoteActionStatus.PENDING,
            ticket_reference=incident.ticket_reference,
            requested_by=actor_sub,
            reason=payload.reason,
            requested_at=now,
        )
        session.add(action_request)
        await session.flush()

        await self._append_timeline(
            session=session,
            incident=incident,
            action='REMOTE_WIPE_EXECUTED',
            summary='Immediate remote wipe requested',
            metadata={
                'reason': payload.reason,
                'action_id': str(action_request.id),
                'tradeoff': 'Wiping may protect data but reduce recovery chances.',
            },
        )
        await audit_service.append_event(
            session=session,
            actor_sub=actor_sub,
            organization_id=organization_id,
            action=INCIDENT_REMOTE_WIPE_EXECUTED,
            entity_type='incident',
            entity_id=str(incident.id),
            metadata={'reason': payload.reason, 'action_id': str(action_request.id)},
        )
        await session.commit()
        return incident, action_request

    async def recover(
        self,
        session: AsyncSession,
        incident_id: UUID,
        payload: IncidentResolutionRequest,
        actor_sub: str,
        organization_id: str | None,
        audit_service: AuditService,
    ) -> IncidentRecord:
        incident = await self._get_incident(session, incident_id)
        device = await self._get_device(session, incident.device_id)
        self._assert_actor_org_access(organization_id, device.organization_id)
        next_state = self.state_machine.transition(
            current=IncidentStateSchema(incident.state.value),
            trigger='recover',
        )
        incident.state = IncidentState(next_state.value)
        incident.wipe_scheduled_at = None
        incident.updated_at = datetime.now(timezone.utc)
        await self._append_timeline(
            session=session,
            incident=incident,
            action='RECOVERED',
            summary='Device marked recovered',
            metadata={'reason': payload.reason},
        )
        await audit_service.append_event(
            session=session,
            actor_sub=actor_sub,
            organization_id=organization_id,
            action=INCIDENT_RECOVERED,
            entity_type='incident',
            entity_id=str(incident.id),
            metadata={'reason': payload.reason},
        )
        await session.commit()
        return incident

    async def cancel(
        self,
        session: AsyncSession,
        incident_id: UUID,
        payload: IncidentResolutionRequest,
        actor_sub: str,
        organization_id: str | None,
        audit_service: AuditService,
    ) -> IncidentRecord:
        incident = await self._get_incident(session, incident_id)
        device = await self._get_device(session, incident.device_id)
        self._assert_actor_org_access(organization_id, device.organization_id)
        next_state = self.state_machine.transition(
            current=IncidentStateSchema(incident.state.value),
            trigger='cancel',
        )
        incident.state = IncidentState(next_state.value)
        incident.wipe_scheduled_at = None
        incident.updated_at = datetime.now(timezone.utc)
        await self._append_timeline(
            session=session,
            incident=incident,
            action='CANCELLED',
            summary='Incident cancelled',
            metadata={'reason': payload.reason},
        )
        await audit_service.append_event(
            session=session,
            actor_sub=actor_sub,
            organization_id=organization_id,
            action=INCIDENT_CANCELLED,
            entity_type='incident',
            entity_id=str(incident.id),
            metadata={'reason': payload.reason},
        )
        await session.commit()
        return incident

    async def decommission(
        self,
        session: AsyncSession,
        incident_id: UUID,
        payload: IncidentResolutionRequest,
        actor_sub: str,
        organization_id: str | None,
        audit_service: AuditService,
    ) -> IncidentRecord:
        incident = await self._get_incident(session, incident_id)
        device = await self._get_device(session, incident.device_id)
        self._assert_actor_org_access(organization_id, device.organization_id)
        next_state = self.state_machine.transition(
            current=IncidentStateSchema(incident.state.value),
            trigger='decommission',
        )
        incident.state = IncidentState(next_state.value)
        incident.wipe_scheduled_at = None
        incident.updated_at = datetime.now(timezone.utc)
        await self._append_timeline(
            session=session,
            incident=incident,
            action='DECOMMISSIONED',
            summary='Device decommissioned from active fleet',
            metadata={'reason': payload.reason},
        )
        await audit_service.append_event(
            session=session,
            actor_sub=actor_sub,
            organization_id=organization_id,
            action=INCIDENT_DECOMMISSIONED,
            entity_type='incident',
            entity_id=str(incident.id),
            metadata={'reason': payload.reason},
        )
        await session.commit()
        return incident

    async def timeline(
        self,
        session: AsyncSession,
        incident_id: UUID,
        limit: int = 200,
    ) -> list[IncidentTimelineEvent]:
        await self._get_incident(session, incident_id)
        stmt = (
            select(IncidentTimelineEvent)
            .where(IncidentTimelineEvent.incident_id == incident_id)
            .order_by(desc(IncidentTimelineEvent.occurred_at))
            .limit(limit)
        )
        return list((await session.execute(stmt)).scalars().all())

    async def _get_device(self, session: AsyncSession, device_id: UUID) -> Device:
        stmt = select(Device).where(Device.id == device_id)
        device = (await session.execute(stmt)).scalar_one_or_none()
        if device is None:
            raise ValueError('Unknown device_id')
        return device

    async def _get_incident(self, session: AsyncSession, incident_id: UUID) -> IncidentRecord:
        stmt = select(IncidentRecord).where(IncidentRecord.id == incident_id)
        incident = (await session.execute(stmt)).scalar_one_or_none()
        if incident is None:
            raise ValueError('Unknown incident_id')
        return incident

    async def _append_timeline(
        self,
        session: AsyncSession,
        incident: IncidentRecord,
        action: str,
        summary: str,
        metadata: dict,
    ) -> None:
        session.add(
            IncidentTimelineEvent(
                incident_id=incident.id,
                state=incident.state,
                action=action,
                summary=summary,
                metadata_json=metadata,
                occurred_at=datetime.now(timezone.utc),
            )
        )
        await session.flush()

    async def _notify_escalation(self, title: str, body: str) -> None:
        await self.notification_service.send(
            NotificationMessage(
                title=title,
                body=body,
                device_token='owner-admin-placeholder',
            )
        )

    def _assert_actor_org_access(self, actor_org_id: str | None, resource_org_id) -> None:
        """
        Enforces tenant-bound access for non-global principals.
        A null actor org is treated as global admin access.
        """
        if actor_org_id is None:
            return
        if resource_org_id is None or str(resource_org_id) != actor_org_id:
            raise PermissionError('Tenant access denied')
