from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import String, cast, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditLog,
    EvidenceExport,
    EvidenceExportFormat,
    EvidenceExportStatus,
    GeofenceEvent,
    Incident,
    IncidentAttachment,
    IncidentEvent,
    IncidentNote,
    LocationEvent,
    RemoteAction,
)
from app.schemas.platform import (
    EvidenceShareRequest,
    IncidentAttachmentCreateRequest,
    IncidentEvidenceExportRequest,
    IncidentNoteCreateRequest,
    IncidentNoteUpdateRequest,
)
from app.services.evidence_export_bundle_service import EvidenceExportBundleService
from app.services.spatial_service import SpatialService


class CaseEvidenceService:
    def apply_redactions(self, payload: dict, redact_fields: list[str]) -> dict:
        redaction_set = {field.strip() for field in redact_fields if field.strip()}
        return self._redact_value(payload, redaction_set)

    async def list_cases(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        state: str | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        assigned_operator_sub: str | None = None,
        search: str | None = None,
    ) -> list[Incident]:
        stmt = select(Incident).where(Incident.org_id == org_id)
        if state:
            stmt = stmt.where(Incident.state == state)
        if updated_from is not None:
            stmt = stmt.where(Incident.updated_at >= updated_from)
        if updated_to is not None:
            stmt = stmt.where(Incident.updated_at <= updated_to)
        if assigned_operator_sub:
            stmt = stmt.where(Incident.assigned_operator_sub == assigned_operator_sub.strip())
        if search:
            like = f'%{search.strip()}%'
            stmt = stmt.where(
                or_(
                    Incident.ticket_reference.ilike(like),
                    Incident.assigned_operator_sub.ilike(like),
                    cast(Incident.device_id, String).ilike(like),
                )
            )
        stmt = stmt.order_by(desc(Incident.updated_at))
        return list((await session.execute(stmt)).scalars().all())

    async def list_notes(
        self,
        session: AsyncSession,
        *,
        incident_id: UUID,
    ) -> list[IncidentNote]:
        stmt = (
            select(IncidentNote)
            .where(IncidentNote.incident_id == incident_id)
            .order_by(desc(IncidentNote.is_pinned), desc(IncidentNote.updated_at))
        )
        return list((await session.execute(stmt)).scalars().all())

    async def create_note(
        self,
        session: AsyncSession,
        *,
        incident: Incident,
        payload: IncidentNoteCreateRequest,
        actor_sub: str,
    ) -> IncidentNote:
        now = datetime.now(timezone.utc)
        note = IncidentNote(
            org_id=incident.org_id,
            incident_id=incident.id,
            author_sub=actor_sub,
            body=payload.body.strip(),
            is_pinned=payload.is_pinned,
            created_at=now,
            updated_at=now,
        )
        session.add(note)
        await session.flush()
        return note

    async def update_note(
        self,
        session: AsyncSession,
        *,
        incident: Incident,
        note_id: UUID,
        payload: IncidentNoteUpdateRequest,
    ) -> IncidentNote:
        note = (
            await session.execute(
                select(IncidentNote).where(
                    IncidentNote.id == note_id,
                    IncidentNote.incident_id == incident.id,
                    IncidentNote.org_id == incident.org_id,
                )
            )
        ).scalar_one_or_none()
        if note is None:
            raise ValueError('Unknown note_id')
        note.body = payload.body.strip()
        note.is_pinned = payload.is_pinned
        note.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return note

    async def list_attachments(
        self,
        session: AsyncSession,
        *,
        incident_id: UUID,
    ) -> list[IncidentAttachment]:
        stmt = (
            select(IncidentAttachment)
            .where(IncidentAttachment.incident_id == incident_id)
            .order_by(desc(IncidentAttachment.created_at))
        )
        return list((await session.execute(stmt)).scalars().all())

    async def create_attachment(
        self,
        session: AsyncSession,
        *,
        incident: Incident,
        payload: IncidentAttachmentCreateRequest,
        actor_sub: str,
    ) -> IncidentAttachment:
        attachment = IncidentAttachment(
            org_id=incident.org_id,
            incident_id=incident.id,
            uploaded_by_sub=actor_sub,
            file_name=payload.file_name.strip(),
            media_type=payload.media_type.strip(),
            byte_size=payload.byte_size,
            sha256=payload.sha256,
            description=payload.description,
            storage_key=payload.storage_key or f'placeholder://incident/{incident.id}/{payload.file_name.strip()}',
            created_at=datetime.now(timezone.utc),
        )
        session.add(attachment)
        await session.flush()
        return attachment

    async def list_exports(
        self,
        session: AsyncSession,
        *,
        incident_id: UUID,
    ) -> list[EvidenceExport]:
        stmt = (
            select(EvidenceExport)
            .where(EvidenceExport.incident_id == incident_id)
            .order_by(desc(EvidenceExport.created_at))
        )
        return list((await session.execute(stmt)).scalars().all())

    async def create_export(
        self,
        session: AsyncSession,
        *,
        incident: Incident,
        payload: IncidentEvidenceExportRequest,
        actor_sub: str,
        spatial_service: SpatialService,
        bundle_service: EvidenceExportBundleService,
        initial_status: EvidenceExportStatus = EvidenceExportStatus.GENERATED,
    ) -> EvidenceExport:
        now = datetime.now(timezone.utc)
        if initial_status == EvidenceExportStatus.PENDING_APPROVAL:
            export = EvidenceExport(
                org_id=incident.org_id,
                incident_id=incident.id,
                requested_by_sub=actor_sub,
                format=payload.format,
                status=initial_status,
                reason=payload.reason.strip(),
                redact_fields_json={'fields': payload.redact_fields},
                summary_json={
                    'placeholder': True,
                    'pending_approval': True,
                    'generated_at': None,
                },
                created_at=now,
                generated_at=None,
            )
            session.add(export)
            await session.flush()
            return export

        chain = await self.build_chain(
            session,
            incident=incident,
            redact_fields=payload.redact_fields,
            spatial_service=spatial_service,
        )
        summary = self._build_export_summary(incident=incident, payload=payload, chain=chain, generated_at=now)
        export = EvidenceExport(
            org_id=incident.org_id,
            incident_id=incident.id,
            requested_by_sub=actor_sub,
            format=payload.format,
            status=initial_status,
            reason=payload.reason.strip(),
            redact_fields_json={'fields': payload.redact_fields},
            summary_json=summary,
            created_at=now,
            generated_at=now,
        )
        session.add(export)
        await session.flush()
        bundle = bundle_service.ensure_bundle(export_record=export, chain=chain)
        export.summary_json = {
            **summary,
            'bundle_path': str(bundle.bundle_path),
            'summary_path': str(bundle.summary_path),
        }
        await session.flush()
        return export

    async def materialize_pending_export(
        self,
        session: AsyncSession,
        *,
        export: EvidenceExport,
        incident: Incident,
        spatial_service: SpatialService,
        bundle_service: EvidenceExportBundleService,
    ) -> EvidenceExport:
        payload = IncidentEvidenceExportRequest(
            org_id=incident.org_id,
            format=export.format,
            reason=export.reason,
            redact_fields=list(export.redact_fields_json.get('fields', [])),
        )
        chain = await self.build_chain(
            session,
            incident=incident,
            redact_fields=payload.redact_fields,
            spatial_service=spatial_service,
        )
        now = datetime.now(timezone.utc)
        summary = {
            **self._build_export_summary(
                incident=incident,
                payload=payload,
                chain=chain,
                generated_at=now,
            ),
        }
        export.status = EvidenceExportStatus.GENERATED
        export.summary_json = summary
        export.generated_at = now
        await session.flush()
        bundle = bundle_service.ensure_bundle(export_record=export, chain=chain)
        export.summary_json = {
            **summary,
            'bundle_path': str(bundle.bundle_path),
            'summary_path': str(bundle.summary_path),
        }
        await session.flush()
        return export

    async def record_external_share(
        self,
        session: AsyncSession,
        *,
        export: EvidenceExport,
        payload: EvidenceShareRequest,
        actor_sub: str,
    ) -> dict:
        shared_at = datetime.now(timezone.utc)
        share_record = {
            'export_id': str(export.id),
            'incident_id': str(export.incident_id),
            'recipient_label': payload.recipient_label.strip(),
            'reason': payload.reason.strip(),
            'shared_by_sub': actor_sub,
            'shared_at': shared_at.isoformat(),
        }
        history = list(export.summary_json.get('external_shares', []))
        history.append(share_record)
        export.summary_json = {
            **deepcopy(export.summary_json),
            'external_shares': history,
            'last_shared_at': share_record['shared_at'],
        }
        await session.flush()
        return share_record

    async def build_chain(
        self,
        session: AsyncSession,
        *,
        incident: Incident,
        redact_fields: list[str],
        spatial_service: SpatialService,
    ) -> dict:
        notes = await self.list_notes(session, incident_id=incident.id)
        attachments = await self.list_attachments(session, incident_id=incident.id)
        exports = await self.list_exports(session, incident_id=incident.id)

        incident_events = list(
            (
                await session.execute(
                    select(IncidentEvent)
                    .where(IncidentEvent.incident_id == incident.id)
                    .order_by(IncidentEvent.occurred_at.asc())
                )
            ).scalars().all()
        )
        remote_actions = list(
            (
                await session.execute(
                    select(RemoteAction)
                    .where(RemoteAction.incident_id == incident.id)
                    .order_by(RemoteAction.requested_at.asc())
                )
            ).scalars().all()
        )
        export_ids = [str(export.id) for export in exports] or ['00000000-0000-0000-0000-000000000000']
        note_ids = [str(note.id) for note in notes] or ['00000000-0000-0000-0000-000000000000']
        attachment_ids = [str(attachment.id) for attachment in attachments] or ['00000000-0000-0000-0000-000000000000']
        audit_logs = list(
            (
                await session.execute(
                    select(AuditLog)
                    .where(
                        AuditLog.org_id == incident.org_id,
                        or_(
                            (AuditLog.entity_type == 'incident') & (AuditLog.entity_id == str(incident.id)),
                            (AuditLog.entity_type == 'remote_action')
                            & (AuditLog.entity_id.in_([str(action.id) for action in remote_actions] or ['00000000-0000-0000-0000-000000000000'])),
                            (AuditLog.entity_type == 'evidence_export') & (AuditLog.entity_id.in_(export_ids)),
                            (AuditLog.entity_type == 'incident_note') & (AuditLog.entity_id.in_(note_ids)),
                            (AuditLog.entity_type == 'incident_attachment') & (AuditLog.entity_id.in_(attachment_ids)),
                        ),
                    )
                    .order_by(AuditLog.occurred_at.asc())
                )
            ).scalars().all()
        )
        incident_route = await spatial_service.get_incident_route(
            session,
            org_id=incident.org_id,
            incident_id=incident.id,
            starts_at=incident.created_at,
            ends_at=incident.updated_at,
            limit=200,
        )
        _, points, geofence_events, _ = incident_route
        location_timeline = [self._serialize_location_point(point=point, spatial_service=spatial_service) for point in points]
        geofence_event_rows = [
            self._serialize_geofence_event(geofence_event=geofence_event, geofence_name=geofence_name)
            for geofence_event, geofence_name in geofence_events
        ]
        command_history = [self._serialize_remote_action(action) for action in remote_actions]
        audit_trail = [self._serialize_audit_log(audit) for audit in audit_logs]
        external_shares = self._collect_external_shares(exports)

        entries: list[dict] = []
        for event in incident_events:
            entries.append(
                {
                    'entry_id': f'incident-event-{event.id}',
                    'kind': 'incident_event',
                    'title': event.action.replace('_', ' ').title(),
                    'summary': event.summary,
                    'occurred_at': event.occurred_at,
                    'actor_sub': event.metadata_json.get('actor_sub'),
                    'mutable': False,
                    'data': deepcopy(event.metadata_json),
                }
            )
        for point in points:
            point_summary = self._location_summary(point=point, spatial_service=spatial_service)
            entries.append(
                {
                    'entry_id': f'location-{point.id}',
                    'kind': 'location',
                    'title': 'Location sample',
                    'summary': point_summary,
                    'occurred_at': point.captured_at,
                    'actor_sub': None,
                    'mutable': False,
                    'data': self._serialize_location_point(point=point, spatial_service=spatial_service),
                }
            )
        for geofence_event, geofence_name in geofence_events:
            entries.append(
                {
                    'entry_id': f'geofence-{geofence_event.id}',
                    'kind': 'geofence',
                    'title': f'Geofence {geofence_event.event_type.value}',
                    'summary': geofence_name or 'Geofence transition',
                    'occurred_at': geofence_event.triggered_at,
                    'actor_sub': None,
                    'mutable': False,
                    'data': {
                        'geofence_id': str(geofence_event.geofence_id),
                        'geofence_name': geofence_name,
                        'precision': geofence_event.precision.value,
                        'confidence_score': geofence_event.confidence_score,
                        'alert_emitted': geofence_event.alert_emitted,
                    },
                }
            )
        for action in remote_actions:
            entries.append(
                {
                    'entry_id': f'remote-action-{action.id}',
                    'kind': 'remote_action',
                    'title': action.action_kind.value.replace('_', ' ').title(),
                    'summary': f'{action.state.value.upper()} command attempt',
                    'occurred_at': action.requested_at,
                    'actor_sub': action.requested_by_sub,
                    'mutable': False,
                    'data': {
                        'state': action.state.value,
                        'reason': action.reason,
                        'last_error': action.last_error,
                        'delayed_until': action.delayed_until.isoformat() if action.delayed_until else None,
                    },
                }
            )
        for attachment in attachments:
            entries.append(
                {
                    'entry_id': f'attachment-{attachment.id}',
                    'kind': 'attachment',
                    'title': attachment.file_name,
                    'summary': attachment.description or attachment.media_type,
                    'occurred_at': attachment.created_at,
                    'actor_sub': attachment.uploaded_by_sub,
                    'mutable': False,
                    'data': {
                        'media_type': attachment.media_type,
                        'byte_size': attachment.byte_size,
                        'sha256': attachment.sha256,
                    },
                }
            )
        for note in notes:
            entries.append(
                {
                    'entry_id': f'note-{note.id}',
                    'kind': 'note',
                    'title': 'Analyst note',
                    'summary': note.body,
                    'occurred_at': note.updated_at,
                    'actor_sub': note.author_sub,
                    'mutable': True,
                    'data': {'is_pinned': note.is_pinned},
                }
            )
        for audit in audit_logs:
            entries.append(
                {
                    'entry_id': f'audit-{audit.id}',
                    'kind': 'audit',
                    'title': audit.action.replace('_', ' ').title(),
                    'summary': f'Immutable audit event on {audit.entity_type}',
                    'occurred_at': audit.occurred_at,
                    'actor_sub': audit.actor_sub,
                    'mutable': False,
                    'data': deepcopy(audit.metadata_json),
                }
            )

        entries.sort(key=lambda item: item['occurred_at'], reverse=True)
        redacted = self.apply_redactions(
            {
                'incident': {
                    'incident_id': str(incident.id),
                    'org_id': str(incident.org_id),
                    'device_id': str(incident.device_id),
                    'ticket_reference': incident.ticket_reference,
                    'state': incident.state.value,
                    'assigned_operator_sub': incident.assigned_operator_sub,
                    'recovery_message': incident.recovery_message,
                    'lost_mode_until': incident.lost_mode_until.isoformat() if incident.lost_mode_until else None,
                    'wipe_scheduled_at': incident.wipe_scheduled_at.isoformat() if incident.wipe_scheduled_at else None,
                    'created_at': incident.created_at.isoformat(),
                    'updated_at': incident.updated_at.isoformat(),
                },
                'incident_summary': {
                    'incident_id': str(incident.id),
                    'ticket_reference': incident.ticket_reference,
                    'state': incident.state.value,
                    'assigned_operator_sub': incident.assigned_operator_sub,
                    'device_id': str(incident.device_id),
                    'org_id': str(incident.org_id),
                    'recovery_message': incident.recovery_message,
                    'created_at': incident.created_at.isoformat(),
                    'updated_at': incident.updated_at.isoformat(),
                },
                'location_timeline': location_timeline,
                'audit_trail': audit_trail,
                'command_history': command_history,
                'geofence_events': geofence_event_rows,
                'entries': entries,
                'notes': [
                    {
                        'note_id': str(note.id),
                        'incident_id': str(note.incident_id),
                        'author_sub': note.author_sub,
                        'body': note.body,
                        'is_pinned': note.is_pinned,
                        'created_at': note.created_at.isoformat(),
                        'updated_at': note.updated_at.isoformat(),
                    }
                    for note in notes
                ],
                'attachments': [
                    {
                        'attachment_id': str(attachment.id),
                        'incident_id': str(attachment.incident_id),
                        'uploaded_by_sub': attachment.uploaded_by_sub,
                        'file_name': attachment.file_name,
                        'media_type': attachment.media_type,
                        'byte_size': attachment.byte_size,
                        'sha256': attachment.sha256,
                        'description': attachment.description,
                        'storage_key': attachment.storage_key,
                        'created_at': attachment.created_at.isoformat(),
                    }
                    for attachment in attachments
                ],
                'exports': [
                    {
                        'export_id': str(export.id),
                        'incident_id': str(export.incident_id),
                        'requested_by_sub': export.requested_by_sub,
                        'format': export.format.value,
                        'status': export.status.value,
                        'reason': export.reason,
                        'redact_fields': list(export.redact_fields_json.get('fields', [])),
                        'summary': deepcopy(export.summary_json),
                        'download_placeholder': f'placeholder://exports/{export.id}.{export.format.value}',
                        'created_at': export.created_at.isoformat(),
                        'generated_at': export.generated_at.isoformat() if export.generated_at else None,
                    }
                    for export in exports
                ],
                'actions_taken': [
                    action for action in command_history
                ],
                'external_shares': external_shares,
            },
            redact_fields,
        )
        return redacted

    def _build_export_summary(
        self,
        *,
        incident: Incident,
        payload: IncidentEvidenceExportRequest,
        chain: dict,
        generated_at: datetime,
    ) -> dict:
        return {
            'format': payload.format.value,
            'placeholder': payload.format != EvidenceExportFormat.CSV,
            'incident_id': str(incident.id),
            'entry_count': len(chain['entries']),
            'location_count': len(chain.get('location_timeline', [])),
            'audit_event_count': len(chain.get('audit_trail', [])),
            'command_count': len(chain.get('command_history', [])),
            'note_count': len(chain['notes']),
            'attachment_count': len(chain['attachments']),
            'geofence_event_count': len(chain.get('geofence_events', [])),
            'generated_at': generated_at.isoformat(),
            'summary_preview': {
                'state': incident.state.value,
                'ticket_reference': chain['incident'].get('ticket_reference'),
                'assigned_operator_sub': chain['incident'].get('assigned_operator_sub'),
            },
        }

    def _location_summary(self, *, point: LocationEvent, spatial_service: SpatialService) -> str:
        source_label = spatial_service.source_label_for(point)
        if point.precision.value == 'approximate' or point.is_ip_approximate:
            return f'{source_label} (Approximate only - not exact recovery position)'
        return f'{source_label} ({point.precision.value})'

    def _serialize_location_point(self, *, point: LocationEvent, spatial_service: SpatialService) -> dict:
        return {
            'event_id': str(point.id),
            'device_id': str(point.device_id),
            'captured_at': point.captured_at.isoformat(),
            'latitude': float(point.latitude) if point.latitude is not None else None,
            'longitude': float(point.longitude) if point.longitude is not None else None,
            'accuracy_meters': float(point.accuracy_meters) if point.accuracy_meters is not None else None,
            'precision': point.precision.value,
            'confidence_score': point.confidence_score,
            'source_methods': list((point.source_methods or {}).get('methods', [])),
            'is_ip_approximate': bool(point.is_ip_approximate),
            'source_label': spatial_service.source_label_for(point),
            'approximate_label': (
                'Approximate source only'
                if point.precision.value == 'approximate' or point.is_ip_approximate
                else 'Not approximate'
            ),
            'staleness_label': 'Historical timeline point',
        }

    def _serialize_geofence_event(self, *, geofence_event: GeofenceEvent, geofence_name: str | None) -> dict:
        return {
            'geofence_event_id': str(geofence_event.id),
            'geofence_id': str(geofence_event.geofence_id),
            'geofence_name': geofence_name,
            'device_id': str(geofence_event.device_id),
            'event_type': geofence_event.event_type.value,
            'precision': geofence_event.precision.value,
            'confidence_score': geofence_event.confidence_score,
            'alert_emitted': geofence_event.alert_emitted,
            'suppressed_reason': geofence_event.suppressed_reason,
            'triggered_at': geofence_event.triggered_at.isoformat(),
        }

    def _serialize_remote_action(self, action: RemoteAction) -> dict:
        return {
            'remote_action_id': str(action.id),
            'action_kind': action.action_kind.value,
            'state': action.state.value,
            'reason': action.reason,
            'requested_by_sub': action.requested_by_sub,
            'requested_at': action.requested_at.isoformat(),
            'sent_at': action.sent_at.isoformat() if action.sent_at else None,
            'delivered_at': action.delivered_at.isoformat() if action.delivered_at else None,
            'acked_at': action.acked_at.isoformat() if action.acked_at else None,
            'failed_at': action.failed_at.isoformat() if action.failed_at else None,
            'last_error': action.last_error,
        }

    def _serialize_audit_log(self, audit: AuditLog) -> dict:
        return {
            'audit_id': str(audit.id),
            'org_id': str(audit.org_id) if audit.org_id else None,
            'actor_sub': audit.actor_sub,
            'action': audit.action,
            'entity_type': audit.entity_type,
            'entity_id': audit.entity_id,
            'metadata': deepcopy(audit.metadata_json),
            'occurred_at': audit.occurred_at.isoformat(),
            'previous_hash': audit.previous_hash,
            'event_hash': audit.event_hash,
        }

    def _collect_external_shares(self, exports: list[EvidenceExport]) -> list[dict]:
        rows: list[dict] = []
        for export in exports:
            for share in export.summary_json.get('external_shares', []):
                rows.append(deepcopy(share))
        rows.sort(key=lambda item: item.get('shared_at', ''), reverse=True)
        return rows

    def _redact_value(self, value, redact_fields: set[str]):
        if isinstance(value, dict):
            redacted: dict = {}
            for key, nested in value.items():
                if key in redact_fields:
                    redacted[key] = '[REDACTED]'
                else:
                    redacted[key] = self._redact_value(nested, redact_fields)
            return redacted
        if isinstance(value, list):
            return [self._redact_value(item, redact_fields) for item in value]
        return value
