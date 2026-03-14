from __future__ import annotations

import json
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import AccessReview, AccessReviewStatus, AuditLog, LocationEvent, RemoteAction, RemoteActionState


@dataclass(frozen=True)
class SecuritySignal:
    occurred_at: datetime
    path: str
    ip_address: str
    actor_hint: str | None
    org_id: str | None
    reason: str
    request_id: str | None


class SecuritySignalStore:
    def __init__(self) -> None:
        self._events: deque[SecuritySignal] = deque(maxlen=5000)

    def record_auth_failure(
        self,
        *,
        path: str,
        ip_address: str,
        actor_hint: str | None,
        org_id: str | None,
        reason: str,
        request_id: str | None,
    ) -> None:
        self._events.append(
            SecuritySignal(
                occurred_at=datetime.now(timezone.utc),
                path=path,
                ip_address=ip_address,
                actor_hint=actor_hint,
                org_id=org_id,
                reason=reason,
                request_id=request_id,
            )
        )

    def recent(self, *, org_id: str | None, since: datetime) -> list[SecuritySignal]:
        return [
            event
            for event in self._events
            if event.occurred_at >= since and (org_id is None or event.org_id == org_id)
        ]

    def clear(self) -> None:
        self._events.clear()


security_signal_store = SecuritySignalStore()


class ObservabilityService:
    async def build_dashboard(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        window_hours: int,
    ) -> dict:
        since = self._since(window_hours)
        location_events = await self._location_events(session, org_id=org_id, since=since)
        remote_actions = await self._remote_actions(session, org_id=org_id, since=since)
        audit_logs = await self._audit_logs(session, org_id=org_id, since=since)

        confidence_buckets = Counter()
        precision_distribution = Counter()
        low_battery_events = 0
        battery_values: list[int] = []
        for event in location_events:
            if event.confidence_score is None:
                confidence_buckets['unknown'] += 1
            elif event.confidence_score >= 80:
                confidence_buckets['high'] += 1
            elif event.confidence_score >= 50:
                confidence_buckets['medium'] += 1
            else:
                confidence_buckets['low'] += 1
            precision_distribution[event.precision.value] += 1
            if event.battery_percent is not None:
                battery_values.append(event.battery_percent)
                if event.battery_percent <= 15:
                    low_battery_events += 1

        locate_requests = [row for row in audit_logs if row.action in {'LOCATION_LOOKUP_REQUESTED', 'LOCATION_LOOKUP_DENIED'}]
        actor_counts = Counter(row.actor_sub for row in locate_requests)
        denied_counts = Counter(row.actor_sub for row in locate_requests if row.action == 'LOCATION_LOOKUP_DENIED')
        top_actor = actor_counts.most_common(1)[0] if actor_counts else None

        return {
            'ingestion_health': {
                'window_hours': window_hours,
                'location_events': len(location_events),
                'last_ingested_at': location_events[0].received_at.isoformat() if location_events else None,
                'approximate_events': sum(1 for row in location_events if row.is_ip_approximate),
                'telemetry_verified_events': sum(1 for row in location_events if row.telemetry_verified),
            },
            'failed_commands': {
                'failed_count': sum(1 for action in remote_actions if action.state == RemoteActionState.FAILED),
                'expired_count': sum(1 for action in remote_actions if action.state == RemoteActionState.EXPIRED),
                'top_last_errors': Counter(action.last_error or 'unknown' for action in remote_actions if action.last_error).most_common(5),
            },
            'battery_impact': {
                'samples_with_battery': len(battery_values),
                'average_battery_percent': round(sum(battery_values) / len(battery_values), 2) if battery_values else None,
                'low_battery_samples': low_battery_events,
            },
            'location_confidence_distribution': {
                'confidence_buckets': dict(confidence_buckets),
                'precision_distribution': dict(precision_distribution),
            },
            'suspicious_actor_behavior': {
                'top_lookup_actor': {
                    'actor_sub': top_actor[0],
                    'lookup_count': top_actor[1],
                    'denied_count': denied_counts.get(top_actor[0], 0),
                } if top_actor else None,
                'unique_lookup_actors': len(actor_counts),
            },
        }

    async def detect_alerts(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        window_hours: int,
    ) -> list[dict]:
        since = self._since(window_hours)
        alerts: list[dict] = []
        audit_logs = await self._audit_logs(session, org_id=org_id, since=since)
        remote_actions = await self._remote_actions(session, org_id=org_id, since=since)
        signals = security_signal_store.recent(org_id=str(org_id), since=since)

        locate_requests = [row for row in audit_logs if row.action == 'LOCATION_LOOKUP_REQUESTED']
        by_actor: dict[str, list[AuditLog]] = defaultdict(list)
        for row in locate_requests:
            by_actor[row.actor_sub].append(row)
        for actor_sub, rows in by_actor.items():
            distinct_devices = {row.entity_id for row in rows}
            if len(rows) >= settings.observability_bulk_lookup_threshold or len(distinct_devices) >= max(5, settings.observability_bulk_lookup_threshold // 2):
                alerts.append(
                    {
                        'code': 'bulk_location_lookup',
                        'severity': 'high',
                        'actor_sub': actor_sub,
                        'count': len(rows),
                        'device_count': len(distinct_devices),
                        'summary': 'Actor performed unusually high volume location lookups.',
                    }
                )

        denied = [row for row in audit_logs if row.action == 'LOCATION_LOOKUP_DENIED']
        denied_by_actor = Counter(row.actor_sub for row in denied)
        for actor_sub, count in denied_by_actor.items():
            if count >= settings.observability_failed_auth_threshold:
                alerts.append(
                    {
                        'code': 'repeated_locate_denied',
                        'severity': 'medium',
                        'actor_sub': actor_sub,
                        'count': count,
                        'summary': 'Actor had repeated denied location lookups.',
                    }
                )

        if len(signals) >= settings.observability_failed_auth_threshold:
            alerts.append(
                {
                    'code': 'repeated_failed_authorization',
                    'severity': 'high',
                    'actor_sub': None,
                    'count': len(signals),
                    'summary': 'Repeated HTTP authorization failures detected.',
                    'examples': [event.path for event in signals[:3]],
                }
            )

        failed_commands = [action for action in remote_actions if action.state in {RemoteActionState.FAILED, RemoteActionState.EXPIRED}]
        if len(failed_commands) >= settings.observability_failed_command_threshold:
            alerts.append(
                {
                    'code': 'command_failure_spike',
                    'severity': 'medium',
                    'actor_sub': None,
                    'count': len(failed_commands),
                    'summary': 'Remote command failures are elevated in the current window.',
                }
            )

        return alerts

    async def build_access_review_report(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        window_hours: int,
    ) -> dict:
        since = self._since(window_hours)
        rows = list(
            (
                await session.execute(
                    select(AccessReview)
                    .where(and_(AccessReview.org_id == org_id, AccessReview.created_at >= since))
                    .order_by(desc(AccessReview.created_at))
                )
            ).scalars().all()
        )
        return {
            'window_hours': window_hours,
            'totals': {
                'pending': sum(1 for row in rows if row.status == AccessReviewStatus.PENDING),
                'approved': sum(1 for row in rows if row.status == AccessReviewStatus.APPROVED),
                'rejected': sum(1 for row in rows if row.status == AccessReviewStatus.REJECTED),
            },
            'reviews': [
                {
                    'access_review_id': str(row.id),
                    'device_id': str(row.device_id),
                    'requested_by_sub': row.requested_by_sub,
                    'reviewed_by_sub': row.reviewed_by_sub,
                    'status': row.status.value,
                    'rationale': row.rationale,
                    'review_notes': row.review_notes,
                    'created_at': row.created_at.isoformat(),
                    'reviewed_at': row.reviewed_at.isoformat() if row.reviewed_at else None,
                }
                for row in rows
            ],
        }

    async def build_audit_report(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        window_hours: int,
    ) -> dict:
        since = self._since(window_hours)
        rows = await self._audit_logs(session, org_id=org_id, since=since)
        return {
            'org_id': str(org_id),
            'window_hours': window_hours,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'entries': [self._normalize_audit_row(row) for row in rows],
        }

    def export_audit_report(self, *, org_id: UUID, report: dict) -> Path:
        report_dir = Path(settings.exports_storage_dir) / 'observability' / str(org_id)
        report_dir.mkdir(parents=True, exist_ok=True)
        output_path = report_dir / f'audit-report-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}.json'
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding='utf-8')
        return output_path

    async def _audit_logs(self, session: AsyncSession, *, org_id: UUID, since: datetime) -> list[AuditLog]:
        return list(
            (
                await session.execute(
                    select(AuditLog)
                    .where(and_(AuditLog.org_id == org_id, AuditLog.occurred_at >= since))
                    .order_by(desc(AuditLog.occurred_at))
                )
            ).scalars().all()
        )

    async def _remote_actions(self, session: AsyncSession, *, org_id: UUID, since: datetime) -> list[RemoteAction]:
        return list(
            (
                await session.execute(
                    select(RemoteAction)
                    .where(and_(RemoteAction.org_id == org_id, RemoteAction.requested_at >= since))
                    .order_by(desc(RemoteAction.requested_at))
                )
            ).scalars().all()
        )

    async def _location_events(self, session: AsyncSession, *, org_id: UUID, since: datetime) -> list[LocationEvent]:
        return list(
            (
                await session.execute(
                    select(LocationEvent)
                    .where(and_(LocationEvent.org_id == org_id, LocationEvent.received_at >= since))
                    .order_by(desc(LocationEvent.received_at))
                )
            ).scalars().all()
        )

    def _normalize_audit_row(self, row: AuditLog) -> dict:
        metadata = row.metadata_json or {}
        return {
            'audit_id': str(row.id),
            'occurred_at': row.occurred_at.isoformat(),
            'actor_sub': row.actor_sub,
            'action': row.action,
            'entity_type': row.entity_type,
            'entity_id': row.entity_id,
            'reason': metadata.get('reason') or metadata.get('decision_reason'),
            'result': metadata.get('result') or ('denied' if row.action.endswith('DENIED') else 'success'),
            'request_id': metadata.get('request_id'),
            'device_id': metadata.get('device_id') or (row.entity_id if row.entity_type == 'device' else None),
            'privacy_preserving': True,
            'metadata': metadata,
        }

    def _since(self, window_hours: int) -> datetime:
        bounded_hours = max(1, min(window_hours, settings.spatial_max_history_hours))
        return datetime.now(timezone.utc) - timedelta(hours=bounded_hours)
