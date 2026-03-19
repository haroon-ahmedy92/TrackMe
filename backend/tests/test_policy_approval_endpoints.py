from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import (
    get_approval_workflow_service,
    get_audit_log_service,
    get_authorization_policy_service,
    get_case_management_service,
    get_case_evidence_service,
    get_remote_action_service,
)
from app.core.security import Principal, Role, get_current_principal
from app.db.base import get_db_session
from app.db.models import ApprovalDecisionType, ApprovalStatus, EvidenceExportFormat, IncidentCaseState, PolicyActionType, RemoteActionKind, RemoteActionState
from app.main import app
from app.services.approval_workflow_service import ApprovalWorkflowService
from app.services.authorization_policy_service import AuthorizationPolicyService, PolicyDecision


class DummySession:
    def __init__(self) -> None:
        self.added: list[object] = []

    async def commit(self):
        return None

    async def flush(self):
        return None

    async def refresh(self, _obj):
        return None

    def add(self, obj):
        self.added.append(obj)


async def _dummy_db_session():
    yield DummySession()


def _principal(subject: str, roles: list[Role], org_id: str):
    return lambda: Principal(subject=subject, roles=set(roles), organization_id=org_id)


class FakeAuditLogService:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def append(self, session, *, action: str, **kwargs):
        self.actions.append(action)
        return None


class AllowingWipePolicyService:
    async def evaluate_remote_action(self, session, *, payload, principal):
        return PolicyDecision(
            action_type=PolicyActionType.WIPE,
            allowed=True,
            requires_approval=True,
            reason_code='wipe_requires_approval',
            reason='Wipe is valid but requires two-person approval.',
            required_approvals=2,
            owner_subject='owner@example.com',
            incident_state=IncidentCaseState.CONFIRMED_STOLEN,
        )


class DenyingExportPolicyService:
    async def evaluate_evidence_export(self, session, *, incident, principal, payload):
        return PolicyDecision(
            action_type=PolicyActionType.EVIDENCE_EXPORT,
            allowed=False,
            requires_approval=False,
            reason_code='export_not_permitted',
            reason='Evidence export is not permitted for this role.',
            owner_subject='owner@example.com',
            incident_state=incident.state,
        )


class DenyingRetentionPolicyService:
    async def evaluate_retention_update(self, session, *, principal, payload):
        return PolicyDecision(
            action_type=PolicyActionType.RETENTION_UPDATE,
            allowed=False,
            requires_approval=False,
            reason_code='role_not_allowed',
            reason='Only admin-level roles can update tenant retention and access rules.',
        )


class FakeRemoteActionService:
    async def request_action(self, session, payload, *, requested_by_sub, initial_state=RemoteActionState.PENDING):
        return SimpleNamespace(
            id=uuid4(),
            org_id=payload.org_id,
            device_id=payload.device_id,
            incident_id=payload.incident_id,
            action_kind=payload.action_kind,
            state=initial_state,
            delayed_until=payload.delayed_until,
            requested_at=datetime.now(timezone.utc),
        )


class FakeApprovalWorkflowService:
    def __init__(self) -> None:
        self.created_requests: list[tuple[str, str]] = []

    async def create_request(self, session, *, org_id, action_type, entity_type, entity_id, requested_by_sub, request_reason, required_approvals, policy_decision, requested_payload, device_id=None, incident_id=None):
        approval = SimpleNamespace(
            id=uuid4(),
            org_id=org_id,
            action_type=action_type,
            status=ApprovalStatus.PENDING,
            entity_type=entity_type,
            entity_id=entity_id,
            device_id=device_id,
            incident_id=incident_id,
            requested_by_sub=requested_by_sub,
            request_reason=request_reason,
            required_approvals=required_approvals,
            policy_context_json={'reason': policy_decision.reason},
            decisions=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            approved_at=None,
            rejected_at=None,
        )
        self.created_requests.append((entity_type, entity_id))
        return approval


class FakeCaseManagementService:
    def __init__(self, org_id):
        self.org_id = org_id
        self.device_id = uuid4()

    async def get_case(self, session, incident_id):
        return SimpleNamespace(
            id=incident_id,
            org_id=self.org_id,
            device_id=self.device_id,
            ticket_reference='CASE-222',
            state=IncidentCaseState.CONFIRMED_STOLEN,
            recovery_message='Return to office',
            lost_mode_until=None,
            wipe_scheduled_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


class FakeCaseEvidenceService:
    def __init__(self) -> None:
        self.called = False

    async def create_export(self, *args, **kwargs):
        self.called = True
        return SimpleNamespace(
            id=uuid4(),
            org_id=kwargs['incident'].org_id,
            incident_id=kwargs['incident'].id,
            requested_by_sub=kwargs['actor_sub'],
            format=EvidenceExportFormat.JSON,
            status='generated',
            reason=kwargs['payload'].reason,
            redact_fields_json={'fields': kwargs['payload'].redact_fields},
            summary_json={'placeholder': True},
            created_at=datetime.now(timezone.utc),
            generated_at=datetime.now(timezone.utc),
        )


def test_remote_wipe_request_enters_pending_approval_flow() -> None:
    org_id = str(uuid4())
    audit = FakeAuditLogService()
    approvals = FakeApprovalWorkflowService()

    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_current_principal] = _principal('admin@example.com', [Role.ADMIN], org_id)
    app.dependency_overrides[get_audit_log_service] = lambda: audit
    app.dependency_overrides[get_authorization_policy_service] = lambda: AllowingWipePolicyService()
    app.dependency_overrides[get_approval_workflow_service] = lambda: approvals
    app.dependency_overrides[get_remote_action_service] = lambda: FakeRemoteActionService()
    try:
        client = TestClient(app)
        response = client.post(
            '/api/v1/platform/remote-actions',
            json={
                'org_id': org_id,
                'device_id': str(uuid4()),
                'incident_id': str(uuid4()),
                'action_kind': 'wipe',
                'reason': 'Confirmed stolen device with regulated data exposure risk.',
                'elevated_confirmation': True,
                'acknowledge_wipe_tradeoff': True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload['state'] == 'pending_approval'
    assert payload['approval_request_id'] is not None
    assert 'POLICY_WIPE_ALLOWED' in audit.actions
    assert 'REMOTE_WIPE_REQUESTED' in audit.actions


def test_export_endpoint_denies_when_policy_rejects() -> None:
    org_uuid = uuid4()
    org_id = str(org_uuid)
    audit = FakeAuditLogService()
    case_service = FakeCaseManagementService(org_uuid)
    evidence_service = FakeCaseEvidenceService()

    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_current_principal] = _principal('security@example.com', [Role.SECURITY], org_id)
    app.dependency_overrides[get_audit_log_service] = lambda: audit
    app.dependency_overrides[get_authorization_policy_service] = lambda: DenyingExportPolicyService()
    app.dependency_overrides[get_case_management_service] = lambda: case_service
    app.dependency_overrides[get_case_evidence_service] = lambda: evidence_service
    try:
        client = TestClient(app)
        response = client.post(
            f'/api/v1/platform/cases/{uuid4()}/exports',
            json={
                'org_id': str(case_service.org_id),
                'format': 'json',
                'reason': 'Need full export',
                'redact_fields': [],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert evidence_service.called is False
    assert 'POLICY_EVIDENCE_EXPORT_DENIED' in audit.actions


def test_retention_update_denied_when_policy_engine_blocks() -> None:
    org_id = str(uuid4())
    audit = FakeAuditLogService()

    class FakeComplianceService:
        async def update_retention_policy(self, session, *, payload, actor_sub):  # pragma: no cover
            raise AssertionError('Should not be called when policy denies')

    from app.api.deps import get_compliance_service

    app.dependency_overrides[get_db_session] = _dummy_db_session
    app.dependency_overrides[get_current_principal] = _principal('admin@example.com', [Role.ADMIN], org_id)
    app.dependency_overrides[get_audit_log_service] = lambda: audit
    app.dependency_overrides[get_authorization_policy_service] = lambda: DenyingRetentionPolicyService()
    app.dependency_overrides[get_compliance_service] = lambda: FakeComplianceService()
    try:
        client = TestClient(app)
        response = client.put(
            '/api/v1/platform/settings/retention-policy',
            json={
                'org_id': org_id,
                'location_event_days': 21,
                'audit_log_days': 120,
                'incident_evidence_days': 45,
                'reason': 'Owner trying to change tenant policy',
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert 'POLICY_RETENTION_UPDATE_DENIED' in audit.actions


def test_approval_workflow_requires_distinct_approvers() -> None:
    now = datetime.now(timezone.utc)
    approval = SimpleNamespace(
        id=uuid4(),
        org_id=uuid4(),
        action_type=PolicyActionType.WIPE,
        status=ApprovalStatus.PENDING,
        entity_type='remote_action',
        entity_id=str(uuid4()),
        device_id=uuid4(),
        incident_id=uuid4(),
        requested_by_sub='requester@example.com',
        request_reason='Wipe requested after confirmed theft.',
        required_approvals=2,
        policy_context_json={},
        requested_payload_json={},
        decisions=[
                SimpleNamespace(
                    id=uuid4(),
                    actor_sub='approver1@example.com',
                    decision=ApprovalDecisionType.APPROVE,
                    reason='Validated against policy',
                    created_at=now,
                )
        ],
        created_at=now,
        updated_at=now,
        approved_at=None,
        rejected_at=None,
    )

    class StubApprovalService(ApprovalWorkflowService):
        async def get_approval(self, session, approval_id):
            return approval

    service = StubApprovalService()
    session = DummySession()

    try:
        import asyncio

        asyncio.run(
            service.record_decision(
                session,
                approval_id=approval.id,
                actor_sub='requester@example.com',
                approve=True,
                reason='Self approval attempt',
            )
        )
        assert False, 'Expected requester self-approval to fail'
    except ValueError as exc:
        assert 'cannot approve' in str(exc)

    import asyncio

    resolution = asyncio.run(
        service.record_decision(
            session,
            approval_id=approval.id,
            actor_sub='approver2@example.com',
            approve=True,
            reason='Second reviewer confirmed wipe conditions.',
        )
    )
    assert resolution.completed is True
    assert resolution.approval.status == ApprovalStatus.APPROVED
