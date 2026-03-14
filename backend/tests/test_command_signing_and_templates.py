from datetime import datetime, timezone

from app.db.models import RemoteActionKind
from app.services.command_signing_service import CommandSigningService
from app.services.notification_template_service import NotificationTemplateService


def test_command_signing_service_detects_tampering() -> None:
    service = CommandSigningService()
    payload = {
        'remote_action_id': 'cmd-1',
        'device_id': 'device-1',
        'action_kind': 'display_recovery_message',
        'recovery_message': 'Call owner',
    }
    signature = service.sign(payload)

    assert service.verify(payload, signature)
    assert not service.verify({**payload, 'recovery_message': 'Tampered'}, signature)


def test_notification_template_service_renders_lost_mode_and_recovery_message() -> None:
    service = NotificationTemplateService()
    lost_render = service.render_command(
        action_kind=RemoteActionKind.ENTER_LOST_MODE,
        payload={
            'lost_mode_until': datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc).isoformat(),
        },
        reason='Active recovery incident',
    )
    recovery_render = service.render_command(
        action_kind=RemoteActionKind.DISPLAY_RECOVERY_MESSAGE,
        payload={'recovery_message': 'Please return this phone to reception.'},
        reason='Return contact visible on lock screen',
    )

    assert lost_render.template == 'lost_mode'
    assert 'Active recovery incident' in lost_render.body
    assert recovery_render.template == 'recovery_update'
    assert 'Please return this phone' in recovery_render.body
