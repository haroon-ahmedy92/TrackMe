from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, or_, select
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
    ) -> list[Incident]:
        stmt = (
            select(Incident)
            .where(Incident.org_id == org_id)
            .order_by(desc(Incident.updated_at))
        )
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
        summary = {
            'format': payload.format.value,
            'placeholder': True,
            'incident_id': str(incident.id),
            'entry_count': len(chain['entries']),
            'note_count': len(chain['notes']),
            'attachment_count': len(chain['attachments']),
            'generated_at': now.isoformat(),
            'summary_preview': {
                'state': incident.state.value,
                'ticket_reference': chain['incident'].get('ticket_reference'),
            },
        }
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
            'format': export.format.value,
            'placeholder': True,
            'incident_id': str(incident.id),
            'entry_count': len(chain['entries']),
            'note_count': len(chain['notes']),
            'attachment_count': len(chain['attachments']),
            'generated_at': now.isoformat(),
            'summary_preview': {
                'state': incident.state.value,
                'ticket_reference': chain['incident'].get('ticket_reference'),
            },
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
            entries.append(
                {
                    'entry_id': f'location-{point.id}',
                    'kind': 'location',
                    'title': 'Location sample',
                    'summary': spatial_service.source_label_for(point),
                    'occurred_at': point.captured_at,
                    'actor_sub': None,
                    'mutable': False,
                    'data': {
                        'latitude': float(point.latitude) if point.latitude is not None else None,
                        'longitude': float(point.longitude) if point.longitude is not None else None,
                        'accuracy_meters': float(point.accuracy_meters) if point.accuracy_meters is not None else None,
                        'precision': point.precision.value,
                        'confidence_score': point.confidence_score,
                        'is_ip_approximate': point.is_ip_approximate,
                    },
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
                    'recovery_message': incident.recovery_message,
                    'lost_mode_until': incident.lost_mode_until.isoformat() if incident.lost_mode_until else None,
                    'wipe_scheduled_at': incident.wipe_scheduled_at.isoformat() if incident.wipe_scheduled_at else None,
                    'created_at': incident.created_at.isoformat(),
                    'updated_at': incident.updated_at.isoformat(),
                },
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
                    {
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
                    for action in remote_actions
                ],
            },
            redact_fields,
        )
        return redacted

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
