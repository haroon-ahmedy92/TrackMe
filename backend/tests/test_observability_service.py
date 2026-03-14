from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import RemoteActionState
from app.services.observability_service import ObservabilityService, security_signal_store


class FakeObservabilityService(ObservabilityService):
    def __init__(self, *, audit_logs, remote_actions, location_events) -> None:
        self._audit_rows = audit_logs
        self._remote_rows = remote_actions
        self._location_rows = location_events

    async def _audit_logs(self, session, *, org_id, since):
        return self._audit_rows

    async def _remote_actions(self, session, *, org_id, since):
        return self._remote_rows

    async def _location_events(self, session, *, org_id, since):
        return self._location_rows


def test_detect_alerts_flags_bulk_lookup_and_failed_auth() -> None:
    org_id = uuid4()
    actor = 'analyst@example.com'
    now = datetime.now(timezone.utc)
    security_signal_store.clear()
    audit_logs = [
        SimpleNamespace(
            id=uuid4(),
            org_id=org_id,
            actor_sub=actor,
            action='LOCATION_LOOKUP_REQUESTED',
            entity_type='device',
            entity_id=str(uuid4()),
            metadata_json={'reason': 'Case lookup'},
            occurred_at=now,
        )
        for _ in range(12)
    ] + [
        SimpleNamespace(
            id=uuid4(),
            org_id=org_id,
            actor_sub=actor,
            action='LOCATION_LOOKUP_DENIED',
            entity_type='device',
            entity_id=str(uuid4()),
            metadata_json={'reason': 'Denied'},
            occurred_at=now,
        )
        for _ in range(5)
    ]
    service = FakeObservabilityService(audit_logs=audit_logs, remote_actions=[], location_events=[])
    for _ in range(6):
        security_signal_store.record_auth_failure(
            path='/api/v1/platform/devices',
            ip_address='127.0.0.1',
            actor_hint=None,
            org_id=str(org_id),
            reason='invalid_token',
            request_id='req-1',
        )

    alerts = __import__('asyncio').run(service.detect_alerts(None, org_id=org_id, window_hours=24))

    codes = {alert['code'] for alert in alerts}
    assert 'bulk_location_lookup' in codes
    assert 'repeated_failed_authorization' in codes


def test_build_dashboard_summarizes_health_and_battery() -> None:
    org_id = uuid4()
    now = datetime.now(timezone.utc)
    location_events = [
        SimpleNamespace(
            received_at=now - timedelta(minutes=5),
            is_ip_approximate=False,
            telemetry_verified=True,
            confidence_score=91,
            precision=SimpleNamespace(value='precise'),
            battery_percent=72,
        ),
        SimpleNamespace(
            received_at=now - timedelta(minutes=2),
            is_ip_approximate=True,
            telemetry_verified=False,
            confidence_score=42,
            precision=SimpleNamespace(value='approximate'),
            battery_percent=12,
        ),
    ]
    remote_actions = [
        SimpleNamespace(state=RemoteActionState.FAILED, last_error='device_offline'),
        SimpleNamespace(state=RemoteActionState.EXPIRED, last_error='expired'),
    ]
    service = FakeObservabilityService(
        audit_logs=[],
        remote_actions=remote_actions,
        location_events=location_events,
    )

    dashboard = __import__('asyncio').run(service.build_dashboard(None, org_id=org_id, window_hours=24))

    assert dashboard['ingestion_health']['location_events'] == 2
    assert dashboard['battery_impact']['low_battery_samples'] == 1
    assert dashboard['location_confidence_distribution']['precision_distribution']['precise'] == 1
    assert dashboard['location_confidence_distribution']['precision_distribution']['approximate'] == 1


def test_export_audit_report_writes_file(tmp_path) -> None:
    service = ObservabilityService()
    report = {
        'org_id': str(uuid4()),
        'window_hours': 24,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'entries': [{'audit_id': 'a1'}],
    }
    from app.core.config import settings

    settings.exports_storage_dir = str(tmp_path)
    path = service.export_audit_report(org_id=uuid4(), report=report)
    assert path.exists()
    assert path.read_text(encoding='utf-8').startswith('{')
