from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, Incident, IncidentCaseState, IncidentEvent
from app.schemas.common import IncidentState
from app.schemas.platform import IncidentCreateRequest, IncidentTransitionRequest
from app.services.incident_state_machine import IncidentStateMachine


class CaseManagementService:
    def __init__(self, state_machine: IncidentStateMachine) -> None:
        self.state_machine = state_machine

    async def open_case(self, session: AsyncSession, payload: IncidentCreateRequest) -> Incident:
        device = (await session.execute(select(Device).where(Device.id == payload.device_id))).scalar_one_or_none()
        if device is None:
            raise ValueError('Unknown device_id')
        if device.organization_id != payload.org_id:
            raise ValueError('Device does not belong to tenant org.')

        now = datetime.now(timezone.utc)
        incident = Incident(
            org_id=payload.org_id,
            device_id=payload.device_id,
            ticket_reference=payload.ticket_reference,
            state=IncidentCaseState.SUSPECTED_LOST,
            recovery_message=payload.recovery_message,
            elevated_confirmed_by=None,
            lost_mode_until=payload.lost_mode_until,
            wipe_scheduled_at=None,
            wipe_reason=None,
            created_at=now,
            updated_at=now,
        )
        session.add(incident)
        await session.flush()
        await self._append_event(
            session=session,
            incident=incident,
            action='CASE_OPENED',
            summary='Case opened as suspected lost',
            metadata={'ticket_reference': payload.ticket_reference},
        )
        return incident

    async def transition_case(
        self,
        session: AsyncSession,
        *,
        incident_id: UUID,
        trigger: str,
        reason: str,
        actor_sub: str,
        elevated_confirmation: bool,
        delayed_until: datetime | None = None,
    ) -> Incident:
        incident = await self.get_case(session, incident_id)
        next_state = self.state_machine.transition(
            current=IncidentState(incident.state.value),
            trigger=trigger,
            elevated_confirmed=elevated_confirmation,
        )
        incident.state = IncidentCaseState(next_state.value)
        incident.updated_at = datetime.now(timezone.utc)
        if trigger == 'confirm_stolen':
            incident.elevated_confirmed_by = actor_sub
        if trigger == 'mark_wiped':
            incident.wipe_reason = reason
        if delayed_until is not None:
            incident.wipe_scheduled_at = delayed_until

        await self._append_event(
            session=session,
            incident=incident,
            action=f'CASE_{trigger.upper()}',
            summary='Incident state transition executed',
            metadata={
                'trigger': trigger,
                'reason': reason,
                'actor_sub': actor_sub,
                'elevated_confirmation': elevated_confirmation,
                'delayed_until': delayed_until.isoformat() if delayed_until else None,
            },
        )
        await session.flush()
        return incident

    async def get_case(self, session: AsyncSession, incident_id: UUID) -> Incident:
        row = (await session.execute(select(Incident).where(Incident.id == incident_id))).scalar_one_or_none()
        if row is None:
            raise ValueError('Unknown incident_id')
        return row

    async def list_case_events(self, session: AsyncSession, incident_id: UUID, limit: int = 250) -> list[IncidentEvent]:
        await self.get_case(session, incident_id)
        stmt = (
            select(IncidentEvent)
            .where(IncidentEvent.incident_id == incident_id)
            .order_by(desc(IncidentEvent.occurred_at))
            .limit(limit)
        )
        return list((await session.execute(stmt)).scalars().all())

    async def apply_transition_request(
        self,
        session: AsyncSession,
        incident_id: UUID,
        action: str,
        payload: IncidentTransitionRequest,
        actor_sub: str,
    ) -> Incident:
        trigger_map = {
            'confirm_stolen': 'confirm_stolen',
            'recover': 'recover',
            'cancel': 'cancel',
            'decommission': 'decommission',
            'mark_wiped': 'mark_wiped',
        }
        trigger = trigger_map.get(action)
        if trigger is None:
            raise ValueError('Unknown case action')
        return await self.transition_case(
            session=session,
            incident_id=incident_id,
            trigger=trigger,
            reason=payload.reason,
            actor_sub=actor_sub,
            elevated_confirmation=payload.elevated_confirmation,
            delayed_until=payload.delayed_until,
        )

    async def _append_event(
        self,
        session: AsyncSession,
        *,
        incident: Incident,
        action: str,
        summary: str,
        metadata: dict,
    ) -> None:
        event = IncidentEvent(
            org_id=incident.org_id,
            incident_id=incident.id,
            state=incident.state,
            action=action,
            summary=summary,
            metadata_json=metadata,
            occurred_at=datetime.now(timezone.utc),
        )
        session.add(event)
        await session.flush()
