from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_audit_log_service, get_location_ingestion_service
from app.core.security import Principal, Role, get_current_principal
from app.main import app
from app.db.base import get_db_session


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


class FakeLocationIngestionService:
    def __init__(self) -> None:
        self.seen: set[str] = set()

    async def ingest(self, session, payload):
        duplicate = payload.idempotency_key in self.seen
        self.seen.add(payload.idempotency_key)
        return SimpleNamespace(
            event=SimpleNamespace(
                id=uuid4(),
                is_ip_approximate=payload.precision.value == 'approximate',
                telemetry_verified=True,
            ),
            duplicate=duplicate,
            rule_matches=['RECENT_LOCATION'],
            suspicious_alerts=['STALE_CAPTURE_TIMESTAMP'] if duplicate else [],
            telemetry_digest_matches=True,
            integrity_status='trusted',
        )


def _principal(org_id: str):
    return lambda: Principal(subject='owner@example.com', roles={Role.OWNER}, organization_id=org_id)


def _build_item(org_id: str, device_id: str, key: str) -> dict:
    return {
        'org_id': org_id,
        'device_id': device_id,
        'mode': 'normal',
        'idempotency_key': key,
        'captured_at': datetime.now(timezone.utc).isoformat(),
        'latitude': -6.7924,
        'longitude': 39.2083,
        'accuracy_meters': 18.0,
        'precision': 'moderate',
        'confidence_score': 74,
        'source_methods': ['fused_last_known'],
        'network_type': 'wifi',
        'battery_percent': 83,
        'motion_state': 'still',
        'telemetry_signature': 'abc123',
        'telemetry_key_id': 'device-key-1',
        'telemetry_payload_hash': 'a' * 64,
        'integrity_verdict': 'trusted',
    }


def test_batch_ingest_handles_duplicates_with_idempotency_counts():
    org_id = str(uuid4())
    device_id = str(uuid4())
    fake_service = FakeLocationIngestionService()
    fake_audit = FakeAuditLogService()

    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_current_principal] = _principal(org_id)
    app.dependency_overrides[get_location_ingestion_service] = lambda: fake_service
    app.dependency_overrides[get_audit_log_service] = lambda: fake_audit

    client = TestClient(app)
    response = client.post(
        '/api/v1/platform/locations/ingest-batch',
        json={
            'items': [
                _build_item(org_id, device_id, 'loc-key-1'),
                _build_item(org_id, device_id, 'loc-key-1'),
                _build_item(org_id, device_id, 'loc-key-2'),
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['accepted_count'] == 2
    assert payload['duplicate_count'] == 1
    assert payload['failed_count'] == 0
    assert [item['duplicate'] for item in payload['results']] == [False, True, False]
    assert fake_audit.actions == ['LOCATION_INGESTED', 'LOCATION_INGESTED', 'LOCATION_INGESTED']

    app.dependency_overrides.clear()


def test_batch_ingest_accepts_gzipped_json_payload():
    org_id = str(uuid4())
    device_id = str(uuid4())

    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_current_principal] = _principal(org_id)
    app.dependency_overrides[get_location_ingestion_service] = lambda: FakeLocationIngestionService()
    app.dependency_overrides[get_audit_log_service] = lambda: FakeAuditLogService()

    client = TestClient(app)
    raw_body = json.dumps(
        {'items': [_build_item(org_id, device_id, 'loc-key-gzip')]},
        separators=(',', ':'),
    ).encode('utf-8')
    response = client.post(
        '/api/v1/platform/locations/ingest-batch',
        content=gzip.compress(raw_body),
        headers={'Content-Encoding': 'gzip', 'Content-Type': 'application/json'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['accepted_count'] == 1
    assert payload['duplicate_count'] == 0

    app.dependency_overrides.clear()
