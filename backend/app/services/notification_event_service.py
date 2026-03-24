from __future__ import annotations

from datetime import datetime, timezone
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NotificationEvent, NotificationStatus
from app.schemas.platform import NotificationCreateRequest
from app.services.notification_service import NotificationMessage, NotificationService

logger = logging.getLogger(__name__)


class NotificationEventService:
    def __init__(self, provider: NotificationService) -> None:
        self.provider = provider

    async def create_and_send(
        self,
        session: AsyncSession,
        payload: NotificationCreateRequest,
    ) -> NotificationEvent:
        record = NotificationEvent(
            org_id=payload.org_id,
            incident_id=payload.incident_id,
            device_id=payload.device_id,
            remote_action_id=payload.remote_action_id,
            recipient_sub=payload.recipient_sub,
            recipient_token=payload.recipient_token,
            channel=payload.channel,
            template=payload.template,
            payload_json=payload.payload,
            status=NotificationStatus.QUEUED,
            created_at=datetime.now(timezone.utc),
            sent_at=None,
            provider_message_id=None,
            error_message=None,
        )
        session.add(record)
        await session.flush()

        try:
            provider_message_id = await self.provider.send(
                NotificationMessage(
                    title=str(payload.payload.get('title', payload.template)),
                    body=str(payload.payload.get('body', payload.payload)),
                    device_token=payload.recipient_token or payload.recipient_sub or 'unknown-recipient',
                    data={k: str(v) for k, v in payload.payload.get('data', {}).items()},
                )
            )
            record.status = NotificationStatus.SENT
            record.sent_at = datetime.now(timezone.utc)
            record.provider_message_id = provider_message_id
        except Exception as exc:  # pragma: no cover
            logger.exception(
                'Notification delivery failed',
                extra={
                    'org_id': str(payload.org_id),
                    'device_id': str(payload.device_id) if payload.device_id else None,
                    'incident_id': str(payload.incident_id) if payload.incident_id else None,
                    'template': payload.template,
                    'channel': payload.channel,
                },
            )
            record.status = NotificationStatus.FAILED
            record.error_message = str(exc)[:250]
        await session.flush()
        return record

    async def create_for_device(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        remote_action_id: UUID | None,
        recipient_token: str,
        template: str,
        payload: dict,
        incident_id: UUID | None = None,
    ) -> NotificationEvent:
        return await self.create_and_send(
            session,
            NotificationCreateRequest(
                org_id=org_id,
                incident_id=incident_id,
                device_id=device_id,
                remote_action_id=remote_action_id,
                recipient_sub=None,
                recipient_token=recipient_token,
                channel='fcm',
                template=template,
                payload=payload,
            ),
        )

    async def create_internal_alert(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        template: str,
        payload: dict,
        device_id: UUID | None = None,
        incident_id: UUID | None = None,
        remote_action_id: UUID | None = None,
        recipient_sub: str | None = None,
    ) -> NotificationEvent:
        record = NotificationEvent(
            org_id=org_id,
            incident_id=incident_id,
            device_id=device_id,
            remote_action_id=remote_action_id,
            recipient_sub=recipient_sub,
            recipient_token=None,
            channel='internal',
            template=template,
            payload_json=payload,
            status=NotificationStatus.SENT,
            provider_message_id='internal-alert',
            error_message=None,
            created_at=datetime.now(timezone.utc),
            sent_at=datetime.now(timezone.utc),
        )
        session.add(record)
        await session.flush()
        return record
