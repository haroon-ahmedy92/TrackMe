from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_audit_log_service, get_case_evidence_service, get_case_management_service, get_spatial_service
from app.core.config import settings
from app.core.security import Principal, Role, get_current_principal
from app.db.models import EvidenceExportStatus
from app.main import app
from app.services.case_evidence_service import CaseEvidenceService
from app.services.evidence_export_bundle_service import EvidenceExportBundleService


class DummySession:
    async def commit(self):
        return None


async def _dummy_db_session():
    yield DummySession()


def _override_principal(subject: str, roles: list[Role], org_id: str):
    return lambda: Principal(subject=subject, roles=set(roles), organization_id=org_id)


class FakeAuditLogService:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def append(self, session, *, action: str, **kwargs):
        self.actions.append(action)
        return None


class FakeCaseManagementService:
    def __init__(self) -> None:
        self.org_id = uuid4()
        self.device_id = uuid4()
        self.incident_id = uuid4()

    async def get_case(self, session, incident_id):
        return SimpleNamespace(
            id=incident_id,
            org_id=self.org_id,
            device_id=self.device_id,
            ticket_reference='CASE-102',
            state=SimpleNamespace(value='suspected_lost'),
            recovery_message='Please return to operations desk',
            lost_mode_until=None,
            wipe_scheduled_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


class FakeCaseEvidenceService:
    def __init__(self) -> None:
        self.org_id = uuid4()

    async def list_cases(self, session, *, org_id):
        return [
            SimpleNamespace(
                id=uuid4(),
                org_id=org_id,
                device_id=uuid4(),
                ticket_reference='CASE-102',
                state=SimpleNamespace(value='suspected_lost'),
                recovery_message='Please return to desk',
                lost_mode_until=None,
                wipe_scheduled_at=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]

    async def list_notes(self, session, *, incident_id):
        now = datetime.now(timezone.utc)
        return [
            SimpleNamespace(
                id=uuid4(),
                incident_id=incident_id,
                author_sub='analyst@example.com',
                body='Initial investigation note',
                is_pinned=True,
                created_at=now,
                updated_at=now,
            )
        ]

    async def create_note(self, session, *, incident, payload, actor_sub):
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=uuid4(),
            incident_id=incident.id,
            author_sub=actor_sub,
            body=payload.body,
            is_pinned=payload.is_pinned,
            created_at=now,
            updated_at=now,
        )

    async def update_note(self, session, *, incident, note_id, payload):
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=note_id,
            incident_id=incident.id,
            author_sub='analyst@example.com',
            body=payload.body,
            is_pinned=payload.is_pinned,
            created_at=now,
            updated_at=now,
        )

    async def list_attachments(self, session, *, incident_id):
        return [
            SimpleNamespace(
                id=uuid4(),
                incident_id=incident_id,
                uploaded_by_sub='admin@example.com',
                file_name='handover-form.pdf',
                media_type='application/pdf',
                byte_size=1204,
                sha256='abc123',
                description='Signed handover form',
                storage_key='placeholder://incident/file',
                created_at=datetime.now(timezone.utc),
            )
        ]

    async def create_attachment(self, session, *, incident, payload, actor_sub):
        return SimpleNamespace(
            id=uuid4(),
            incident_id=incident.id,
            uploaded_by_sub=actor_sub,
            file_name=payload.file_name,
            media_type=payload.media_type,
            byte_size=payload.byte_size,
            sha256=payload.sha256,
            description=payload.description,
            storage_key=payload.storage_key or 'placeholder://incident/file',
            created_at=datetime.now(timezone.utc),
        )

    async def list_exports(self, session, *, incident_id):
        return [
            SimpleNamespace(
                id=uuid4(),
                org_id=self.org_id,
                incident_id=incident_id,
                requested_by_sub='auditor@example.com',
                format=SimpleNamespace(value='json'),
                status=EvidenceExportStatus.GENERATED,
                reason='Case handoff',
                redact_fields_json={'fields': ['latitude', 'longitude']},
                summary_json={'placeholder': True},
                created_at=datetime.now(timezone.utc),
                generated_at=datetime.now(timezone.utc),
            )
        ]

    async def create_export(self, session, *, incident, payload, actor_sub, spatial_service, bundle_service):
        return SimpleNamespace(
            id=uuid4(),
            org_id=incident.org_id,
            incident_id=incident.id,
            requested_by_sub=actor_sub,
            format=payload.format,
            status=EvidenceExportStatus.GENERATED,
            reason=payload.reason,
            redact_fields_json={'fields': payload.redact_fields},
            summary_json={'placeholder': True, 'format': payload.format.value},
            created_at=datetime.now(timezone.utc),
            generated_at=datetime.now(timezone.utc),
        )

    async def build_chain(self, session, *, incident, redact_fields, spatial_service):
        now = datetime.now(timezone.utc).isoformat()
        return {
            'incident': {
                'incident_id': str(incident.id),
                'org_id': str(incident.org_id),
                'device_id': str(incident.device_id),
                'ticket_reference': 'CASE-102',
                'state': 'suspected_lost',
                'recovery_message': 'Please return to operations desk',
                'lost_mode_until': None,
                'wipe_scheduled_at': None,
                'created_at': now,
                'updated_at': now,
            },
            'actions_taken': [
                {
                    'remote_action_id': str(uuid4()),
                    'action_kind': 'lock',
                    'state': 'pending',
                    'reason': 'Protect data',
                    'requested_by_sub': 'admin@example.com',
                    'requested_at': now,
                    'sent_at': None,
                    'delivered_at': None,
                    'acked_at': None,
                    'failed_at': None,
                    'last_error': None,
                }
            ],
            'notes': [
                {
                    'note_id': str(uuid4()),
                    'incident_id': str(incident.id),
                    'author_sub': 'analyst@example.com',
                    'body': 'Device last seen near depot',
                    'is_pinned': True,
                    'created_at': now,
                    'updated_at': now,
                }
            ],
            'attachments': [
                {
                    'attachment_id': str(uuid4()),
                    'incident_id': str(incident.id),
                    'uploaded_by_sub': 'admin@example.com',
                    'file_name': 'handover-form.pdf',
                    'media_type': 'application/pdf',
                    'byte_size': 1024,
                    'sha256': 'abc123',
                    'description': 'Signed handover form',
                    'storage_key': 'placeholder://incident/file',
                    'created_at': now,
                }
            ],
            'exports': [
                {
                    'export_id': str(uuid4()),
                    'incident_id': str(incident.id),
                    'requested_by_sub': 'auditor@example.com',
                    'format': 'json',
                    'status': 'generated',
                    'reason': 'Case handoff',
                    'redact_fields': ['latitude', 'longitude'],
                    'summary': {'placeholder': True},
                    'download_placeholder': 'placeholder://exports/test.json',
                    'created_at': now,
                    'generated_at': now,
                }
            ],
            'entries': [
                {
                    'entry_id': 'entry-1',
                    'kind': 'location',
                    'title': 'Location sample',
                    'summary': 'Approximate area-level signal',
                    'occurred_at': now,
                    'actor_sub': None,
                    'mutable': False,
                    'data': {'latitude': '[REDACTED]' if 'latitude' in redact_fields else -6.8},
                }
            ],
        }


class FakeSpatialService:
    pass


def test_case_evidence_service_redacts_sensitive_fields() -> None:
    service = CaseEvidenceService()
    payload = {
        'ticket_reference': 'CASE-102',
        'latitude': -6.8,
        'nested': {'longitude': 39.2, 'detail': 'ok'},
    }

    result = service.apply_redactions(payload, ['latitude', 'longitude'])

    assert result['ticket_reference'] == 'CASE-102'
    assert result['latitude'] == '[REDACTED]'
    assert result['nested']['longitude'] == '[REDACTED]'


def test_case_evidence_endpoints_return_chain_notes_and_exports() -> None:
    fake_case_service = FakeCaseManagementService()
    fake_evidence_service = FakeCaseEvidenceService()
    fake_audit = FakeAuditLogService()
    org_id = str(fake_case_service.org_id)
    from app.db.base import get_db_session

    app.dependency_overrides[get_current_principal] = _override_principal('admin@example.com', [Role.ADMIN], org_id)
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_case_management_service] = lambda: fake_case_service
    app.dependency_overrides[get_case_evidence_service] = lambda: fake_evidence_service
    app.dependency_overrides[get_spatial_service] = lambda: FakeSpatialService()
    app.dependency_overrides[get_audit_log_service] = lambda: fake_audit
    try:
        client = TestClient(app)
        chain_response = client.get(
            f'/api/v1/platform/cases/{fake_case_service.incident_id}/evidence-chain',
            params={'org_id': org_id, 'redact_fields': ['latitude']},
        )
        note_response = client.post(
            f'/api/v1/platform/cases/{fake_case_service.incident_id}/notes',
            json={'org_id': org_id, 'body': 'Supervisor contacted', 'is_pinned': True},
        )
        attachment_response = client.post(
            f'/api/v1/platform/cases/{fake_case_service.incident_id}/attachments',
            json={
                'org_id': org_id,
                'file_name': 'handover-form.pdf',
                'media_type': 'application/pdf',
                'byte_size': 1024,
                'sha256': 'abcdef1234567890abcdef1234567890',
                'description': 'Signed handover form',
            },
        )
        export_response = client.post(
            f'/api/v1/platform/cases/{fake_case_service.incident_id}/exports',
            json={'org_id': org_id, 'format': 'json', 'reason': 'Case handoff', 'redact_fields': ['latitude']},
        )
    finally:
        app.dependency_overrides.clear()

    assert chain_response.status_code == 200
    assert chain_response.json()['entries'][0]['data']['latitude'] == '[REDACTED]'
    assert note_response.status_code == 200
    assert attachment_response.status_code == 200
    assert export_response.status_code == 200
    assert 'CASE_NOTE_CREATED' in fake_audit.actions
    assert 'CASE_ATTACHMENT_ADDED' in fake_audit.actions
    assert 'CASE_EVIDENCE_EXPORT_CREATED' in fake_audit.actions


def test_case_export_download_returns_zip_bundle(tmp_path) -> None:
    fake_case_service = FakeCaseManagementService()
    fake_evidence_service = FakeCaseEvidenceService()
    fake_audit = FakeAuditLogService()
    bundle_service = EvidenceExportBundleService()
    org_id = str(fake_case_service.org_id)
    from app.db.base import get_db_session

    settings.exports_storage_dir = str(tmp_path)
    export_id = uuid4()
    now = datetime.now(timezone.utc)
    export_record = SimpleNamespace(
        id=export_id,
        org_id=fake_case_service.org_id,
        incident_id=fake_case_service.incident_id,
        requested_by_sub='auditor@example.com',
        format=SimpleNamespace(value='json'),
        status=EvidenceExportStatus.GENERATED,
        reason='Case handoff',
        redact_fields_json={'fields': ['latitude']},
        summary_json={'placeholder': False},
        created_at=now,
        generated_at=now,
    )
    bundle_service.ensure_bundle(
        export_record=export_record,
        chain={
            'incident': {'incident_id': str(fake_case_service.incident_id), 'ticket_reference': 'CASE-102', 'state': 'suspected_lost'},
            'actions_taken': [],
            'notes': [],
            'attachments': [],
            'entries': [{'title': 'Location sample', 'summary': 'Approximate area-level signal'}],
            'exports': [],
        },
    )

    async def _list_exports(session, *, incident_id):
        return [export_record]

    fake_evidence_service.list_exports = _list_exports  # type: ignore[method-assign]

    app.dependency_overrides[get_current_principal] = _override_principal('admin@example.com', [Role.ADMIN], org_id)
    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_case_management_service] = lambda: fake_case_service
    app.dependency_overrides[get_case_evidence_service] = lambda: fake_evidence_service
    app.dependency_overrides[get_audit_log_service] = lambda: fake_audit
    try:
        client = TestClient(app)
        response = client.get(
            f'/api/v1/platform/cases/{fake_case_service.incident_id}/exports/{export_id}/download',
            params={'org_id': org_id},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/zip'
    assert 'CASE_EVIDENCE_EXPORT_DOWNLOADED' in fake_audit.actions


def test_pdf_bundle_generation_writes_pdf_file(tmp_path) -> None:
    settings.exports_storage_dir = str(tmp_path)
    bundle_service = EvidenceExportBundleService()
    now = datetime.now(timezone.utc)
    export_record = SimpleNamespace(
        id=uuid4(),
        org_id=uuid4(),
        incident_id=uuid4(),
        requested_by_sub='auditor@example.com',
        format=SimpleNamespace(value='pdf'),
        status=EvidenceExportStatus.GENERATED,
        reason='Case handoff',
        redact_fields_json={'fields': []},
        summary_json={},
        created_at=now,
        generated_at=now,
    )

    bundle = bundle_service.ensure_bundle(
        export_record=export_record,
        chain={
            'incident': {'incident_id': 'inc-1', 'ticket_reference': 'CASE-500', 'state': 'confirmed_stolen'},
            'actions_taken': [],
            'notes': [],
            'attachments': [],
            'entries': [{'title': 'Remote lock', 'summary': 'ACKED command'}],
            'exports': [],
        },
    )

    assert bundle.summary_path.suffix == '.pdf'
    assert bundle.summary_path.read_bytes().startswith(b'%PDF-')
    assert bundle.bundle_path.exists()
