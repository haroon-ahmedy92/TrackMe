from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import RuleExecutionLock
from app.services.audit_log_service import AuditLogService
from app.services.command_queue_service import CommandQueueService
from app.services.notification_event_service import NotificationEventService
from app.services.rules_engine_service import RuleActionRequest, RuleMatch


class RuleActionExecutor:
    def __init__(
        self,
        *,
        notification_event_service: NotificationEventService,
        audit_log_service: AuditLogService,
        command_queue_service: CommandQueueService,
    ) -> None:
        self.notification_event_service = notification_event_service
        self.audit_log_service = audit_log_service
        self.command_queue_service = command_queue_service

    async def execute_matches(
        self,
        session: AsyncSession,
        *,
        org_id: UUID | None,
        source_event_id: UUID,
        matches: list[RuleMatch],
    ) -> list[str]:
        executed: list[str] = []
        for match in matches:
            for action in match.actions:
                allowed = await self._allow_action(
                    session,
                    org_id=org_id,
                    source_event_id=source_event_id,
                    rule_code=match.rule_code,
                    action=action,
                )
                if not allowed:
                    continue
                await self._execute_action(session, org_id=org_id, action=action)
            executed.append(match.rule_code)
        return executed

    async def _allow_action(
        self,
        session: AsyncSession,
        *,
        org_id: UUID | None,
        source_event_id: UUID,
        rule_code: str,
        action: RuleActionRequest,
    ) -> bool:
        if not action.cooldown_scope:
            return True
        now = datetime.now(timezone.utc)
        cooldown_seconds = action.cooldown_seconds or settings.rules_alert_cooldown_seconds
        row = (
            await session.execute(
                select(RuleExecutionLock).where(
                    RuleExecutionLock.org_id == org_id,
                    RuleExecutionLock.rule_code == rule_code,
                    RuleExecutionLock.scope_key == action.cooldown_scope,
                )
            )
        ).scalar_one_or_none()
        if row is not None and row.cooldown_until > now:
            return False
        if row is None:
            row = RuleExecutionLock(
                org_id=org_id,
                rule_code=rule_code,
                scope_key=action.cooldown_scope,
                last_event_id=source_event_id,
                last_triggered_at=now,
                cooldown_until=now + timedelta(seconds=cooldown_seconds),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
        else:
            row.last_event_id = source_event_id
            row.last_triggered_at = now
            row.cooldown_until = now + timedelta(seconds=cooldown_seconds)
            row.updated_at = now
        await session.flush()
        return True

    async def _execute_action(
        self,
        session: AsyncSession,
        *,
        org_id: UUID | None,
        action: RuleActionRequest,
    ) -> None:
        if action.action_type == 'notify_internal':
            payload = action.payload
            if org_id is None:
                return
            await self.notification_event_service.create_internal_alert(
                session,
                org_id=org_id,
                template=str(payload.get('template', 'rule_alert')),
                payload=payload,
                device_id=_uuid_or_none(payload.get('device_id')),
                incident_id=_uuid_or_none(payload.get('incident_id')),
                remote_action_id=_uuid_or_none(payload.get('remote_action_id')),
                recipient_sub=payload.get('recipient_sub'),
            )
            return

        if action.action_type == 'audit':
            payload = action.payload
            await self.audit_log_service.append(
                session,
                org_id=str(org_id) if org_id else None,
                actor_sub='rules-engine',
                action=str(payload['action']),
                entity_type=str(payload['entity_type']),
                entity_id=str(payload['entity_id']),
                metadata=dict(payload.get('metadata', {})),
            )
            return

        if action.action_type == 'retry_command':
            payload = action.payload
            org_uuid = _uuid_or_none(payload.get('org_id')) or org_id
            if org_uuid is None:
                return
            await self.command_queue_service.retry_pending_commands(
                session,
                org_id=org_uuid,
                device_id=_uuid_or_none(payload.get('device_id')),
            )
            return

        if action.action_type == 'expire_command':
            payload = action.payload
            remote_action_id = _uuid_or_none(payload.get('remote_action_id'))
            if remote_action_id is None:
                return
            await self.command_queue_service.expire_action(
                session,
                remote_action_id=remote_action_id,
                reason=str(payload.get('reason', 'Expired by rules engine')),
            )


def _uuid_or_none(value) -> UUID | None:
    if value in (None, ''):
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
