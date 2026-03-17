from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import AuditLog, Incident, IncidentCaseState, LocationEvent, RemoteAction, RemoteActionState
from app.schemas.events import EventTopic, PlatformEventEnvelope
from app.services.event_publisher_service import EventPublisherService
from app.services.event_queue_service import EventQueue, SqlAlchemyEventQueueService
from app.services.rule_action_executor import RuleActionExecutor
from app.services.rules_engine_service import RulesEngineService


@dataclass(frozen=True)
class ConsumerResult:
    topic: str
    handled: bool
    executed_rules: list[str]


class BaseEventConsumer:
    topic: EventTopic

    def __init__(
        self,
        *,
        rules_engine: RulesEngineService,
        action_executor: RuleActionExecutor,
        event_publisher: EventPublisherService,
    ) -> None:
        self.rules_engine = rules_engine
        self.action_executor = action_executor
        self.event_publisher = event_publisher

    async def consume(self, session: AsyncSession, event_record, envelope: PlatformEventEnvelope) -> ConsumerResult:
        return ConsumerResult(topic=envelope.topic.value, handled=True, executed_rules=[])


class LocationUpdateConsumer(BaseEventConsumer):
    topic = EventTopic.LOCATION_UPDATED

    async def consume(self, session: AsyncSession, event_record, envelope: PlatformEventEnvelope) -> ConsumerResult:
        device_id = envelope.payload.get('device_id')
        latest_incident = (
            await session.execute(
                select(Incident)
                .where(
                    Incident.org_id == envelope.org_id,
                    Incident.device_id == _uuid_or_none(device_id),
                    Incident.state.in_([IncidentCaseState.SUSPECTED_LOST, IncidentCaseState.CONFIRMED_STOLEN]),
                )
                .order_by(desc(Incident.updated_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest_incident is not None:
            await self.event_publisher.schedule_incident_offline_check(
                session,
                incident=latest_incident,
                expected_latest_captured_at=_parse_datetime(envelope.payload.get('captured_at')),
            )
        return ConsumerResult(topic=envelope.topic.value, handled=True, executed_rules=[])


class GeofenceEventConsumer(BaseEventConsumer):
    topic = EventTopic.GEOFENCE_TRANSITION

    async def consume(self, session: AsyncSession, event_record, envelope: PlatformEventEnvelope) -> ConsumerResult:
        device_id = envelope.payload.get('device_id')
        latest_incident = (
            await session.execute(
                select(Incident)
                .where(
                    Incident.org_id == envelope.org_id,
                    Incident.device_id == _uuid_or_none(device_id),
                    Incident.state.in_([IncidentCaseState.SUSPECTED_LOST, IncidentCaseState.CONFIRMED_STOLEN]),
                )
                .order_by(desc(Incident.updated_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        enriched = envelope.model_copy(
            update={
                'payload': {
                    **envelope.payload,
                    'active_incident': (
                        {
                            'incident_id': str(latest_incident.id),
                            'state': latest_incident.state.value,
                            'lost_mode_until': latest_incident.lost_mode_until.isoformat() if latest_incident.lost_mode_until else None,
                        }
                        if latest_incident is not None
                        else None
                    ),
                }
            }
        )
        result = self.rules_engine.evaluate_event(enriched)
        executed = await self.action_executor.execute_matches(
            session,
            org_id=envelope.org_id,
            source_event_id=event_record.id,
            matches=result.matches,
        )
        return ConsumerResult(topic=enriched.topic.value, handled=True, executed_rules=executed)


class IncidentStateChangeConsumer(BaseEventConsumer):
    topic = EventTopic.INCIDENT_STATE_CHANGED

    async def consume(self, session: AsyncSession, event_record, envelope: PlatformEventEnvelope) -> ConsumerResult:
        if envelope.payload.get('active_incident'):
            latest_location = (
                await session.execute(
                    select(LocationEvent)
                    .where(
                        LocationEvent.org_id == envelope.org_id,
                        LocationEvent.device_id == _uuid_or_none(envelope.payload.get('device_id')),
                    )
                    .order_by(desc(LocationEvent.captured_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            incident = (
                await session.execute(select(Incident).where(Incident.id == _uuid_or_none(envelope.payload.get('incident_id'))))
            ).scalar_one_or_none()
            if incident is not None:
                await self.event_publisher.schedule_incident_offline_check(
                    session,
                    incident=incident,
                    expected_latest_captured_at=latest_location.captured_at if latest_location else None,
                )
        return ConsumerResult(topic=envelope.topic.value, handled=True, executed_rules=[])


class CommandAcknowledgementConsumer(BaseEventConsumer):
    topic = EventTopic.COMMAND_ACKNOWLEDGED

    async def consume(self, session: AsyncSession, event_record, envelope: PlatformEventEnvelope) -> ConsumerResult:
        return ConsumerResult(topic=envelope.topic.value, handled=True, executed_rules=[])


class SuspiciousAccessAlertConsumer(BaseEventConsumer):
    topic = EventTopic.SUSPICIOUS_ACCESS_ALERT

    async def consume(self, session: AsyncSession, event_record, envelope: PlatformEventEnvelope) -> ConsumerResult:
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        actor_sub = envelope.payload.get('actor_sub')
        rows = list(
            (
                await session.execute(
                    select(AuditLog)
                    .where(
                        AuditLog.org_id == envelope.org_id,
                        AuditLog.actor_sub == actor_sub,
                        AuditLog.action.in_(['LOCATION_LOOKUP_REQUESTED', 'LOCATION_LOOKUP_DENIED']),
                        AuditLog.occurred_at >= since,
                    )
                    .order_by(desc(AuditLog.occurred_at))
                )
            ).scalars().all()
        )
        enriched = envelope.model_copy(
            update={
                'payload': {
                    **envelope.payload,
                    'lookup_count': len(rows),
                    'denied_count': sum(1 for row in rows if row.action == 'LOCATION_LOOKUP_DENIED'),
                    'distinct_device_count': len({row.entity_id for row in rows}),
                    'unusual_activity': len(rows) >= settings.observability_bulk_lookup_threshold,
                }
            }
        )
        result = self.rules_engine.evaluate_event(enriched)
        executed = await self.action_executor.execute_matches(
            session,
            org_id=envelope.org_id,
            source_event_id=event_record.id,
            matches=result.matches,
        )
        return ConsumerResult(topic=enriched.topic.value, handled=True, executed_rules=executed)


class IncidentOfflineCheckConsumer(BaseEventConsumer):
    topic = EventTopic.INCIDENT_OFFLINE_CHECK

    async def consume(self, session: AsyncSession, event_record, envelope: PlatformEventEnvelope) -> ConsumerResult:
        incident = (
            await session.execute(select(Incident).where(Incident.id == _uuid_or_none(envelope.payload.get('incident_id'))))
        ).scalar_one_or_none()
        if incident is None:
            return ConsumerResult(topic=envelope.topic.value, handled=True, executed_rules=[])
        latest_location = (
            await session.execute(
                select(LocationEvent)
                .where(
                    LocationEvent.org_id == envelope.org_id,
                    LocationEvent.device_id == incident.device_id,
                )
                .order_by(desc(LocationEvent.captured_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        latest_location_at = latest_location.captured_at if latest_location else None
        expected_latest = _parse_datetime(envelope.payload.get('expected_latest_captured_at'))
        stale_threshold = timedelta(minutes=int(envelope.payload.get('threshold_minutes', settings.incident_offline_threshold_minutes)))
        now = datetime.now(timezone.utc)
        is_active = incident.state in {IncidentCaseState.SUSPECTED_LOST, IncidentCaseState.CONFIRMED_STOLEN}
        is_stale = latest_location_at is None or (now - latest_location_at) >= stale_threshold
        has_no_newer_update = expected_latest is None or latest_location_at is None or latest_location_at <= expected_latest
        enriched = envelope.model_copy(
            update={
                'payload': {
                    **envelope.payload,
                    'incident_active': is_active,
                    'latest_location_at': latest_location_at.isoformat() if latest_location_at else None,
                    'is_stale': is_stale and has_no_newer_update,
                }
            }
        )
        result = self.rules_engine.evaluate_event(enriched)
        executed = await self.action_executor.execute_matches(
            session,
            org_id=envelope.org_id,
            source_event_id=event_record.id,
            matches=result.matches,
        )
        return ConsumerResult(topic=enriched.topic.value, handled=True, executed_rules=executed)


class CommandPendingCheckConsumer(BaseEventConsumer):
    topic = EventTopic.COMMAND_PENDING_CHECK

    async def consume(self, session: AsyncSession, event_record, envelope: PlatformEventEnvelope) -> ConsumerResult:
        action = (
                await session.execute(select(RemoteAction).where(RemoteAction.id == _uuid_or_none(envelope.payload.get('remote_action_id'))))
        ).scalar_one_or_none()
        if action is None:
            return ConsumerResult(topic=envelope.topic.value, handled=True, executed_rules=[])
        now = datetime.now(timezone.utc)
        should_expire = (
            action.state in {RemoteActionState.PENDING, RemoteActionState.SENT, RemoteActionState.DELIVERED}
            and (
                (action.expires_at is not None and action.expires_at <= now)
                or action.attempt_count >= settings.command_max_attempts
            )
        )
        enriched = envelope.model_copy(
            update={
                'payload': {
                    **envelope.payload,
                    'state': action.state.value,
                    'attempt_count': action.attempt_count,
                    'should_expire': should_expire,
                }
            }
        )
        result = self.rules_engine.evaluate_event(enriched)
        executed = await self.action_executor.execute_matches(
            session,
            org_id=envelope.org_id,
            source_event_id=event_record.id,
            matches=result.matches,
        )
        if action.state in {RemoteActionState.PENDING, RemoteActionState.SENT, RemoteActionState.DELIVERED} and not should_expire:
            await self.event_publisher.schedule_command_pending_check(session, action=action)
        return ConsumerResult(topic=enriched.topic.value, handled=True, executed_rules=executed)


class EventConsumerWorker:
    def __init__(
        self,
        *,
        queue: EventQueue,
        consumers: list[BaseEventConsumer],
    ) -> None:
        self.queue = queue
        self.consumers = {consumer.topic.value: consumer for consumer in consumers}

    async def process_once(self, session: AsyncSession, *, worker_name: str = 'rules-worker') -> ConsumerResult | None:
        record = await self.queue.claim_next(session, worker_name=worker_name, topics=set(self.consumers.keys()))
        if record is None:
            return None
        envelope = self.queue.to_envelope(record) if hasattr(self.queue, 'to_envelope') else PlatformEventEnvelope(**record.payload_json)
        consumer = self.consumers.get(envelope.topic.value)
        if consumer is None:
            await self.queue.mark_completed(session, record=record)
            return ConsumerResult(topic=envelope.topic.value, handled=True, executed_rules=[])
        try:
            result = await consumer.consume(session, record, envelope)
            await self.queue.mark_completed(session, record=record)
            return result
        except Exception as exc:
            await self.queue.mark_failed(session, record=record, error_message=str(exc))
            raise

    async def drain(self, session: AsyncSession, *, worker_name: str = 'rules-worker', max_events: int = 100) -> list[ConsumerResult]:
        results: list[ConsumerResult] = []
        for _ in range(max_events):
            result = await self.process_once(session, worker_name=worker_name)
            if result is None:
                break
            results.append(result)
        return results


def build_default_event_worker(
    *,
    queue: EventQueue | None,
    rules_engine: RulesEngineService,
    action_executor: RuleActionExecutor,
    event_publisher: EventPublisherService,
) -> EventConsumerWorker:
    queue_service = queue or SqlAlchemyEventQueueService()
    consumers: list[BaseEventConsumer] = [
        LocationUpdateConsumer(rules_engine=rules_engine, action_executor=action_executor, event_publisher=event_publisher),
        GeofenceEventConsumer(rules_engine=rules_engine, action_executor=action_executor, event_publisher=event_publisher),
        IncidentStateChangeConsumer(rules_engine=rules_engine, action_executor=action_executor, event_publisher=event_publisher),
        CommandAcknowledgementConsumer(rules_engine=rules_engine, action_executor=action_executor, event_publisher=event_publisher),
        SuspiciousAccessAlertConsumer(rules_engine=rules_engine, action_executor=action_executor, event_publisher=event_publisher),
        IncidentOfflineCheckConsumer(rules_engine=rules_engine, action_executor=action_executor, event_publisher=event_publisher),
        CommandPendingCheckConsumer(rules_engine=rules_engine, action_executor=action_executor, event_publisher=event_publisher),
    ]
    return EventConsumerWorker(queue=queue_service, consumers=consumers)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _uuid_or_none(value):
    if value in (None, ''):
        return None
    return value if isinstance(value, UUID) else UUID(str(value))
