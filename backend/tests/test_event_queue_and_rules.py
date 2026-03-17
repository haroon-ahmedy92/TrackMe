from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.events import EventTopic, PlatformEventEnvelope
from app.services.event_consumer_worker import BaseEventConsumer, ConsumerResult, EventConsumerWorker
from app.services.event_queue_service import InMemoryEventQueueService
from app.services.rule_action_executor import RuleActionExecutor
from app.services.rules_engine_service import RuleActionRequest, RuleMatch, RulesEngineService


@pytest.mark.asyncio
async def test_in_memory_event_queue_is_idempotent_and_replay_safe() -> None:
    queue = InMemoryEventQueueService()
    envelope = PlatformEventEnvelope(
        topic=EventTopic.LOCATION_UPDATED,
        org_id=uuid4(),
        entity_type='location_event',
        entity_id=str(uuid4()),
        producer='test',
        occurred_at=datetime.now(timezone.utc),
        idempotency_key='location-event:1',
        payload={'device_id': str(uuid4())},
    )

    first = await queue.publish(None, envelope)
    second = await queue.publish(None, envelope)
    claimed = await queue.claim_next(None, worker_name='worker-a')

    assert first.created is True
    assert second.created is False
    assert claimed is not None

    await queue.mark_completed(None, record=claimed)

    assert await queue.claim_next(None, worker_name='worker-a') is None


def test_rules_engine_matches_geofence_exit_during_lost_mode() -> None:
    service = RulesEngineService()
    envelope = PlatformEventEnvelope(
        topic=EventTopic.GEOFENCE_TRANSITION,
        org_id=uuid4(),
        entity_type='geofence_event',
        entity_id=str(uuid4()),
        producer='test',
        occurred_at=datetime.now(timezone.utc),
        idempotency_key='geofence-event:1',
        payload={
            'device_id': str(uuid4()),
            'geofence_id': str(uuid4()),
            'event_type': 'exit',
            'alert_emitted': True,
            'active_incident': {
                'incident_id': str(uuid4()),
                'state': 'confirmed_stolen',
                'lost_mode_until': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            },
        },
    )

    result = service.evaluate_event(envelope)

    assert [match.rule_code for match in result.matches] == ['geofence_exit_during_lost_mode']
    assert result.matches[0].actions[0].action_type == 'notify_internal'


def test_rules_engine_matches_stale_incident_offline_check() -> None:
    service = RulesEngineService()
    envelope = PlatformEventEnvelope(
        topic=EventTopic.INCIDENT_OFFLINE_CHECK,
        org_id=uuid4(),
        entity_type='incident',
        entity_id=str(uuid4()),
        producer='test',
        occurred_at=datetime.now(timezone.utc),
        idempotency_key='incident-offline:1',
        payload={
            'incident_id': str(uuid4()),
            'device_id': str(uuid4()),
            'incident_active': True,
            'is_stale': True,
            'latest_location_at': (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
        },
    )

    result = service.evaluate_event(envelope)

    assert [match.rule_code for match in result.matches] == ['incident_device_offline_too_long']


def test_rules_engine_matches_unusual_locate_activity() -> None:
    service = RulesEngineService()
    envelope = PlatformEventEnvelope(
        topic=EventTopic.SUSPICIOUS_ACCESS_ALERT,
        org_id=uuid4(),
        entity_type='device',
        entity_id=str(uuid4()),
        producer='test',
        occurred_at=datetime.now(timezone.utc),
        idempotency_key='suspicious-access:1',
        payload={
            'device_id': str(uuid4()),
            'actor_sub': 'admin@example.com',
            'unusual_activity': True,
            'lookup_count': 14,
            'denied_count': 1,
            'distinct_device_count': 9,
        },
    )

    result = service.evaluate_event(envelope)

    assert [match.rule_code for match in result.matches] == ['unusual_locate_activity']


def test_rules_engine_retries_pending_command_before_expiring() -> None:
    service = RulesEngineService()
    envelope = PlatformEventEnvelope(
        topic=EventTopic.COMMAND_PENDING_CHECK,
        org_id=uuid4(),
        entity_type='remote_action',
        entity_id=str(uuid4()),
        producer='test',
        occurred_at=datetime.now(timezone.utc),
        idempotency_key='command-pending:1',
        payload={
            'remote_action_id': str(uuid4()),
            'device_id': str(uuid4()),
            'state': 'pending',
            'attempt_count': 1,
            'should_expire': False,
        },
    )

    result = service.evaluate_event(envelope)

    assert [match.rule_code for match in result.matches] == ['pending_command_retry']
    assert result.matches[0].actions[0].action_type == 'retry_command'


def test_rules_engine_expires_pending_command_when_required() -> None:
    service = RulesEngineService()
    envelope = PlatformEventEnvelope(
        topic=EventTopic.COMMAND_PENDING_CHECK,
        org_id=uuid4(),
        entity_type='remote_action',
        entity_id=str(uuid4()),
        producer='test',
        occurred_at=datetime.now(timezone.utc),
        idempotency_key='command-pending:2',
        payload={
            'remote_action_id': str(uuid4()),
            'device_id': str(uuid4()),
            'state': 'pending',
            'attempt_count': 5,
            'should_expire': True,
        },
    )

    result = service.evaluate_event(envelope)

    assert [match.rule_code for match in result.matches] == ['pending_command_expired']
    assert result.matches[0].actions[0].action_type == 'expire_command'


@pytest.mark.asyncio
async def test_rule_action_executor_rate_limits_repeated_internal_alerts() -> None:
    notification_service = FakeNotificationEventService()
    executor = RuleActionExecutor(
        notification_event_service=notification_service,
        audit_log_service=FakeAuditLogService(),
        command_queue_service=FakeCommandQueueService(),
    )
    session = FakeRuleSession()
    org_id = uuid4()
    match = RuleMatch(
        rule_code='unusual_locate_activity',
        reason='Repeated lookups crossed threshold',
        actions=[
            RuleActionRequest(
                action_type='notify_internal',
                cooldown_scope='admin@example.com',
                payload={'template': 'abuse_alert', 'title': 'Alert', 'body': 'Repeated lookups'},
            )
        ],
    )

    first = await executor.execute_matches(session, org_id=org_id, source_event_id=uuid4(), matches=[match])
    second = await executor.execute_matches(session, org_id=org_id, source_event_id=uuid4(), matches=[match])

    assert first == ['unusual_locate_activity']
    assert second == ['unusual_locate_activity']
    assert len(notification_service.records) == 1


@pytest.mark.asyncio
async def test_event_consumer_worker_dispatches_to_matching_consumer() -> None:
    queue = InMemoryEventQueueService()
    envelope = PlatformEventEnvelope(
        topic=EventTopic.LOCATION_UPDATED,
        org_id=uuid4(),
        entity_type='location_event',
        entity_id=str(uuid4()),
        producer='test',
        occurred_at=datetime.now(timezone.utc),
        idempotency_key='dispatch:1',
        payload={},
    )
    await queue.publish(None, envelope)
    consumer = FakeConsumer()
    worker = EventConsumerWorker(queue=queue, consumers=[consumer])

    results = await worker.drain(None, max_events=2)

    assert len(results) == 1
    assert consumer.calls == 1
    assert results[0].topic == EventTopic.LOCATION_UPDATED.value


class FakeConsumer(BaseEventConsumer):
    topic = EventTopic.LOCATION_UPDATED

    def __init__(self) -> None:
        self.calls = 0
        super().__init__(
            rules_engine=RulesEngineService(),
            action_executor=SimpleNamespace(),
            event_publisher=SimpleNamespace(),
        )

    async def consume(self, session, event_record, envelope: PlatformEventEnvelope) -> ConsumerResult:
        self.calls += 1
        return ConsumerResult(topic=envelope.topic.value, handled=True, executed_rules=[])


class FakeRuleSession:
    def __init__(self) -> None:
        self.lock = None

    async def execute(self, stmt):
        return SimpleNamespace(scalar_one_or_none=lambda: self.lock)

    def add(self, row) -> None:
        self.lock = row

    async def flush(self) -> None:
        return None


class FakeNotificationEventService:
    def __init__(self) -> None:
        self.records: list[dict] = []

    async def create_internal_alert(self, session, **kwargs):
        self.records.append(kwargs)
        return SimpleNamespace(id=uuid4())


class FakeAuditLogService:
    async def append(self, session, **kwargs):
        return SimpleNamespace(id=uuid4(), **kwargs)


class FakeCommandQueueService:
    async def retry_pending_commands(self, session, *, org_id, device_id=None):
        return None

    async def expire_action(self, session, *, remote_action_id, reason):
        return None
