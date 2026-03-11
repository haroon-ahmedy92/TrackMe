from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationMessage:
    title: str
    body: str
    device_token: str


class NotificationService:
    async def send(self, message: NotificationMessage) -> None:
        raise NotImplementedError


class NoopNotificationService(NotificationService):
    async def send(self, message: NotificationMessage) -> None:
        # Placeholder for Firebase Cloud Messaging integration.
        return None
