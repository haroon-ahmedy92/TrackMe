from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationMessage:
    title: str
    body: str
    device_token: str
    data: dict[str, str] = field(default_factory=dict)


class NotificationService:
    async def send(self, message: NotificationMessage) -> str:
        raise NotImplementedError


class NotificationDeliveryError(RuntimeError):
    pass


class FcmNotificationService(NotificationService):
    async def send(self, message: NotificationMessage) -> str:
        if not settings.fcm_server_key:
            logger.error('FCM delivery requested without FCM_SERVER_KEY configured')
            raise NotificationDeliveryError('FCM_SERVER_KEY is not configured. Push delivery cannot proceed.')

        headers = {
            'Authorization': f'key={settings.fcm_server_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'to': message.device_token,
            'priority': 'high',
            'notification': {
                'title': message.title,
                'body': message.body,
            },
            'data': message.data,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(settings.fcm_endpoint, headers=headers, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.exception('FCM push delivery failed')
                raise NotificationDeliveryError(f'FCM delivery failed: {exc}') from exc
            body = response.json()
        return body.get('message_id') or body.get('name') or f'fcm-{uuid.uuid4()}'
