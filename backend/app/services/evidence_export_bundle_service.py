from __future__ import annotations

import csv
import json
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from io import StringIO
from uuid import UUID

from app.db.models import EvidenceExport
from app.services.object_storage_service import ObjectStorageService


@dataclass(frozen=True)
class GeneratedEvidenceBundle:
    bundle_storage_key: str
    bundle_storage_backend: str
    bundle_file_name: str
    bundle_media_type: str
    bundle_local_path: Path | None
    bundle_byte_size: int
    summary_file_name: str
    manifest_file_name: str
    summary_local_path: Path | None = None
    manifest_local_path: Path | None = None

    @property
    def bundle_path(self) -> Path:
        if self.bundle_local_path is None:
            raise RuntimeError('Bundle path is not available for this storage backend.')
        return self.bundle_local_path

    @property
    def summary_path(self) -> Path:
        if self.summary_local_path is None:
            raise RuntimeError('Summary path is not available for this storage backend.')
        return self.summary_local_path

    @property
    def manifest_path(self) -> Path:
        if self.manifest_local_path is None:
            raise RuntimeError('Manifest path is not available for this storage backend.')
        return self.manifest_local_path


class EvidenceExportBundleService:
    def __init__(self, *, object_storage_service: ObjectStorageService) -> None:
        self.object_storage_service = object_storage_service

    async def ensure_bundle(
        self,
        *,
        export_record: EvidenceExport,
        chain: dict,
    ) -> GeneratedEvidenceBundle:
        with tempfile.TemporaryDirectory(prefix='trackme-export-') as temp_dir_value:
            export_dir = Path(temp_dir_value)
            summary_path = export_dir / f'evidence-summary.{export_record.format.value}'
            manifest_path = export_dir / 'manifest.json'
            bundle_file_name = f'evidence-bundle-{export_record.id}.zip'
            bundle_path = export_dir / bundle_file_name
            generated_files: list[tuple[Path, str]] = []

            summary_payload = {
                'incident_summary': chain.get('incident_summary', chain['incident']),
                'incident': chain['incident'],
                'location_timeline': chain.get('location_timeline', []),
                'audit_trail': chain.get('audit_trail', []),
                'command_history': chain.get('command_history', chain['actions_taken']),
                'geofence_events': chain.get('geofence_events', []),
                'actions_taken': chain['actions_taken'],
                'notes': chain['notes'],
                'attachments': chain['attachments'],
                'external_shares': chain.get('external_shares', []),
                'entries': chain['entries'],
                'exports': chain['exports'],
            }
            generated_files.extend(
                self._write_summary_files(
                    export_dir=export_dir,
                    summary_path=summary_path,
                    export_format=export_record.format.value,
                    summary_payload=summary_payload,
                )
            )

            manifest = {
                'export_id': str(export_record.id),
                'incident_id': str(export_record.incident_id),
                'org_id': str(export_record.org_id),
                'format': export_record.format.value,
                'status': export_record.status.value,
                'reason': export_record.reason,
                'redact_fields': list(export_record.redact_fields_json.get('fields', [])),
                'files': [{'name': path.name, 'role': role} for path, role in generated_files]
                + [{'name': 'manifest.json', 'role': 'manifest'}],
            }
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')

            with zipfile.ZipFile(bundle_path, mode='w', compression=zipfile.ZIP_DEFLATED) as bundle_zip:
                for generated_path, _ in generated_files:
                    bundle_zip.write(generated_path, arcname=generated_path.name)
                bundle_zip.write(manifest_path, arcname=manifest_path.name)

            stored = await self.object_storage_service.store_bytes(
                org_id=str(export_record.org_id),
                incident_id=str(export_record.incident_id),
                file_name=bundle_file_name,
                media_type='application/zip',
                payload=bundle_path.read_bytes(),
                object_scope=f'exports/{export_record.id}',
            )
            primary_summary_path = generated_files[0][0] if generated_files else summary_path
            return GeneratedEvidenceBundle(
                bundle_storage_key=stored.storage_key,
                bundle_storage_backend=stored.storage_backend,
                bundle_file_name=stored.file_name,
                bundle_media_type=stored.media_type,
                bundle_local_path=stored.local_path,
                bundle_byte_size=stored.byte_size,
                summary_file_name=primary_summary_path.name,
                manifest_file_name=manifest_path.name,
                summary_local_path=primary_summary_path,
                manifest_local_path=manifest_path,
            )

    def download_url(self, *, incident_id: UUID, export_id: UUID, org_id: UUID) -> str:
        return f'/api/v1/platform/cases/{incident_id}/exports/{export_id}/download?org_id={org_id}'

    def _write_summary_files(
        self,
        *,
        export_dir: Path,
        summary_path: Path,
        export_format: str,
        summary_payload: dict,
    ) -> list[tuple[Path, str]]:
        if export_format == 'csv':
            return self._write_csv_bundle(export_dir=export_dir, summary_payload=summary_payload)
        self._write_summary_file(path=summary_path, export_format=export_format, summary_payload=summary_payload)
        return [(summary_path, 'summary')]

    def _write_summary_file(self, *, path: Path, export_format: str, summary_payload: dict) -> None:
        if export_format == 'json':
            path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding='utf-8')
            return
        path.write_bytes(self._build_basic_pdf(summary_payload))

    def _write_csv_bundle(self, *, export_dir: Path, summary_payload: dict) -> list[tuple[Path, str]]:
        files: list[tuple[Path, str]] = []
        csv_specs = [
            ('incident-summary.csv', 'incident_summary', [summary_payload.get('incident_summary', {})]),
            ('location-timeline.csv', 'location_timeline', summary_payload.get('location_timeline', [])),
            ('actor-action-audit-trail.csv', 'audit_trail', summary_payload.get('audit_trail', [])),
            ('command-history.csv', 'command_history', summary_payload.get('command_history', [])),
            ('geofence-events.csv', 'geofence_events', summary_payload.get('geofence_events', [])),
            ('notes.csv', 'notes', summary_payload.get('notes', [])),
            ('attachments.csv', 'attachments', summary_payload.get('attachments', [])),
            ('external-shares.csv', 'external_shares', summary_payload.get('external_shares', [])),
        ]
        for file_name, role, rows in csv_specs:
            path = export_dir / file_name
            self._write_csv(path=path, rows=rows)
            files.append((path, role))
        return files

    def _write_csv(self, *, path: Path, rows: list[dict]) -> None:
        flat_rows = [self._flatten_row(row) for row in rows]
        fieldnames: list[str] = []
        for row in flat_rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        if not fieldnames:
            fieldnames = ['empty']
            flat_rows = [{'empty': ''}]
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in flat_rows:
            writer.writerow(row)
        path.write_text(buffer.getvalue(), encoding='utf-8')

    def _flatten_row(self, row: dict, *, prefix: str = '') -> dict[str, str]:
        flattened: dict[str, str] = {}
        for key, value in row.items():
            full_key = f'{prefix}{key}' if not prefix else f'{prefix}.{key}'
            if isinstance(value, dict):
                flattened.update(self._flatten_row(value, prefix=full_key))
            elif isinstance(value, list):
                flattened[full_key] = json.dumps(value, sort_keys=True)
            else:
                flattened[full_key] = '' if value is None else str(value)
        return flattened

    # Small no-dependency PDF renderer for evidence summaries.
    def _build_basic_pdf(self, summary_payload: dict) -> bytes:
        incident = summary_payload.get('incident_summary', summary_payload.get('incident', {}))
        lines = [
            'TrackMe Evidence Summary',
            '',
            f"Incident ID: {incident.get('incident_id', '-')}",
            f"Ticket Reference: {incident.get('ticket_reference', '-')}",
            f"State: {incident.get('state', '-')}",
            f"Assigned Operator: {incident.get('assigned_operator_sub') or '-'}",
            f"Recovery Message: {incident.get('recovery_message') or '-'}",
            f"Entries: {len(summary_payload.get('entries', []))}",
            f"Location Timeline Points: {len(summary_payload.get('location_timeline', []))}",
            f"Audit Trail Entries: {len(summary_payload.get('audit_trail', []))}",
            f"Notes: {len(summary_payload.get('notes', []))}",
            f"Attachments: {len(summary_payload.get('attachments', []))}",
            f"Command History: {len(summary_payload.get('command_history', []))}",
            '',
            'Recent Chain Entries:',
        ]
        for entry in summary_payload.get('entries', [])[:12]:
            title = self._sanitize_pdf_text(str(entry.get('title', 'Entry')))
            summary = self._sanitize_pdf_text(str(entry.get('summary', '')))
            lines.append(f'- {title}: {summary[:90]}')

        content_lines = ['BT', '/F1 10 Tf', '40 760 Td']
        first = True
        for raw_line in lines:
            line = self._sanitize_pdf_text(raw_line)
            if not first:
                content_lines.append('0 -14 Td')
            content_lines.append(f'({line}) Tj')
            first = False
        content_lines.append('ET')
        stream = '\n'.join(content_lines).encode('latin-1', errors='replace')

        objects = [
            b'1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj',
            b'2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj',
            b'3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >> endobj',
            b'4 0 obj << /Length ' + str(len(stream)).encode('ascii') + b' >> stream\n' + stream + b'\nendstream endobj',
            b'5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj',
        ]

        pdf = bytearray(b'%PDF-1.4\n')
        offsets = [0]
        for obj in objects:
            offsets.append(len(pdf))
            pdf.extend(obj)
            pdf.extend(b'\n')

        xref_offset = len(pdf)
        pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('ascii'))
        pdf.extend(b'0000000000 65535 f \n')
        for offset in offsets[1:]:
            pdf.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
        pdf.extend(
            (
                f'trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n'
                f'startxref\n{xref_offset}\n%%EOF'
            ).encode('ascii')
        )
        return bytes(pdf)

    def _sanitize_pdf_text(self, value: str) -> str:
        return (
            value.replace('\\', '\\\\')
            .replace('(', '\\(')
            .replace(')', '\\)')
            .replace('\n', ' ')
            .replace('\r', ' ')[:110]
        )
