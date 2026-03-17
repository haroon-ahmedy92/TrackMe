from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Geofence, LocationPrecision
from app.schemas.events import EventTopic, PlatformEventEnvelope
from app.schemas.platform import LocationIngestRequest


@dataclass(frozen=True)
class RuleEvaluation:
    matches: list[str]


@dataclass(frozen=True)
class RuleActionRequest:
    action_type: str
    payload: dict = field(default_factory=dict)
    cooldown_scope: str | None = None
    cooldown_seconds: int | None = None


@dataclass(frozen=True)
class RuleMatch:
    rule_code: str
    reason: str
    actions: list[RuleActionRequest]


@dataclass(frozen=True)
class EventRuleEvaluation:
    matches: list[RuleMatch]


class RulesEngineService:
    async def evaluate_location(
        self,
        session: AsyncSession,
        payload: LocationIngestRequest,
    ) -> RuleEvaluation:
        matches: list[str] = []

        if payload.precision == LocationPrecision.APPROXIMATE:
            matches.append('APPROXIMATE_SIGNAL_ONLY')
        if payload.confidence_score is not None and payload.confidence_score < 40:
            matches.append('LOW_CONFIDENCE_SCORE')

        if payload.latitude is None or payload.longitude is None:
            return RuleEvaluation(matches=matches)

        geofence_matches = await self._evaluate_geofence(
            session=session,
            org_id=payload.org_id,
            device_id=payload.device_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
        matches.extend(geofence_matches)
        return RuleEvaluation(matches=sorted(set(matches)))

    def evaluate_event(self, event: PlatformEventEnvelope) -> EventRuleEvaluation:
        if event.topic == EventTopic.GEOFENCE_TRANSITION:
            return self._evaluate_geofence_transition(event)
        if event.topic == EventTopic.INCIDENT_OFFLINE_CHECK:
            return self._evaluate_offline_incident(event)
        if event.topic == EventTopic.SUSPICIOUS_ACCESS_ALERT:
            return self._evaluate_suspicious_access(event)
        if event.topic == EventTopic.COMMAND_PENDING_CHECK:
            return self._evaluate_pending_command(event)
        return EventRuleEvaluation(matches=[])

    async def _evaluate_geofence(
        self,
        session: AsyncSession,
        org_id: UUID,
        device_id: UUID,
        latitude: float,
        longitude: float,
    ) -> list[str]:
        stmt = select(Geofence).where(
            Geofence.org_id == org_id,
            Geofence.is_enabled.is_(True),
            or_(Geofence.device_id.is_(None), Geofence.device_id == device_id),
        )
        geofences = list((await session.execute(stmt)).scalars().all())
        if not geofences:
            return []

        triggered: list[str] = []
        for geofence in geofences:
            distance_m = self._haversine_meters(
                lat1=float(latitude),
                lon1=float(longitude),
                lat2=float(geofence.center_latitude),
                lon2=float(geofence.center_longitude),
            )
            if distance_m > geofence.radius_meters:
                triggered.append(f'GEOFENCE_EXIT:{geofence.id}')
        return triggered

    def _haversine_meters(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius = 6_371_000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _evaluate_geofence_transition(self, event: PlatformEventEnvelope) -> EventRuleEvaluation:
        payload = event.payload
        if payload.get('event_type') != 'exit' or not payload.get('alert_emitted', False):
            return EventRuleEvaluation(matches=[])
        incident = payload.get('active_incident')
        if not incident:
            return EventRuleEvaluation(matches=[])
        lost_mode_until = incident.get('lost_mode_until')
        if not lost_mode_until:
            return EventRuleEvaluation(matches=[])
        lost_until = _parse_datetime(lost_mode_until)
        if lost_until is None or lost_until <= datetime.now(timezone.utc):
            return EventRuleEvaluation(matches=[])

        geofence_id = payload.get('geofence_id')
        incident_id = incident.get('incident_id')
        device_id = payload.get('device_id')
        return EventRuleEvaluation(
            matches=[
                RuleMatch(
                    rule_code='geofence_exit_during_lost_mode',
                    reason='Device exited a monitored geofence while lost mode was still active.',
                    actions=[
                        RuleActionRequest(
                            action_type='notify_internal',
                            cooldown_scope=f'geofence-exit:{device_id}:{geofence_id}',
                            payload={
                                'template': 'lost_mode_geofence_exit',
                                'device_id': device_id,
                                'incident_id': incident_id,
                                'title': 'Lost mode geofence exit detected',
                                'body': 'A protected device exited a monitored geofence while lost mode remained active.',
                            },
                        ),
                        RuleActionRequest(
                            action_type='audit',
                            payload={
                                'action': 'RULE_GEOFENCE_EXIT_ESCALATED',
                                'entity_type': 'geofence_event',
                                'entity_id': event.entity_id,
                                'metadata': {'incident_id': incident_id, 'geofence_id': geofence_id},
                            },
                        ),
                    ],
                )
            ]
        )

    def _evaluate_offline_incident(self, event: PlatformEventEnvelope) -> EventRuleEvaluation:
        payload = event.payload
        if not payload.get('incident_active', False) or not payload.get('is_stale', False):
            return EventRuleEvaluation(matches=[])
        incident_id = payload.get('incident_id')
        device_id = payload.get('device_id')
        return EventRuleEvaluation(
            matches=[
                RuleMatch(
                    rule_code='incident_device_offline_too_long',
                    reason='Device has not checked in within the configured stale window during an active incident.',
                    actions=[
                        RuleActionRequest(
                            action_type='notify_internal',
                            cooldown_scope=f'incident-offline:{incident_id}',
                            payload={
                                'template': 'incident_device_stale',
                                'device_id': device_id,
                                'incident_id': incident_id,
                                'title': 'Incident device is stale',
                                'body': 'The device has been offline long enough to treat its last known location as stale.',
                            },
                        ),
                        RuleActionRequest(
                            action_type='audit',
                            payload={
                                'action': 'RULE_INCIDENT_DEVICE_STALE',
                                'entity_type': 'incident',
                                'entity_id': str(incident_id),
                                'metadata': {'device_id': device_id, 'latest_location_at': payload.get('latest_location_at')},
                            },
                        ),
                    ],
                )
            ]
        )

    def _evaluate_suspicious_access(self, event: PlatformEventEnvelope) -> EventRuleEvaluation:
        payload = event.payload
        if not payload.get('unusual_activity', False):
            return EventRuleEvaluation(matches=[])
        actor_sub = payload.get('actor_sub')
        return EventRuleEvaluation(
            matches=[
                RuleMatch(
                    rule_code='unusual_locate_activity',
                    reason='Repeated locate requests crossed the unusual admin activity threshold.',
                    actions=[
                        RuleActionRequest(
                            action_type='notify_internal',
                            cooldown_scope=f'unusual-locate:{actor_sub}',
                            payload={
                                'template': 'abuse_alert',
                                'device_id': payload.get('device_id'),
                                'title': 'Potential abuse pattern detected',
                                'body': 'Repeated locate requests from unusual admin activity triggered an abuse alert.',
                            },
                        ),
                        RuleActionRequest(
                            action_type='audit',
                            payload={
                                'action': 'RULE_UNUSUAL_LOCATE_ACTIVITY',
                                'entity_type': 'device',
                                'entity_id': str(payload.get('device_id')),
                                'metadata': {
                                    'actor_sub': actor_sub,
                                    'lookup_count': payload.get('lookup_count'),
                                    'denied_count': payload.get('denied_count'),
                                    'distinct_device_count': payload.get('distinct_device_count'),
                                },
                            },
                        ),
                    ],
                )
            ]
        )

    def _evaluate_pending_command(self, event: PlatformEventEnvelope) -> EventRuleEvaluation:
        payload = event.payload
        state = payload.get('state')
        if state not in {'pending', 'sent', 'delivered'}:
            return EventRuleEvaluation(matches=[])
        command_id = payload.get('remote_action_id')
        device_id = payload.get('device_id')
        if payload.get('should_expire', False):
            return EventRuleEvaluation(
                matches=[
                    RuleMatch(
                        rule_code='pending_command_expired',
                        reason='Command stayed pending past its valid delivery window.',
                        actions=[
                            RuleActionRequest(
                                action_type='expire_command',
                                payload={'remote_action_id': command_id, 'reason': 'Pending command exceeded delivery window.'},
                            ),
                            RuleActionRequest(
                                action_type='audit',
                                payload={
                                    'action': 'RULE_PENDING_COMMAND_EXPIRED',
                                    'entity_type': 'remote_action',
                                    'entity_id': str(command_id),
                                    'metadata': {'device_id': device_id},
                                },
                            ),
                        ],
                    )
                ]
            )
        return EventRuleEvaluation(
            matches=[
                RuleMatch(
                    rule_code='pending_command_retry',
                    reason='Command remained pending and should be retried while still valid.',
                    actions=[
                        RuleActionRequest(
                            action_type='retry_command',
                            payload={
                                'org_id': str(event.org_id) if event.org_id else None,
                                'device_id': device_id,
                                'remote_action_id': command_id,
                            },
                        ),
                        RuleActionRequest(
                            action_type='audit',
                            payload={
                                'action': 'RULE_PENDING_COMMAND_RETRY',
                                'entity_type': 'remote_action',
                                'entity_id': str(command_id),
                                'metadata': {'device_id': device_id, 'attempt_count': payload.get('attempt_count')},
                            },
                        ),
                    ],
                )
            ]
        )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
