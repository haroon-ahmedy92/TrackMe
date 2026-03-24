from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_local_auth_service
from app.db.base import get_db_session
from app.main import app


class DummySession:
    async def commit(self):
        return None


async def _dummy_db_session():
    yield DummySession()


class FakeLocalAuthService:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    async def authenticate(self, session, *, email: str, password: str):
        if self.should_fail:
            raise PermissionError('Invalid email or password.')
        return SimpleNamespace(
            user=SimpleNamespace(id=uuid4(), org_id=uuid4()),
            email=email,
            full_name='Pilot Admin',
            token='signed-jwt',
            ui_role='admin',
        )


def test_login_returns_operator_profile() -> None:
    app.dependency_overrides[get_local_auth_service] = lambda: FakeLocalAuthService()
    app.dependency_overrides[get_db_session] = _dummy_db_session
    try:
        client = TestClient(app)
        response = client.post(
            '/api/v1/auth/login',
            json={'email': 'pilot@example.com', 'password': 'password123'},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload['access_token'] == 'signed-jwt'
    assert payload['profile']['email'] == 'pilot@example.com'
    assert payload['profile']['role'] == 'admin'


def test_login_rejects_invalid_credentials() -> None:
    app.dependency_overrides[get_local_auth_service] = lambda: FakeLocalAuthService(should_fail=True)
    app.dependency_overrides[get_db_session] = _dummy_db_session
    try:
        client = TestClient(app)
        response = client.post(
            '/api/v1/auth/login',
            json={'email': 'pilot@example.com', 'password': 'wrongpass'},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid email or password.'
