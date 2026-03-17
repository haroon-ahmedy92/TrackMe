from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import GeofenceEvent, Incident, IncidentEvent, LocationEvent, RemoteAction
from app.schemas.events import (
    CommandAcknowledgedPayload,
    CommandPendingCheckPayload,
    EventTopic,
    GeofenceTransitionPayload,
    IncidentOfflineCheckPayload,
    IncidentStateChangedPayload,
    LocationUpdatedPayload,
    PlatformEventEnvelope,
    SuspiciousAccessAlertPayload,
)
from app.services.event_queue_service import EventQueue, QueuePublishResult


class EventPublisherService:
    def __init__(self, queue: EventQueue) -> None:
        self.queue = queue

    async def publish_location_updated(
        self,
        session: AsyncSession,
        *,
        location_event: LocationEvent,
        rule_matches: list[str],
        suspicious_alerts: list[str],
    ) -> QueuePublishResult:
        if self._queue_unavailable(session):
            return self._noop_result()
        payload = LocationUpdatedPayload(
            location_event_id=location_event.id,
            device_id=location_event.device_id,
            mode=location_event.mode.value,
            captured_at=location_event.captured_at,
            precision=location_event.precision.value,
            confidence_score=location_event.confidence_score,
            rule_matches=rule_matches,
            suspicious_alerts=suspicious_alerts,
        )
        return await self._publish_if_possible(
            session,
            PlatformEventEnvelope(
                topic=EventTopic.LOCATION_UPDATED,
                org_id=location_event.org_id,
                entity_type='location_event',
                entity_id=str(location_event.id),
                producer='location_ingestion',
                occurred_at=location_event.received_at,
                idempotency_key=f'location-event:{location_event.id}',
                payload=payload.model_dump(mode='json'),
            ),
        )

    async def publish_geofence_transition(
        self,
        session: AsyncSession,
        *,
        geofence_event: GeofenceEvent,
    ) -> QueuePublishResult:
        if self._queue_unavailable(session):
            return self._noop_result()
        payload = GeofenceTransitionPayload(
            geofence_event_id=geofence_event.id,
            geofence_id=geofence_event.geofence_id,
            device_id=geofence_event.device_id,
            event_type=geofence_event.event_type.value,
            alert_emitted=geofence_event.alert_emitted,
            precision=geofence_event.precision.value,
            confidence_score=geofence_event.confidence_score,
        )
        return await self._publish_if_possible(
            session,
            PlatformEventEnvelope(
                topic=EventTopic.GEOFENCE_TRANSITION,
                org_id=geofence_event.org_id,
                entity_type='geofence_event',
                entity_id=str(geofence_event.id),
                producer='geofence_service',
                occurred_at=geofence_event.created_at,
                idempotency_key=f'geofence-event:{geofence_event.id}',
                payload=payload.model_dump(mode='json'),
            ),
        )

    async def publish_incident_state_changed(
        self,
        session: AsyncSession,
        *,
        incident: Incident,
        incident_event: IncidentEvent,
    ) -> QueuePublishResult:
        if self._queue_unavailable(session):
            return self._noop_result()
        payload = IncidentStateChangedPayload(
            incident_id=incident.id,
            device_id=incident.device_id,
            state=incident.state.value,
            action=incident_event.action,
            lost_mode_until=incident.lost_mode_until,
            active_incident=incident.state.value in {'suspected_lost', 'confirmed_stolen'},
        )
        return await self._publish_if_possible(
            session,
            PlatformEventEnvelope(
                topic=EventTopic.INCIDENT_STATE_CHANGED,
                org_id=incident.org_id,
                entity_type='incident',
                entity_id=str(incident.id),
                producer='case_management',
                occurred_at=incident.updated_at,
                idempotency_key=f'incident-event:{incident_event.id}',
                payload=payload.model_dump(mode='json'),
            ),
        )

    async def publish_command_acknowledged(
        self,
        session: AsyncSession,
        *,
        action: RemoteAction,
    ) -> QueuePublishResult:
        if self._queue_unavailable(session):
            return self._noop_result()
        payload = CommandAcknowledgedPayload(
            remote_action_id=action.id,
            device_id=action.device_id,
            incident_id=action.incident_id,
            status=action.state.value,
            attempt_count=action.attempt_count,
            expires_at=action.expires_at,
            error_message=action.last_error,
        )
        return await self._publish_if_possible(
            session,
            PlatformEventEnvelope(
                topic=EventTopic.COMMAND_ACKNOWLEDGED,
                org_id=action.org_id,
                entity_type='remote_action',
                entity_id=str(action.id),
                producer='command_queue',
                occurred_at=action.updated_at,
                idempotency_key=f'command-ack:{action.id}:{action.state.value}:{int(action.updated_at.timestamp())}',
                payload=payload.model_dump(mode='json'),
            ),
        )

    async def publish_suspicious_access_signal(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        actor_sub: str,
        result: str,
        reason: str | None,
        request_id: str | None,
    ) -> QueuePublishResult:
        if self._queue_unavailable(session):
            return self._noop_result()
        payload = SuspiciousAccessAlertPayload(
            device_id=device_id,
            actor_sub=actor_sub,
            result=result,
            reason=reason,
            request_id=request_id,
        )
        return await self._publish_if_possible(
            session,
            PlatformEventEnvelope(
                topic=EventTopic.SUSPICIOUS_ACCESS_ALERT,
                org_id=org_id,
                entity_type='device',
                entity_id=str(device_id),
                producer='ownership_locate',
                occurred_at=datetime.now(timezone.utc),
                idempotency_key=f'suspicious-access:{request_id or uuid_fallback(actor_sub, device_id, result)}',
                payload=payload.model_dump(mode='json'),
            ),
        )

    async def schedule_incident_offline_check(
        self,
        session: AsyncSession,
        *,
        incident: Incident,
        expected_latest_captured_at: datetime | None,
    ) -> QueuePublishResult:
        if self._queue_unavailable(session):
            return self._noop_result()
        threshold = timedelta(minutes=settings.incident_offline_threshold_minutes)
        payload = IncidentOfflineCheckPayload(
            incident_id=incident.id,
            device_id=incident.device_id,
            expected_latest_captured_at=expected_latest_captured_at,
            threshold_minutes=settings.incident_offline_threshold_minutes,
        )
        baseline = expected_latest_captured_at or datetime.now(timezone.utc)
        return await self._publish_if_possible(
            session,
            PlatformEventEnvelope(
                topic=EventTopic.INCIDENT_OFFLINE_CHECK,
                org_id=incident.org_id,
                entity_type='incident',
                entity_id=str(incident.id),
                producer='rules_scheduler',
                occurred_at=datetime.now(timezone.utc),
                idempotency_key=f'incident-offline-check:{incident.id}:{int(baseline.timestamp())}',
                payload=payload.model_dump(mode='json'),
                available_at=baseline + threshold,
            ),
        )

    async def schedule_command_pending_check(
        self,
        session: AsyncSession,
        *,
        action: RemoteAction,
    ) -> QueuePublishResult:
        if self._queue_unavailable(session):
            return self._noop_result()
        payload = CommandPendingCheckPayload(
            remote_action_id=action.id,
            device_id=action.device_id,
            incident_id=action.incident_id,
            retry_after_seconds=settings.command_pending_retry_seconds,
        )
        attempt_count = getattr(action, 'attempt_count', 0)
        return await self._publish_if_possible(
            session,
            PlatformEventEnvelope(
                topic=EventTopic.COMMAND_PENDING_CHECK,
                org_id=action.org_id,
                entity_type='remote_action',
                entity_id=str(action.id),
                producer='command_scheduler',
                occurred_at=datetime.now(timezone.utc),
                idempotency_key=f'command-pending-check:{action.id}:{attempt_count}',
                payload=payload.model_dump(mode='json'),
                available_at=datetime.now(timezone.utc) + timedelta(seconds=settings.command_pending_retry_seconds),
            ),
        )

    async def _publish_if_possible(
        self,
        session: AsyncSession,
        envelope: PlatformEventEnvelope,
    ):
        if self._queue_unavailable(session):
            return self._noop_result()
        return await self.queue.publish(session, envelope)

    def _queue_unavailable(self, session: AsyncSession) -> bool:
        return not hasattr(session, 'execute')

    def _noop_result(self):
        return SimpleNamespace(record=None, created=False)


def uuid_fallback(actor_sub: str, device_id: UUID, result: str) -> str:
    safe_actor = actor_sub.replace('@', '-').replace(':', '-')
    return f'{safe_actor}:{device_id}:{result}:{int(datetime.now(timezone.utc).timestamp())}'
