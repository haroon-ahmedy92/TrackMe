from __future__ import annotations

from dataclasses import dataclass

from app.db.models import RemoteActionKind


@dataclass(frozen=True)
class NotificationTemplateRender:
    template: str
    title: str
    body: str
    data: dict[str, str]


class NotificationTemplateService:
    def render_command(self, *, action_kind: RemoteActionKind, payload: dict, reason: str) -> NotificationTemplateRender:
        if action_kind == RemoteActionKind.ENTER_LOST_MODE:
            return NotificationTemplateRender(
                template='lost_mode',
                title='Lost mode requested',
                body=f'This enrolled device has been placed into recovery lost mode. Reason: {reason}',
                data={'command_type': action_kind.value, 'reason': reason, 'sync_pending_commands': 'true'},
            )
        if action_kind == RemoteActionKind.DISPLAY_RECOVERY_MESSAGE:
            message = payload.get('recovery_message') or 'A recovery message is ready for this device.'
            return NotificationTemplateRender(
                template='recovery_update',
                title='Recovery update',
                body=message,
                data={'command_type': action_kind.value, 'reason': reason, 'sync_pending_commands': 'true'},
            )
        if action_kind in {RemoteActionKind.LOCK, RemoteActionKind.WIPE}:
            return NotificationTemplateRender(
                template='remote_action_confirmation',
                title='Sensitive device action queued',
                body=f'{action_kind.value.replace("_", " ").title()} command queued for this device. Reason: {reason}',
                data={'command_type': action_kind.value, 'reason': reason, 'sync_pending_commands': 'true'},
            )
        return NotificationTemplateRender(
            template='approval_request',
            title='Device command queued',
            body='A device command is waiting for delivery.',
            data={'command_type': action_kind.value, 'reason': reason, 'sync_pending_commands': 'true'},
        )
