from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, RemoteAction, RemoteActionKind, RemoteActionState
from app.schemas.platform import RemoteActionCreateRequest


class RemoteActionService:
    async def request_action(
        self,
        session: AsyncSession,
        payload: RemoteActionCreateRequest,
        *,
        requested_by_sub: str,
    ) -> RemoteAction:
        device = (await session.execute(select(Device).where(Device.id == payload.device_id))).scalar_one_or_none()
        if device is None:
            raise ValueError('Unknown device_id')
        if device.organization_id != payload.org_id:
            raise ValueError('Device does not belong to tenant org.')
        if not device.is_policy_managed:
            raise PermissionError('Remote actions are allowed only on policy-managed devices.')

        if payload.action_kind == RemoteActionKind.WIPE:
            if not payload.elevated_confirmation:
                raise ValueError('Remote wipe requires elevated confirmation.')
            if not payload.acknowledge_wipe_tradeoff:
                raise ValueError('Remote wipe requires tradeoff acknowledgement.')

        now = datetime.now(timezone.utc)
        action = RemoteAction(
            org_id=payload.org_id,
            device_id=payload.device_id,
            incident_id=payload.incident_id,
            action_kind=payload.action_kind,
            state=RemoteActionState.REQUESTED,
            reason=payload.reason,
            requires_elevated_confirmation=payload.elevated_confirmation,
            delayed_until=payload.delayed_until,
            requested_by_sub=requested_by_sub,
            requested_at=now,
            updated_at=now,
        )
        session.add(action)
        await session.flush()
        return action

    async def mark_dispatched(self, session: AsyncSession, action_id: UUID) -> RemoteAction:
        action = await self._get(session, action_id)
        action.state = RemoteActionState.DISPATCHED
        action.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return action

    async def mark_applied(self, session: AsyncSession, action_id: UUID) -> RemoteAction:
        action = await self._get(session, action_id)
        action.state = RemoteActionState.APPLIED
        action.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return action

    async def mark_failed(self, session: AsyncSession, action_id: UUID) -> RemoteAction:
        action = await self._get(session, action_id)
        action.state = RemoteActionState.FAILED
        action.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return action

    async def _get(self, session: AsyncSession, action_id: UUID) -> RemoteAction:
        action = (await session.execute(select(RemoteAction).where(RemoteAction.id == action_id))).scalar_one_or_none()
        if action is None:
            raise ValueError('Unknown remote_action_id')
        return action
