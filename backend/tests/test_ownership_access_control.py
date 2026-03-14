from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from app.api.deps import get_audit_log_service, get_ownership_access_service
from app.core.security import Principal, Role, get_current_principal
from app.db.models import DeviceAccessPolicy
from app.main import app
from app.services.ownership_access_service import OwnershipAccessService


class FakeAuditLogService:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def append(self, session, *, action: str, **kwargs):
        self.actions.append(action)
        return None


class FakeLocateService:
    def __init__(self, *, owner_subject: str | None, allowed: bool = True) -> None:
        self.owner_subject = owner_subject
        self.allowed = allowed

    async def get_active_binding(self, session, device_id):
        return SimpleNamespace(id=uuid4(), org_id=uuid4(), device_id=device_id, owner_user_id=uuid4() if self.owner_subject else None)

    async def get_owner_subject(self, session, binding):
        return self.owner_subject

    async def get_policy(self, session, device_id):
        return DeviceAccessPolicy(
            id=uuid4(),
            org_id=uuid4(),
            device_id=device_id,
            owner_can_locate=True,
            admin_can_locate=True,
            security_operator_can_review=True,
            require_access_review=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def authorize_locate(self, *, principal_roles, principal_subject, owner_subject, policy):
        if self.allowed:
            return SimpleNamespace(allowed=True, reason='allowed', owner_subject=owner_subject)
        return SimpleNamespace(allowed=False, reason='policy_denied', owner_subject=owner_subject)

    async def locate_device(self, session, *, org_id, device_id):
        return SimpleNamespace(
            precision=SimpleNamespace(value='precise'),
            confidence_score=92,
            is_ip_approximate=False,
            latitude=DecimalLike(1.23),
            longitude=DecimalLike(2.34),
            accuracy_meters=DecimalLike(8.0),
            captured_at=datetime.now(timezone.utc),
            source_methods={'methods': ['gps', 'geofence']},
        )

    async def verify_device_identity(self, session, payload):  # pragma: no cover
        return True, True, True


class DecimalLike(float):
    pass


class DummySession:
    async def commit(self):
        return None



async def _dummy_db_session():
    yield DummySession()



def _override_principal(subject: str, roles: list[Role], org_id: str):
    return lambda: Principal(subject=subject, roles=set(roles), organization_id=org_id)


def test_parse_pairing_token_from_qr_uri() -> None:
    service = OwnershipAccessService()
    token = service.parse_pairing_token('trackme://pair?token=abc123xyz')
    assert token == 'abc123xyz'


def test_authorize_locate_owner_allowed() -> None:
    service = OwnershipAccessService()
    policy = DeviceAccessPolicy(
        id=uuid4(),
        org_id=uuid4(),
        device_id=uuid4(),
        owner_can_locate=True,
        admin_can_locate=True,
        security_operator_can_review=True,
        require_access_review=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    result = service.authorize_locate(
        principal_roles={'owner'},
        principal_subject='owner-sub',
        owner_subject='owner-sub',
        policy=policy,
    )
    assert result.allowed is True
    assert result.reason == 'owner_allowed'


def test_authorize_locate_owner_denied_on_binding_mismatch() -> None:
    service = OwnershipAccessService()
    policy = DeviceAccessPolicy(
        id=uuid4(),
        org_id=uuid4(),
        device_id=uuid4(),
        owner_can_locate=True,
        admin_can_locate=True,
        security_operator_can_review=True,
        require_access_review=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    result = service.authorize_locate(
        principal_roles={'owner'},
        principal_subject='other-owner',
        owner_subject='bound-owner',
        policy=policy,
    )
    assert result.allowed is False
    assert result.reason == 'owner_binding_mismatch'


def test_authorize_locate_security_operator_denied() -> None:
    service = OwnershipAccessService()
    policy = DeviceAccessPolicy(
        id=uuid4(),
        org_id=uuid4(),
        device_id=uuid4(),
        owner_can_locate=True,
        admin_can_locate=True,
        security_operator_can_review=True,
        require_access_review=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    result = service.authorize_locate(
        principal_roles={'security_operator'},
        principal_subject='sec-op',
        owner_subject='bound-owner',
        policy=policy,
    )
    assert result.allowed is False
    assert result.reason == 'role_not_allowed'


def test_locate_endpoint_allows_owner_and_audits() -> None:
    org_id = str(uuid4())
    device_id = uuid4()
    audit_service = FakeAuditLogService()
    locate_service = FakeLocateService(owner_subject='owner-sub', allowed=True)
    from app.db.base import get_db_session

    app.dependency_overrides[get_current_principal] = _override_principal('owner-sub', [Role.OWNER], org_id)
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_audit_log_service] = lambda: audit_service
    app.dependency_overrides[get_ownership_access_service] = lambda: locate_service
    try:
        client = TestClient(app)
        response = client.post(
            f'/api/v1/ownership/devices/{device_id}/locate',
            params={'org_id': org_id},
            json={'reason': 'Investigating reported loss'},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload['device_id'] == str(device_id)
        assert payload['precision'] == 'precise'
        assert 'LOCATION_LOOKUP_REQUESTED' in audit_service.actions
        assert 'LOCATION_LOOKUP_RESULT' in audit_service.actions
    finally:
        app.dependency_overrides.clear()


def test_locate_endpoint_rejects_security_operator_role() -> None:
    org_id = str(uuid4())
    device_id = uuid4()
    app.dependency_overrides[get_current_principal] = _override_principal('sec-op', [Role.SECURITY_OPERATOR], org_id)
    try:
        client = TestClient(app)
        response = client.post(
            f'/api/v1/ownership/devices/{device_id}/locate',
            params={'org_id': org_id},
            json={'reason': 'Checking device'},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
