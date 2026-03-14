from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_audit_log_service, get_compliance_service, get_ownership_access_service
from app.core.security import Principal, Role, get_current_principal
from app.db.base import get_db_session
from app.main import app


class DummySession:
    async def commit(self):
        return None


async def _dummy_db_session():
    yield DummySession()


class FakeAuditLogService:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def append(self, session, *, action: str, **kwargs):
        self.actions.append(action)
        return None


class FakeComplianceService:
    def __init__(self) -> None:
        self.settings_id = uuid4()
        self.deprovision_calls: list[tuple[str, str, str]] = []

    async def get_or_create_settings(self, session, *, org_id):
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=self.settings_id,
            org_id=org_id,
            location_event_days=30,
            audit_log_days=90,
            incident_evidence_days=60,
            updated_at=now,
            updated_by_sub='admin@example.com',
        )

    async def update_retention_policy(self, session, *, payload, actor_sub):
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=self.settings_id,
            org_id=payload.org_id,
            location_event_days=payload.location_event_days,
            audit_log_days=payload.audit_log_days,
            incident_evidence_days=payload.incident_evidence_days,
            updated_at=now,
            updated_by_sub=actor_sub,
        )

    async def create_abuse_report(self, session, *, payload, reported_by_sub):
        return SimpleNamespace(
            id=uuid4(),
            org_id=payload.org_id,
            device_id=payload.device_id,
            category=payload.category,
            description=payload.description,
            contact_email=payload.contact_email,
            reported_by_sub=reported_by_sub,
            status='submitted',
            created_at=datetime.now(timezone.utc),
        )

    async def list_access_history(self, session, *, org_id, device_id, limit=50):
        return [
            SimpleNamespace(
                id=uuid4(),
                actor_sub='admin@example.com',
                action='LOCATION_LOOKUP_REQUESTED',
                occurred_at=datetime.now(timezone.utc),
                metadata_json={'reason': 'Investigating report', 'result': 'requested', 'device_id': str(device_id)},
            ),
            SimpleNamespace(
                id=uuid4(),
                actor_sub='admin@example.com',
                action='LOCATION_LOOKUP_RESULT',
                occurred_at=datetime.now(timezone.utc),
                metadata_json={'reason': 'Investigating report', 'result': 'success', 'device_id': str(device_id)},
            ),
        ]

    async def deprovision_device(self, session, *, org_id, device_id, requested_by_sub, reason):
        self.deprovision_calls.append((str(org_id), str(device_id), requested_by_sub))
        return SimpleNamespace(
            id=uuid4(),
            org_id=org_id,
            device_id=device_id,
            requested_by_sub=requested_by_sub,
            reason=reason,
            status=SimpleNamespace(value='completed'),
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )


class FakeOwnershipAccessService:
    def __init__(self, owner_subject: str | None = 'owner@example.com') -> None:
        self.owner_subject = owner_subject

    async def get_active_binding(self, session, device_id):
        return SimpleNamespace(id=uuid4(), org_id=uuid4(), device_id=device_id, owner_user_id=uuid4())

    async def get_owner_subject(self, session, binding):
        return self.owner_subject


class NoOwnerBindingService(FakeOwnershipAccessService):
    def __init__(self) -> None:
        super().__init__(owner_subject='another-owner@example.com')



def _principal(subject: str, roles: list[Role], org_id: str):
    return lambda: Principal(subject=subject, roles=set(roles), organization_id=org_id)


def test_platform_settings_returns_short_defaults() -> None:
    org_id = str(uuid4())
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_current_principal] = _principal('admin@example.com', [Role.ADMIN], org_id)
    app.dependency_overrides[get_compliance_service] = lambda: FakeComplianceService()
    try:
        client = TestClient(app)
        response = client.get('/api/v1/platform/settings', params={'org_id': org_id})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload['retention_policy']['location_event_days'] == 30
    assert payload['privacy_defaults']['explicit_consent_required'] is True


def test_retention_update_requires_admin_and_audits() -> None:
    org_id = str(uuid4())
    audit_service = FakeAuditLogService()
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_current_principal] = _principal('admin@example.com', [Role.ADMIN], org_id)
    app.dependency_overrides[get_compliance_service] = lambda: FakeComplianceService()
    app.dependency_overrides[get_audit_log_service] = lambda: audit_service
    try:
        client = TestClient(app)
        response = client.put(
            '/api/v1/platform/settings/retention-policy',
            json={
                'org_id': org_id,
                'location_event_days': 21,
                'audit_log_days': 120,
                'incident_evidence_days': 45,
                'reason': 'Reduce retained location footprint for compliance review',
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()['location_event_days'] == 21
    assert 'RETENTION_POLICY_UPDATED' in audit_service.actions


def test_abuse_report_submission_is_audited() -> None:
    org_id = str(uuid4())
    audit_service = FakeAuditLogService()
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_current_principal] = _principal('owner@example.com', [Role.OWNER], org_id)
    app.dependency_overrides[get_compliance_service] = lambda: FakeComplianceService()
    app.dependency_overrides[get_audit_log_service] = lambda: audit_service
    try:
        client = TestClient(app)
        response = client.post(
            '/api/v1/platform/abuse-reports',
            json={
                'org_id': org_id,
                'category': 'unauthorized_lookup',
                'description': 'Repeated lookups without a valid support ticket',
                'contact_email': 'owner@example.com',
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()['status'] == 'submitted'
    assert 'ABUSE_REPORT_SUBMITTED' in audit_service.actions


def test_access_history_endpoint_returns_locate_audit_chain() -> None:
    org_id = str(uuid4())
    device_id = uuid4()
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_current_principal] = _principal('owner@example.com', [Role.OWNER], org_id)
    app.dependency_overrides[get_compliance_service] = lambda: FakeComplianceService()
    app.dependency_overrides[get_ownership_access_service] = lambda: FakeOwnershipAccessService()
    try:
        client = TestClient(app)
        response = client.get(f'/api/v1/ownership/devices/{device_id}/access-history', params={'org_id': org_id})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]['action'] == 'LOCATION_LOOKUP_REQUESTED'


def test_owner_deprovision_requires_bound_owner_subject() -> None:
    org_id = str(uuid4())
    device_id = uuid4()
    audit_service = FakeAuditLogService()
    compliance_service = FakeComplianceService()
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_current_principal] = _principal('owner@example.com', [Role.OWNER], org_id)
    app.dependency_overrides[get_compliance_service] = lambda: compliance_service
    app.dependency_overrides[get_ownership_access_service] = lambda: NoOwnerBindingService()
    app.dependency_overrides[get_audit_log_service] = lambda: audit_service
    try:
        client = TestClient(app)
        response = client.post(
            f'/api/v1/ownership/devices/{device_id}/deprovision',
            params={'org_id': org_id},
            json={'reason': 'Employee leaving organization and device must be unmanaged'},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert compliance_service.deprovision_calls == []


def test_admin_deprovision_audits_completion() -> None:
    org_id = str(uuid4())
    device_id = uuid4()
    audit_service = FakeAuditLogService()
    compliance_service = FakeComplianceService()
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_current_principal] = _principal('admin@example.com', [Role.ADMIN], org_id)
    app.dependency_overrides[get_compliance_service] = lambda: compliance_service
    app.dependency_overrides[get_ownership_access_service] = lambda: FakeOwnershipAccessService()
    app.dependency_overrides[get_audit_log_service] = lambda: audit_service
    try:
        client = TestClient(app)
        response = client.post(
            f'/api/v1/ownership/devices/{device_id}/deprovision',
            params={'org_id': org_id},
            json={'reason': 'Device returned to stock and should no longer remain managed'},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()['status'] == 'completed'
    assert 'DEVICE_DEPROVISIONED' in audit_service.actions
