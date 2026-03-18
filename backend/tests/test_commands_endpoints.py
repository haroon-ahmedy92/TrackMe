from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_audit_log_service, get_command_queue_service, get_signed_telemetry_service
from app.core.security import Principal, Role, get_current_principal
from app.db.models import RemoteActionKind, RemoteActionState
from app.main import app


class FakeAuditLogService:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def append(self, session, *, action: str, **kwargs):
        self.actions.append(action)
        return None


class FakeCommandQueueService:
    def __init__(self) -> None:
        self.command_id = uuid4()
        self.org_id = uuid4()
        self.device_id = uuid4()
        self.updated_at = datetime.now(timezone.utc)

    async def queue_command(self, session, payload, *, actor_sub: str):
        self.org_id = payload.org_id
        self.device_id = payload.device_id
        return SimpleNamespace(
            id=self.command_id,
            org_id=payload.org_id,
            device_id=payload.device_id,
            incident_id=payload.incident_id,
            action_kind=payload.action_kind,
            state=RemoteActionState.PENDING,
            reason=payload.reason,
            command_payload_json={'recovery_message': payload.recovery_message},
            command_signature='signed',
            signature_algorithm='HMAC_SHA256_PLACEHOLDER',
            requested_by_sub=actor_sub,
            requested_at=self.updated_at,
            expires_at=payload.expires_at,
            updated_at=self.updated_at,
        )

    async def retry_pending_commands(self, session, *, org_id=None, device_id=None):
        return SimpleNamespace(processed=1, sent=1, failed=0, expired=0)

    def _to_envelope(self, action):
        from app.schemas.commands import CommandEnvelopeResponse

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

    async def register_push_token(self, session, payload):
        return SimpleNamespace(
            id=uuid4(),
            org_id=payload.org_id,
            device_id=payload.device_id,
            key_id=payload.key_id,
            is_active=True,
            last_seen_at=self.updated_at,
        )

    async def get_pending_commands(self, session, payload):
        from app.schemas.commands import CommandEnvelopeResponse

        return [
            CommandEnvelopeResponse(
                remote_action_id=self.command_id,
                org_id=payload.org_id,
                device_id=payload.device_id,
                incident_id=None,
                action_kind=RemoteActionKind.DISPLAY_RECOVERY_MESSAGE,
                state=RemoteActionState.DELIVERED,
                reason='Visible recovery banner requested',
                payload={'recovery_message': 'Please return this device to reception.'},
                signature='signed',
                signature_algorithm='HMAC_SHA256_PLACEHOLDER',
                requested_by_sub='admin@example.com',
                requested_at=self.updated_at,
                expires_at=None,
            )
        ]

    async def acknowledge_command(self, session, command_id, payload):
        return SimpleNamespace(id=command_id, state=payload.status, updated_at=self.updated_at)


class DummySession:
    async def commit(self):
        return None


async def _dummy_db_session():
    yield DummySession()


def _override_principal(subject: str, roles: list[Role], org_id: str):
    return lambda: Principal(subject=subject, roles=set(roles), organization_id=org_id)


class FakeSignedTelemetryService:
    def __init__(self, *, accepted: bool, reason: str = 'verified') -> None:
        self.accepted = accepted
        self.reason = reason

    async def verify_command_ack_request(self, session, *, command_id, device_id, payload):
        return SimpleNamespace(accepted=self.accepted, reason=self.reason)


def test_queue_command_endpoint_audits_sensitive_action() -> None:
    fake_service = FakeCommandQueueService()
    audit_service = FakeAuditLogService()
    org_id = str(fake_service.org_id)
    app.dependency_overrides[get_current_principal] = _override_principal('admin@example.com', [Role.ADMIN], org_id)
    app.dependency_overrides[get_command_queue_service] = lambda: fake_service
    app.dependency_overrides[get_audit_log_service] = lambda: audit_service
    from app.db.base import get_db_session
    app.dependency_overrides[get_db_session] = _dummy_db_session
    try:
        client = TestClient(app)
        response = client.post(
            '/api/v1/commands',
            json={
                'org_id': org_id,
                'device_id': str(fake_service.device_id),
                'action_kind': 'display_recovery_message',
                'reason': 'Visible recovery message requested',
                'recovery_message': 'Please return this device to reception.',
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload['action_kind'] == 'display_recovery_message'
    assert 'COMMAND_DISPLAY_RECOVERY_MESSAGE_QUEUED' in audit_service.actions


def test_sync_endpoint_returns_pending_commands_for_device() -> None:
    fake_service = FakeCommandQueueService()
    from app.db.base import get_db_session
    app.dependency_overrides[get_command_queue_service] = lambda: fake_service
    app.dependency_overrides[get_db_session] = _dummy_db_session
    try:
        client = TestClient(app)
        response = client.post(
            '/api/v1/commands/sync',
            json={
                'org_id': str(fake_service.org_id),
                'device_id': str(fake_service.device_id),
                'key_id': 'trackme-device-key',
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]['state'] == 'delivered'


def test_ack_endpoint_records_audit_entry() -> None:
    fake_service = FakeCommandQueueService()
    audit_service = FakeAuditLogService()
    from app.db.base import get_db_session
    app.dependency_overrides[get_command_queue_service] = lambda: fake_service
    app.dependency_overrides[get_audit_log_service] = lambda: audit_service
    app.dependency_overrides[get_db_session] = _dummy_db_session
    try:
        client = TestClient(app)
        response = client.post(
            f'/api/v1/commands/{fake_service.command_id}/ack',
            json={
                'org_id': str(fake_service.org_id),
                'device_id': str(fake_service.device_id),
                'key_id': 'trackme-device-key',
                'status': 'acked',
                'metadata': {'executedAtEpochMs': '1710410000000'},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert 'COMMAND_ACKED_RECORDED' in audit_service.actions


def test_ack_endpoint_rejects_invalid_signed_acknowledgement() -> None:
    fake_service = FakeCommandQueueService()
    from app.db.base import get_db_session
    app.dependency_overrides[get_command_queue_service] = lambda: fake_service
    app.dependency_overrides[get_signed_telemetry_service] = lambda: FakeSignedTelemetryService(
        accepted=False,
        reason='signature_mismatch',
    )
    app.dependency_overrides[get_db_session] = _dummy_db_session
    try:
        client = TestClient(app)
        response = client.post(
            f'/api/v1/commands/{fake_service.command_id}/ack',
            json={
                'org_id': str(fake_service.org_id),
                'device_id': str(fake_service.device_id),
                'key_id': 'trackme-device-key',
                'status': 'acked',
                'metadata': {'executedAtEpochMs': '1710410000000'},
                'telemetry_signature': 'invalid',
                'telemetry_algorithm': 'SHA256withECDSA',
                'telemetry_payload_hash': 'a' * 64,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid signed command acknowledgement: signature_mismatch'
