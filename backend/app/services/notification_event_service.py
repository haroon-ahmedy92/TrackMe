from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NotificationEvent, NotificationStatus
from app.schemas.platform import NotificationCreateRequest
from app.services.notification_service import NotificationMessage, NotificationService


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
            recipient_sub=payload.recipient_sub,
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
            await self.provider.send(
                NotificationMessage(
                    title=payload.template,
                    body=str(payload.payload),
                    device_token=payload.recipient_sub or 'unknown-recipient',
                )
            )
            record.status = NotificationStatus.SENT
            record.sent_at = datetime.now(timezone.utc)
            record.provider_message_id = f'noop-{record.id}'
        except Exception as exc:  # pragma: no cover
            record.status = NotificationStatus.FAILED
            record.error_message = str(exc)[:250]
        await session.flush()
        return record
