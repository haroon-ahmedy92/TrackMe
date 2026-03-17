from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Device, DeviceKey, DevicePushToken, Enrollment, EnrollmentStatus, NotificationStatus, RemoteAction, RemoteActionKind, RemoteActionState
from app.schemas.commands import CommandAckRequest, CommandEnvelopeResponse, CommandQueueRequest, DeviceCommandSyncRequest, DevicePushTokenRegisterRequest
from app.services.command_signing_service import CommandSigningService
from app.services.notification_event_service import NotificationEventService
from app.services.notification_template_service import NotificationTemplateService


@dataclass(frozen=True)
class RetryDispatchResult:
    processed: int
    sent: int
    failed: int
    expired: int


class CommandQueueService:
    def __init__(
        self,
        *,
        signing_service: CommandSigningService,
        notification_event_service: NotificationEventService,
        notification_template_service: NotificationTemplateService,
    ) -> None:
        self.signing_service = signing_service
        self.notification_event_service = notification_event_service
        self.notification_template_service = notification_template_service

    async def queue_command(
        self,
        session: AsyncSession,
        payload: CommandQueueRequest,
        *,
        actor_sub: str,
    ) -> RemoteAction:
        device = await self._get_device(session, payload.device_id)
        if device.organization_id != payload.org_id:
            raise ValueError('Device does not belong to tenant org.')
        if payload.action_kind in {RemoteActionKind.LOCK, RemoteActionKind.WIPE} and not device.is_policy_managed:
            raise PermissionError('Lock and wipe are allowed only for policy-managed devices.')
        if payload.action_kind == RemoteActionKind.ENTER_LOST_MODE and payload.lost_mode_until is None:
            raise ValueError('lost_mode_until is required for enter_lost_mode commands.')
        if payload.action_kind == RemoteActionKind.DISPLAY_RECOVERY_MESSAGE and not payload.recovery_message:
            raise ValueError('recovery_message is required for display_recovery_message commands.')
        if payload.action_kind == RemoteActionKind.WIPE:
            if not payload.elevated_confirmation:
                raise ValueError('Remote wipe requires elevated confirmation.')
            if not payload.acknowledge_wipe_tradeoff:
                raise ValueError('Remote wipe requires tradeoff acknowledgement.')

        now = datetime.now(timezone.utc)
        expires_at = payload.expires_at or now + timedelta(minutes=settings.command_default_ttl_minutes)
        action = RemoteAction(
            org_id=payload.org_id,
            device_id=payload.device_id,
            incident_id=payload.incident_id,
            action_kind=payload.action_kind,
            state=RemoteActionState.PENDING,
            reason=payload.reason,
            command_payload_json={},
            command_signature='',
            signature_algorithm=self.signing_service.algorithm,
            requires_elevated_confirmation=payload.elevated_confirmation,
            delayed_until=payload.delayed_until,
            expires_at=expires_at,
            requested_by_sub=actor_sub,
            requested_at=now,
            sent_at=None,
            delivered_at=None,
            acked_at=None,
            failed_at=None,
            attempt_count=0,
            last_error=None,
            acknowledgement_metadata_json={},
            updated_at=now,
        )
        session.add(action)
        await session.flush()
        payload_json = self._build_payload(payload, actor_sub=actor_sub, requested_at=now, remote_action_id=action.id, expires_at=expires_at)
        action.command_payload_json = payload_json
        action.command_signature = self.signing_service.sign(payload_json)
        await session.flush()
        return action

    async def register_push_token(
        self,
        session: AsyncSession,
        payload: DevicePushTokenRegisterRequest,
    ) -> DevicePushToken:
        await self._verify_device_identity(session, payload.org_id, payload.device_id, payload.key_id)
        now = datetime.now(timezone.utc)
        existing = (
            await session.execute(select(DevicePushToken).where(DevicePushToken.push_token == payload.push_token))
        ).scalar_one_or_none()
        if existing is not None:
            existing.org_id = payload.org_id
            existing.device_id = payload.device_id
            existing.key_id = payload.key_id
            existing.app_version = payload.app_version
            existing.is_active = True
            existing.invalidated_at = None
            existing.last_seen_at = now
            await session.flush()
            return existing

        token = DevicePushToken(
            org_id=payload.org_id,
            device_id=payload.device_id,
            key_id=payload.key_id,
            push_token=payload.push_token,
            platform='android',
            app_version=payload.app_version,
            is_active=True,
            last_seen_at=now,
            created_at=now,
            invalidated_at=None,
        )
        session.add(token)
        await session.flush()
        return token

    async def get_pending_commands(
        self,
        session: AsyncSession,
        payload: DeviceCommandSyncRequest,
    ) -> list[CommandEnvelopeResponse]:
        await self._verify_device_identity(session, payload.org_id, payload.device_id, payload.key_id)
        await self._expire_stale_commands(session, device_id=payload.device_id)
        now = datetime.now(timezone.utc)
        rows = list(
            (
                await session.execute(
                    select(RemoteAction)
                    .where(
                        RemoteAction.org_id == payload.org_id,
                        RemoteAction.device_id == payload.device_id,
                        RemoteAction.state.in_(
                            [RemoteActionState.PENDING, RemoteActionState.SENT, RemoteActionState.DELIVERED]
                        ),
                        or_(RemoteAction.expires_at.is_(None), RemoteAction.expires_at > now),
                    )
                    .order_by(RemoteAction.requested_at.asc())
                )
            ).scalars().all()
        )
        envelopes: list[CommandEnvelopeResponse] = []
        for action in rows:
            if action.state in {RemoteActionState.PENDING, RemoteActionState.SENT}:
                action.state = RemoteActionState.DELIVERED
                action.delivered_at = action.delivered_at or now
                action.updated_at = now
            envelopes.append(self._to_envelope(action))
        await session.flush()
        return envelopes

    async def acknowledge_command(
        self,
        session: AsyncSession,
        command_id: UUID,
        payload: CommandAckRequest,
    ) -> RemoteAction:
        await self._verify_device_identity(session, payload.org_id, payload.device_id, payload.key_id)
        action = (
            await session.execute(
                select(RemoteAction).where(
                    RemoteAction.id == command_id,
                    RemoteAction.org_id == payload.org_id,
                    RemoteAction.device_id == payload.device_id,
                )
            )
        ).scalar_one_or_none()
        if action is None:
            raise ValueError('Unknown command_id')
        now = datetime.now(timezone.utc)
        if payload.status == RemoteActionState.DELIVERED:
            action.state = RemoteActionState.DELIVERED
            action.delivered_at = action.delivered_at or now
        elif payload.status == RemoteActionState.ACKED:
            action.state = RemoteActionState.ACKED
            action.acked_at = now
        elif payload.status == RemoteActionState.FAILED:
            action.state = RemoteActionState.FAILED
            action.failed_at = now
            action.last_error = payload.error_message
        elif payload.status == RemoteActionState.EXPIRED:
            action.state = RemoteActionState.EXPIRED
            action.last_error = payload.error_message or 'Expired on device before execution.'
        else:
            raise ValueError('Only DELIVERED, ACKED, FAILED, or EXPIRED are allowed for command acknowledgement.')
        action.acknowledgement_metadata_json = payload.metadata
        action.updated_at = now
        await session.flush()
        return action

    async def retry_pending_commands(
        self,
        session: AsyncSession,
        *,
        org_id: UUID | None = None,
        device_id: UUID | None = None,
    ) -> RetryDispatchResult:
        await self._expire_stale_commands(session, device_id=device_id, org_id=org_id)
        now = datetime.now(timezone.utc)
        stmt = select(RemoteAction).where(
            RemoteAction.state.in_([RemoteActionState.PENDING, RemoteActionState.SENT]),
            or_(RemoteAction.expires_at.is_(None), RemoteAction.expires_at > now),
        )
        if org_id is not None:
            stmt = stmt.where(RemoteAction.org_id == org_id)
        if device_id is not None:
            stmt = stmt.where(RemoteAction.device_id == device_id)
        actions = list((await session.execute(stmt.order_by(RemoteAction.requested_at.asc()))).scalars().all())

        sent = 0
        failed = 0
        for action in actions:
            delivered = await self._dispatch_action(session, action)
            if delivered:
                sent += 1
            else:
                failed += 1
        expired = len([action for action in actions if action.state == RemoteActionState.EXPIRED])
        return RetryDispatchResult(processed=len(actions), sent=sent, failed=failed, expired=expired)

    async def expire_action(
        self,
        session: AsyncSession,
        *,
        remote_action_id: UUID,
        reason: str,
    ) -> RemoteAction:
        action = (
            await session.execute(select(RemoteAction).where(RemoteAction.id == remote_action_id))
        ).scalar_one_or_none()
        if action is None:
            raise ValueError('Unknown remote_action_id')
        now = datetime.now(timezone.utc)
        action.state = RemoteActionState.EXPIRED
        action.updated_at = now
        action.last_error = reason[:250]
        return action

    async def _dispatch_action(self, session: AsyncSession, action: RemoteAction) -> bool:
        now = datetime.now(timezone.utc)
        if action.delayed_until and action.delayed_until > now:
            return False
        if action.expires_at and action.expires_at <= now:
            action.state = RemoteActionState.EXPIRED
            action.updated_at = now
            action.last_error = 'Command expired before delivery.'
            return False

        token = (
            await session.execute(
                select(DevicePushToken)
                .where(
                    DevicePushToken.device_id == action.device_id,
                    DevicePushToken.org_id == action.org_id,
                    DevicePushToken.is_active.is_(True),
                )
                .order_by(DevicePushToken.last_seen_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if token is None:
            action.last_error = 'No active push token for device.'
            action.updated_at = now
            return False

        render = self.notification_template_service.render_command(
            action_kind=action.action_kind,
            payload=action.command_payload_json,
            reason=action.reason,
        )
        event = await self.notification_event_service.create_for_device(
            session,
            org_id=action.org_id,
            device_id=action.device_id,
            remote_action_id=action.id,
            recipient_token=token.push_token,
            template=render.template,
            payload={
                'title': render.title,
                'body': render.body,
                'data': {
                    **render.data,
                    'remote_action_id': str(action.id),
                    'device_id': str(action.device_id),
                },
            },
            incident_id=action.incident_id,
        )
        action.attempt_count += 1
        action.updated_at = now
        if event.status == NotificationStatus.SENT:
            action.state = RemoteActionState.SENT
            action.sent_at = now
            action.last_error = None
            return True

        action.last_error = event.error_message or 'Push delivery failed.'
        if action.attempt_count >= settings.command_max_attempts:
            action.state = RemoteActionState.FAILED
            action.failed_at = now
        return False

    async def _expire_stale_commands(
        self,
        session: AsyncSession,
        *,
        device_id: UUID | None = None,
        org_id: UUID | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        stmt = select(RemoteAction).where(
            RemoteAction.state.in_([RemoteActionState.PENDING, RemoteActionState.SENT, RemoteActionState.DELIVERED]),
            RemoteAction.expires_at.is_not(None),
            RemoteAction.expires_at <= now,
        )
        if device_id is not None:
            stmt = stmt.where(RemoteAction.device_id == device_id)
        if org_id is not None:
            stmt = stmt.where(RemoteAction.org_id == org_id)
        for action in (await session.execute(stmt)).scalars().all():
            action.state = RemoteActionState.EXPIRED
            action.updated_at = now
            action.last_error = 'Command expired before acknowledgement.'

    async def _get_device(self, session: AsyncSession, device_id: UUID) -> Device:
        device = (await session.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
        if device is None:
            raise ValueError('Unknown device_id')
        return device

    async def _verify_device_identity(self, session: AsyncSession, org_id: UUID, device_id: UUID, key_id: str) -> None:
        device = await self._get_device(session, device_id)
        if device.organization_id != org_id:
            raise ValueError('Device does not belong to tenant org.')
        active_enrollment = (
            await session.execute(
                select(Enrollment).where(
                    Enrollment.org_id == org_id,
                    Enrollment.device_id == device_id,
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                )
            )
        ).scalar_one_or_none()
        if active_enrollment is None:
            raise ValueError('Device has no active enrollment.')
        active_key = (
            await session.execute(
                select(DeviceKey).where(
                    DeviceKey.org_id == org_id,
                    DeviceKey.device_id == device_id,
                    DeviceKey.key_id == key_id,
                    DeviceKey.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if active_key is None:
            raise ValueError('Device identity verification failed.')

    def _build_payload(
        self,
        payload: CommandQueueRequest,
        *,
        actor_sub: str,
        requested_at: datetime,
        remote_action_id: UUID,
        expires_at: datetime | None,
    ) -> dict:
        return {
            'remote_action_id': str(remote_action_id),
            'org_id': str(payload.org_id),
            'device_id': str(payload.device_id),
            'incident_id': str(payload.incident_id) if payload.incident_id else None,
            'action_kind': payload.action_kind.value,
            'reason': payload.reason,
            'lost_mode_until': payload.lost_mode_until.isoformat() if payload.lost_mode_until else None,
            'recovery_message': payload.recovery_message,
            'requested_by_sub': actor_sub,
            'requested_at': requested_at.isoformat(),
            'delayed_until': payload.delayed_until.isoformat() if payload.delayed_until else None,
            'expires_at': expires_at.isoformat() if expires_at else None,
        }

    def _to_envelope(self, action: RemoteAction) -> CommandEnvelopeResponse:
        return CommandEnvelopeResponse(
            remote_action_id=action.id,
            org_id=action.org_id,
            device_id=action.device_id,
            incident_id=action.incident_id,
            action_kind=action.action_kind,
            state=action.state,
            reason=action.reason,
            payload=action.command_payload_json,
            signature=action.command_signature,
            signature_algorithm=action.signature_algorithm,
            requested_by_sub=action.requested_by_sub,
            requested_at=action.requested_at,
            expires_at=action.expires_at,
        )
