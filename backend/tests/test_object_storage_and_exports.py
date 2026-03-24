from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import EvidenceExportStatus
from app.services.evidence_export_bundle_service import EvidenceExportBundleService
from app.services.object_storage_service import LocalObjectStorageService


@pytest.mark.asyncio
async def test_local_object_storage_round_trip(tmp_path) -> None:
    storage = LocalObjectStorageService(str(tmp_path))

    stored = await storage.store_bytes(
        org_id=str(uuid4()),
        incident_id=str(uuid4()),
        file_name='handover-form.pdf',
        media_type='application/pdf',
        payload=b'pdf-content',
    )

    assert stored.storage_backend == 'local'
    assert storage.resolve_local_path(stored.storage_key) is not None
    assert await storage.read_bytes(stored.storage_key) == b'pdf-content'


@pytest.mark.asyncio
async def test_evidence_export_bundle_is_persisted_via_object_storage(tmp_path) -> None:
    storage = LocalObjectStorageService(str(tmp_path))
    bundle_service = EvidenceExportBundleService(object_storage_service=storage)
    now = datetime.now(timezone.utc)
    export_record = SimpleNamespace(
        id=uuid4(),
        org_id=uuid4(),
        incident_id=uuid4(),
        requested_by_sub='auditor@example.com',
        format=SimpleNamespace(value='csv'),
        status=EvidenceExportStatus.GENERATED,
        reason='Operator handoff',
        redact_fields_json={'fields': ['latitude']},
        summary_json={},
        created_at=now,
        generated_at=now,
    )

    bundle = await bundle_service.ensure_bundle(
        export_record=export_record,
        chain={
            'incident_summary': {'incident_id': 'inc-1', 'ticket_reference': 'CASE-500', 'state': 'confirmed_stolen'},
            'incident': {'incident_id': 'inc-1', 'ticket_reference': 'CASE-500', 'state': 'confirmed_stolen'},
            'location_timeline': [{'event_id': 'loc-1', 'precision': 'approximate', 'approximate_label': 'Approximate source only'}],
            'audit_trail': [{'action': 'CASE_EVIDENCE_EXPORT_CREATED'}],
            'command_history': [{'remote_action_id': 'cmd-1', 'action_kind': 'lock'}],
            'geofence_events': [{'geofence_event_id': 'geo-1', 'event_type': 'exit'}],
            'actions_taken': [{'remote_action_id': 'cmd-1', 'action_kind': 'lock'}],
            'notes': [{'note_id': 'note-1', 'body': 'Analyst note'}],
            'attachments': [{'attachment_id': 'att-1', 'file_name': 'handover.pdf'}],
            'external_shares': [],
            'entries': [{'title': 'Remote lock', 'summary': 'ACKED command'}],
            'exports': [],
        },
    )

    assert bundle.bundle_storage_backend == 'local'
    assert bundle.bundle_local_path is not None
    assert bundle.bundle_local_path.exists()
    assert bundle.bundle_file_name.endswith('.zip')
