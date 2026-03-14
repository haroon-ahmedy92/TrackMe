from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.core.config import settings
from app.db.models import EvidenceExport


@dataclass(frozen=True)
class GeneratedEvidenceBundle:
    bundle_path: Path
    summary_path: Path
    manifest_path: Path


class EvidenceExportBundleService:
    def ensure_bundle(
        self,
        *,
        export_record: EvidenceExport,
        chain: dict,
    ) -> GeneratedEvidenceBundle:
        export_dir = self._export_dir(
            org_id=export_record.org_id,
            incident_id=export_record.incident_id,
            export_id=export_record.id,
        )
        export_dir.mkdir(parents=True, exist_ok=True)

        summary_path = export_dir / f'evidence-summary.{export_record.format.value}'
        manifest_path = export_dir / 'manifest.json'
        bundle_path = export_dir / f'evidence-bundle-{export_record.id}.zip'

        summary_payload = {
            'incident': chain['incident'],
            'actions_taken': chain['actions_taken'],
            'notes': chain['notes'],
            'attachments': chain['attachments'],
            'entries': chain['entries'],
            'exports': chain['exports'],
        }
        self._write_summary_file(path=summary_path, export_format=export_record.format.value, summary_payload=summary_payload)

        manifest = {
            'export_id': str(export_record.id),
            'incident_id': str(export_record.incident_id),
            'org_id': str(export_record.org_id),
            'format': export_record.format.value,
            'status': export_record.status.value,
            'reason': export_record.reason,
            'redact_fields': list(export_record.redact_fields_json.get('fields', [])),
            'files': [
                {'name': summary_path.name, 'role': 'summary'},
                {'name': 'manifest.json', 'role': 'manifest'},
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding='utf-8')

        with zipfile.ZipFile(bundle_path, mode='w', compression=zipfile.ZIP_DEFLATED) as bundle_zip:
            bundle_zip.write(summary_path, arcname=summary_path.name)
            bundle_zip.write(manifest_path, arcname=manifest_path.name)

        return GeneratedEvidenceBundle(
            bundle_path=bundle_path,
            summary_path=summary_path,
            manifest_path=manifest_path,
        )

    def bundle_path(self, *, org_id: UUID, incident_id: UUID, export_id: UUID) -> Path:
        return self._export_dir(org_id=org_id, incident_id=incident_id, export_id=export_id) / f'evidence-bundle-{export_id}.zip'

    def download_url(self, *, incident_id: UUID, export_id: UUID, org_id: UUID) -> str:
        return f'/api/v1/platform/cases/{incident_id}/exports/{export_id}/download?org_id={org_id}'

    def _export_dir(self, *, org_id: UUID, incident_id: UUID, export_id: UUID) -> Path:
        return Path(settings.exports_storage_dir) / str(org_id) / str(incident_id) / str(export_id)

    def _write_summary_file(self, *, path: Path, export_format: str, summary_payload: dict) -> None:
        if export_format == 'json':
            path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding='utf-8')
            return
        path.write_bytes(self._build_basic_pdf(summary_payload))

    # Small no-dependency PDF renderer for evidence summaries.
    def _build_basic_pdf(self, summary_payload: dict) -> bytes:
        incident = summary_payload.get('incident', {})
        lines = [
            'TrackMe Evidence Summary',
            '',
            f"Incident ID: {incident.get('incident_id', '-')}",
            f"Ticket Reference: {incident.get('ticket_reference', '-')}",
            f"State: {incident.get('state', '-')}",
            f"Recovery Message: {incident.get('recovery_message') or '-'}",
            f"Entries: {len(summary_payload.get('entries', []))}",
            f"Notes: {len(summary_payload.get('notes', []))}",
            f"Attachments: {len(summary_payload.get('attachments', []))}",
            f"Actions Taken: {len(summary_payload.get('actions_taken', []))}",
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
