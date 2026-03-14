from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_audit_log_service, get_geofence_service, get_spatial_service
from app.core.config import settings
from app.core.security import Principal, Role, get_current_principal
from app.main import app
from app.services.geofence_service import GeofenceService
from app.services.spatial_service import SpatialService


class DummySession:
    async def commit(self):
        return None


async def _dummy_db_session():
    yield DummySession()


def _override_principal(org_id: str):
    return lambda: Principal(subject='admin@example.com', roles={Role.ADMIN}, organization_id=org_id)


class FakeAuditLogService:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def append(self, session, *, action: str, **kwargs):
        self.actions.append(action)
        return None


class FakeSpatialEndpointService:
    def __init__(self) -> None:
        self.org_id = uuid4()
        self.device_id = uuid4()
        self.incident_id = uuid4()

    def normalize_window(self, *, starts_at, ends_at, now=None):
        current = now or datetime.now(timezone.utc)
        return SimpleNamespace(
            starts_at=starts_at or current - timedelta(hours=24),
            ends_at=ends_at or current,
        )

    async def get_last_known_location(self, session, *, org_id, device_id):
        return SimpleNamespace(
            id=uuid4(),
            device_id=device_id,
            captured_at=datetime.now(timezone.utc),
            latitude=-6.7924,
            longitude=39.2083,
            accuracy_meters=18.0,
            precision='precise',
            confidence_score=91,
            source_methods={'methods': ['fused_gps']},
            is_ip_approximate=False,
        )

    async def get_location_history(self, session, *, org_id, device_id, starts_at, ends_at, limit=500):
        now = datetime.now(timezone.utc)
        return [
            SimpleNamespace(
                id=uuid4(),
                device_id=device_id,
                captured_at=now - timedelta(minutes=12),
                latitude=-6.7931,
                longitude=39.2077,
                accuracy_meters=20.0,
                precision='moderate',
                confidence_score=67,
                source_methods={'methods': ['last_known', 'network_context']},
                is_ip_approximate=False,
            ),
            SimpleNamespace(
                id=uuid4(),
                device_id=device_id,
                captured_at=now,
                latitude=-6.7924,
                longitude=39.2083,
                accuracy_meters=14.0,
                precision='precise',
                confidence_score=92,
                source_methods={'methods': ['fused_gps', 'geofence']},
                is_ip_approximate=False,
            ),
        ]

    async def get_geofence_events(self, session, *, org_id, device_id, starts_at, ends_at, limit=500):
        now = datetime.now(timezone.utc)
        return [
            (
                SimpleNamespace(
                    id=uuid4(),
                    geofence_id=uuid4(),
                    device_id=device_id,
                    event_type='exit',
                    precision='moderate',
                    confidence_score=58,
                    alert_emitted=True,
                    suppressed_reason=None,
                    triggered_at=now,
                ),
                'Arusha Depot',
            )
        ]

    async def get_device_clusters(self, session, *, org_id, starts_at, ends_at, cell_size_meters=10000):
        return [
            {
                'cluster_id': 'cluster-dar',
                'center_latitude': -6.7924,
                'center_longitude': 39.2083,
                'device_count': 2,
                'approximate_count': 0,
                'precise_count': 1,
                'moderate_count': 1,
                'latest_captured_at': datetime.now(timezone.utc),
                'device_ids': [self.device_id, uuid4()],
            }
        ]

    async def get_incident_route(self, session, *, org_id, incident_id, starts_at, ends_at, limit=500):
        return (
            SimpleNamespace(id=incident_id, device_id=self.device_id),
            await self.get_location_history(
                session,
                org_id=org_id,
                device_id=self.device_id,
                starts_at=starts_at,
                ends_at=ends_at,
                limit=limit,
            ),
            await self.get_geofence_events(
                session,
                org_id=org_id,
                device_id=self.device_id,
                starts_at=starts_at,
                ends_at=ends_at,
                limit=limit,
            ),
            self.normalize_window(starts_at=starts_at, ends_at=ends_at),
        )

    def source_label_for(self, event):
        return 'Fused GPS'


class FakeGeofenceService:
    def __init__(self) -> None:
        self.geofence_id = uuid4()
        self.device_id = uuid4()

    async def create_geofence(self, session, payload):
        return SimpleNamespace(
            id=self.geofence_id,
            org_id=payload.org_id,
            device_id=payload.device_id,
            name=payload.name,
            center_latitude=payload.center_latitude,
            center_longitude=payload.center_longitude,
            radius_meters=payload.radius_meters,
            is_enabled=True,
            created_at=datetime.now(timezone.utc),
        )

    async def list_geofences(self, session, *, org_id, device_id=None):
        return [
            SimpleNamespace(
                id=self.geofence_id,
                org_id=org_id,
                device_id=device_id or self.device_id,
                name='Dar HQ',
                center_latitude=-6.7924,
                center_longitude=39.2083,
                radius_meters=300,
                is_enabled=True,
                created_at=datetime.now(timezone.utc),
            )
        ]

    async def update_geofence(self, session, *, geofence_id, payload):
        return SimpleNamespace(
            id=geofence_id,
            org_id=payload.org_id,
            device_id=payload.device_id,
            name=payload.name,
            center_latitude=payload.center_latitude,
            center_longitude=payload.center_longitude,
            radius_meters=payload.radius_meters,
            is_enabled=payload.is_enabled,
            created_at=datetime.now(timezone.utc),
        )

    async def delete_geofence(self, session, *, geofence_id, org_id):
        return SimpleNamespace(id=geofence_id, name='Dar HQ')


class _ExecuteResult:
    def __init__(self, row):
        self._row = row

    def scalar_one_or_none(self):
        return self._row


class FakeExecuteSession:
    def __init__(self, row):
        self.row = row

    async def execute(self, stmt):
        return _ExecuteResult(self.row)


def test_spatial_window_is_bounded_to_platform_limit() -> None:
    service = SpatialService()
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=settings.spatial_max_history_hours + 24)

    window = service.normalize_window(starts_at=start, ends_at=end)

    assert (window.ends_at - window.starts_at) == timedelta(hours=settings.spatial_max_history_hours)


def test_geofence_transition_builder_detects_enter_and_exit() -> None:
    service = GeofenceService()
    entering = uuid4()
    staying = uuid4()
    leaving = uuid4()

    enters, exits = service.build_transition_actions(
        previous_inside={staying, leaving},
        current_inside={staying, entering},
    )

    assert enters == {entering}
    assert exits == {leaving}


def test_geofence_alerts_are_rate_limited() -> None:
    service = GeofenceService()
    now = datetime.now(timezone.utc)
    session = FakeExecuteSession(
        SimpleNamespace(triggered_at=now - timedelta(seconds=settings.geofence_alert_cooldown_seconds - 10))
    )

    should_emit = service.should_emit_alert(
        session,
        geofence_id=uuid4(),
        device_id=uuid4(),
        now=now,
    )

    import asyncio

    assert asyncio.run(should_emit) is False


def test_location_history_route_and_cluster_endpoints_return_spatial_payloads() -> None:
    fake_spatial = FakeSpatialEndpointService()
    org_id = str(fake_spatial.org_id)
    from app.db.base import get_db_session

    app.dependency_overrides[get_current_principal] = _override_principal(org_id)
    app.dependency_overrides[get_spatial_service] = lambda: fake_spatial
    app.dependency_overrides[get_db_session] = _dummy_db_session
    try:
        client = TestClient(app)
        history = client.get(f'/api/v1/platform/devices/{fake_spatial.device_id}/location-history?org_id={org_id}')
        route = client.get(f'/api/v1/platform/cases/{fake_spatial.incident_id}/route?org_id={org_id}')
        clusters = client.get(f'/api/v1/platform/devices/clusters?org_id={org_id}')
    finally:
        app.dependency_overrides.clear()

    assert history.status_code == 200
    assert len(history.json()) == 2
    assert route.status_code == 200
    assert route.json()['geofence_events'][0]['geofence_name'] == 'Arusha Depot'
    assert clusters.status_code == 200
    assert clusters.json()[0]['device_count'] == 2


def test_geofence_crud_endpoints_append_audit_entries() -> None:
    fake_geofence = FakeGeofenceService()
    fake_audit = FakeAuditLogService()
    org_id = str(uuid4())
    from app.db.base import get_db_session

    app.dependency_overrides[get_current_principal] = _override_principal(org_id)
    app.dependency_overrides[get_geofence_service] = lambda: fake_geofence
    app.dependency_overrides[get_audit_log_service] = lambda: fake_audit
    app.dependency_overrides[get_db_session] = _dummy_db_session
    try:
        client = TestClient(app)
        create = client.post(
            '/api/v1/platform/geofences',
            json={
                'org_id': org_id,
                'device_id': str(fake_geofence.device_id),
                'name': 'Dar HQ',
                'radius_meters': 300,
                'center_latitude': -6.7924,
                'center_longitude': 39.2083,
            },
        )
        update = client.put(
            f'/api/v1/platform/geofences/{fake_geofence.geofence_id}',
            json={
                'org_id': org_id,
                'device_id': str(fake_geofence.device_id),
                'name': 'Dar HQ Updated',
                'radius_meters': 350,
                'center_latitude': -6.7924,
                'center_longitude': 39.2083,
                'is_enabled': True,
            },
        )
        delete = client.delete(
            f'/api/v1/platform/geofences/{fake_geofence.geofence_id}?org_id={org_id}&reason=policy cleanup',
        )
    finally:
        app.dependency_overrides.clear()

    assert create.status_code == 200
    assert update.status_code == 200
    assert delete.status_code == 204
    assert fake_audit.actions == ['GEOFENCE_CREATED', 'GEOFENCE_UPDATED', 'GEOFENCE_DELETED']
