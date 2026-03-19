'use client';

import { LoadingCard } from '@/components/common/LoadingCard';
import { SensitiveActionModal } from '@/components/common/SensitiveActionModal';
import { GeoSignalMap } from '@/components/maps/GeoSignalMap';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { apiClient } from '@/lib/api/client';
import { formatDateTime } from '@/lib/format';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import { useMemo, useState } from 'react';

export default function IncidentsPage() {
  const incidentsState = useAsyncData(() => apiClient.getIncidents(), []);
  const devicesState = useAsyncData(() => apiClient.getDevices(), []);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [targetDeviceId, setTargetDeviceId] = useState<string>('');
  const [windowHours, setWindowHours] = useState('24');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [modal, setModal] = useState<null | 'markLost' | 'confirmStolen' | 'recover'>(null);
  const [noteBody, setNoteBody] = useState('');
  const [attachmentName, setAttachmentName] = useState('');
  const [attachmentType, setAttachmentType] = useState('application/pdf');
  const [attachmentSize, setAttachmentSize] = useState('1024');
  const [attachmentDescription, setAttachmentDescription] = useState('');
  const [exportFormat, setExportFormat] = useState<'json' | 'pdf'>('json');
  const [redactionFields, setRedactionFields] = useState('latitude,longitude');

  const incidents = incidentsState.data ?? [];
  const devices = devicesState.data ?? [];

  const selectedIncident = useMemo(
    () => incidents.find((incident) => incident.id === selectedIncidentId) ?? incidents[0] ?? null,
    [incidents, selectedIncidentId],
  );

  const timelineState = useAsyncData(
    () => (selectedIncident ? apiClient.getIncidentTimeline(selectedIncident.id) : Promise.resolve([])),
    [selectedIncident?.id],
  );
  const routeState = useAsyncData(
    () =>
      selectedIncident ? apiClient.getIncidentRoute(selectedIncident.id, Number(windowHours)) : Promise.resolve(null),
    [selectedIncident?.id, windowHours],
  );
  const evidenceState = useAsyncData(
    () =>
      selectedIncident
        ? apiClient.getCaseEvidenceChain(
            selectedIncident.id,
            redactionFields
              .split(',')
              .map((field) => field.trim())
              .filter(Boolean),
          )
        : Promise.resolve(null),
    [selectedIncident?.id, redactionFields],
  );

  const refreshCaseViews = async () => {
    await Promise.all([incidentsState.refresh(), devicesState.refresh(), timelineState.refresh(), routeState.refresh(), evidenceState.refresh()]);
  };

  const runAction = async (runner: () => Promise<void>) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await runner();
      await refreshCaseViews();
      setModal(null);
    } catch (errorValue) {
      setActionError(errorValue instanceof Error ? errorValue.message : 'Operation failed');
    } finally {
      setActionLoading(false);
    }
  };

  const submitNote = async () => {
    if (!selectedIncident || !noteBody.trim()) {
      return;
    }
    await runAction(async () => {
      await apiClient.addCaseNote(selectedIncident.id, { body: noteBody.trim(), pinned: false });
      setNoteBody('');
    });
  };

  const submitAttachment = async () => {
    if (!selectedIncident || !attachmentName.trim()) {
      return;
    }
    await runAction(async () => {
      await apiClient.addCaseAttachment(selectedIncident.id, {
        fileName: attachmentName.trim(),
        mediaType: attachmentType.trim(),
        byteSize: Number(attachmentSize) || 1,
        description: attachmentDescription.trim() || undefined,
      });
      setAttachmentName('');
      setAttachmentDescription('');
    });
  };

  const submitExport = async () => {
    if (!selectedIncident) {
      return;
    }
    await runAction(async () => {
      await apiClient.requestEvidenceExport(selectedIncident.id, {
        format: exportFormat,
        reason: 'Case evidence summary requested by operator',
        redactFields: redactionFields
          .split(',')
          .map((field) => field.trim())
          .filter(Boolean),
      });
    });
  };

  if (incidentsState.loading || devicesState.loading) {
    return (
      <div className="page">
        <LoadingCard />
      </div>
    );
  }

  if (incidentsState.error || devicesState.error) {
    return (
      <div className="page">
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>
            {incidentsState.error ?? devicesState.error ?? 'Could not load incidents.'}
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="page container stack">
      <div>
        <h1 className="page-title">Incident Case Management</h1>
        <p className="page-subtitle">
          Recovery case handling, evidence notes, attachments, exports, and command history in one reviewable workflow.
        </p>
      </div>

      {actionError ? (
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{actionError}</p>
        </Card>
      ) : null}

      <Card>
        <h2 style={{ marginTop: 0, marginBottom: 10 }}>Create or escalate incident</h2>
        <div className="row">
          <Select
            label="Target device"
            value={targetDeviceId}
            onChange={(event) => setTargetDeviceId(event.target.value)}
            options={[
              { label: 'Select device', value: '' },
              ...devices.map((device) => ({
                label: `${device.deviceName} (${device.incidentState})`,
                value: device.id,
              })),
            ]}
          />
          <Button style={{ marginTop: 23 }} disabled={!targetDeviceId} onClick={() => setModal('markLost')}>
            Mark Device as Lost
          </Button>
        </div>
      </Card>

      <Card>
        <DataTable
          rows={incidents}
          rowKey={(incident) => incident.id}
          columns={[
            {
              key: 'title',
              header: 'Incident',
              cell: (incident) => (
                <button
                  type="button"
                  onClick={() => setSelectedIncidentId(incident.id)}
                  style={{ border: 0, background: 'transparent', textAlign: 'left', cursor: 'pointer', color: 'var(--text)', padding: 0 }}
                >
                  <span style={{ fontWeight: 700 }}>{incident.title}</span>
                  <span className="text-muted" style={{ display: 'block', fontSize: 12 }}>
                    ID: {incident.id}
                  </span>
                </button>
              ),
            },
            {
              key: 'state',
              header: 'State',
              cell: (incident) => (
                <Badge variant={incident.state === 'CONFIRMED_STOLEN' ? 'danger' : 'warning'}>{incident.state}</Badge>
              ),
            },
            {
              key: 'updated',
              header: 'Last Updated',
              cell: (incident) => formatDateTime(incident.updatedAt),
            },
            {
              key: 'window',
              header: 'High-Frequency Window',
              cell: (incident) => (incident.highFrequencyUntil ? formatDateTime(incident.highFrequencyUntil) : 'Not active'),
            },
          ]}
          emptyMessage="No active incidents"
        />
      </Card>

      {selectedIncident ? (
        <div className="grid-2">
          <Card>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <h2 style={{ margin: 0 }}>Selected Case</h2>
              <Badge variant={selectedIncident.state === 'CONFIRMED_STOLEN' ? 'danger' : 'warning'}>
                {selectedIncident.state}
              </Badge>
            </div>
            <p className="text-muted" style={{ marginTop: 10 }}>
              Actor attribution, exports, notes, and command attempts stay visible for review.
            </p>
            <div className="row" style={{ marginTop: 10 }}>
              <Button variant="danger" onClick={() => setModal('confirmStolen')} disabled={selectedIncident.state !== 'SUSPECTED_LOST'}>
                Confirm Stolen
              </Button>
              <Button variant="ghost" onClick={() => setModal('recover')}>
                Mark Recovered
              </Button>
            </div>
          </Card>

          <Card>
            <h2 style={{ marginTop: 0 }}>Evidence Timeline</h2>
            <div className="stack" style={{ marginTop: 8 }}>
              {timelineState.loading ? <p className="text-muted">Loading timeline...</p> : null}
              {(timelineState.data ?? []).map((event) => (
                <div key={event.id} style={{ borderLeft: '2px solid var(--border)', paddingLeft: 10 }}>
                  <p style={{ margin: 0, fontWeight: 600 }}>{event.eventType}</p>
                  <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
                    {formatDateTime(event.createdAt)} • {event.actor}
                  </p>
                  <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 13 }}>{event.reason}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      ) : null}

      {selectedIncident ? (
        <Card>
          <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-end' }}>
            <div>
              <h2 style={{ marginTop: 0, marginBottom: 8 }}>Actions Taken During Recovery</h2>
              <p className="page-subtitle">
                Signed command attempts, delivery state, and actor attribution stay visible alongside the case.
              </p>
            </div>
            <Badge variant="neutral">{evidenceState.data?.actionsTaken.length ?? 0} actions</Badge>
          </div>
          <div className="stack" style={{ marginTop: 14 }}>
            {evidenceState.loading ? <p className="text-muted">Loading command evidence...</p> : null}
            {(evidenceState.data?.actionsTaken ?? []).length === 0 ? (
              <p className="text-muted">No command attempts are linked to this case yet.</p>
            ) : null}
            {(evidenceState.data?.actionsTaken ?? []).map((action) => (
              <div key={action.id} style={{ borderLeft: '2px solid var(--border)', paddingLeft: 12 }}>
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <p style={{ margin: 0, fontWeight: 700 }}>{action.actionKind.replaceAll('_', ' ')}</p>
                  <Badge variant={action.state === 'failed' ? 'danger' : action.state === 'acked' ? 'success' : 'neutral'}>
                    {action.state}
                  </Badge>
                </div>
                <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
                  {formatDateTime(action.requestedAt)} • {action.requestedBy}
                </p>
                <p style={{ margin: '6px 0 0' }}>{action.reason}</p>
                {action.lastError ? (
                  <p style={{ margin: '6px 0 0', color: 'var(--danger)', fontSize: 13 }}>{action.lastError}</p>
                ) : null}
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      {selectedIncident ? (
        <Card>
          <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-end' }}>
            <div>
              <h2 style={{ marginTop: 0, marginBottom: 8 }}>Route & Location Evidence</h2>
              <p className="page-subtitle">Playback stays time-bounded, and approximate signals never pretend to be exact.</p>
            </div>
            <Select
              label="Route window"
              value={windowHours}
              onChange={(event) => setWindowHours(event.target.value)}
              options={[
                { label: '6 hours', value: '6' },
                { label: '24 hours', value: '24' },
                { label: '72 hours', value: '72' },
              ]}
            />
          </div>

          <div style={{ marginTop: 16 }}>
            <GeoSignalMap
              title="No route points are available in this time window"
              routePoints={routeState.data?.points ?? []}
              points={routeState.data?.points.length ? [routeState.data.points[routeState.data.points.length - 1]] : []}
              height={340}
            />
          </div>
        </Card>
      ) : null}

      {selectedIncident ? (
        <div className="grid-2">
          <Card>
            <h2 style={{ marginTop: 0 }}>Case Notes</h2>
            <Textarea label="New note" value={noteBody} onChange={(event) => setNoteBody(event.target.value)} />
            <div className="row">
              <Button onClick={() => void submitNote()} disabled={!noteBody.trim() || actionLoading}>
                Add Note
              </Button>
            </div>
            <div className="stack" style={{ marginTop: 12 }}>
              {(evidenceState.data?.notes ?? []).map((note) => (
                <div key={note.id} style={{ borderLeft: '2px solid var(--border)', paddingLeft: 10 }}>
                  <p style={{ margin: 0, fontWeight: 600 }}>
                    {note.author} {note.pinned ? '• pinned' : ''}
                  </p>
                  <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
                    {formatDateTime(note.updatedAt)}
                  </p>
                  <p style={{ margin: '6px 0 0' }}>{note.body}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <h2 style={{ marginTop: 0 }}>Attachments & Export</h2>
            <Input label="Attachment name" value={attachmentName} onChange={(event) => setAttachmentName(event.target.value)} />
            <Input label="Media type" value={attachmentType} onChange={(event) => setAttachmentType(event.target.value)} />
            <Input label="Byte size" value={attachmentSize} onChange={(event) => setAttachmentSize(event.target.value)} />
            <Textarea label="Attachment description" value={attachmentDescription} onChange={(event) => setAttachmentDescription(event.target.value)} />
            <div className="row">
              <Button onClick={() => void submitAttachment()} disabled={!attachmentName.trim() || actionLoading}>
                Add Attachment
              </Button>
            </div>

            <div className="stack" style={{ marginTop: 14 }}>
              {(evidenceState.data?.attachments ?? []).map((attachment) => (
                <div key={attachment.id} style={{ borderLeft: '2px solid var(--border)', paddingLeft: 10 }}>
                  <p style={{ margin: 0, fontWeight: 600 }}>{attachment.fileName}</p>
                  <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
                    {attachment.mediaType} • {attachment.byteSize} bytes • {formatDateTime(attachment.createdAt)}
                  </p>
                  {attachment.description ? <p style={{ margin: '6px 0 0' }}>{attachment.description}</p> : null}
                </div>
              ))}
            </div>

            <div className="stack" style={{ marginTop: 18 }}>
              <Select
                label="Export format"
                value={exportFormat}
                onChange={(event) => setExportFormat(event.target.value as 'json' | 'pdf')}
                options={[
                  { label: 'JSON summary placeholder', value: 'json' },
                  { label: 'PDF summary placeholder', value: 'pdf' },
                ]}
              />
              <Input label="Redact fields" value={redactionFields} onChange={(event) => setRedactionFields(event.target.value)} />
              <Button onClick={() => void submitExport()} disabled={actionLoading}>
                Request Evidence Export
              </Button>
              {(evidenceState.data?.exports ?? []).map((item) => (
                <div key={item.id} className="warning-note">
                  {item.format.toUpperCase()} export • {item.status}
                  {item.policyReason ? ` • ${item.policyReason}` : ''} •{' '}
                  {item.downloadPlaceholder ? (
                    <a href={item.downloadPlaceholder} style={{ color: 'inherit' }}>
                      download bundle
                    </a>
                  ) : (
                    item.status === 'pending_approval' ? 'awaiting approval' : 'placeholder only'
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>
      ) : null}

      {selectedIncident ? (
        <Card>
          <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-end' }}>
            <div>
              <h2 style={{ marginTop: 0, marginBottom: 8 }}>Case Evidence Chain</h2>
              <p className="page-subtitle">
                This view combines immutable case events, location evidence, geofence alerts, command attempts, attachments, and mutable notes.
              </p>
            </div>
            <Badge variant="neutral">{evidenceState.data?.entries.length ?? 0} entries</Badge>
          </div>
          <div className="stack" style={{ marginTop: 14 }}>
            {evidenceState.loading ? <p className="text-muted">Loading case evidence…</p> : null}
            {(evidenceState.data?.entries ?? []).map((entry) => (
              <div key={entry.id} style={{ borderLeft: '2px solid var(--border)', paddingLeft: 12 }}>
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <p style={{ margin: 0, fontWeight: 700 }}>{entry.title}</p>
                  <Badge variant={entry.mutable ? 'warning' : 'neutral'}>{entry.kind}</Badge>
                </div>
                <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
                  {formatDateTime(entry.occurredAt)}{entry.actor ? ` • ${entry.actor}` : ''}
                </p>
                <p style={{ margin: '6px 0 0' }}>{entry.summary}</p>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      <SensitiveActionModal
        open={modal === 'markLost'}
        title="Mark Device as Lost"
        description="Starts a time-boxed higher-frequency reporting window with clear incident visibility."
        confirmLabel="Confirm Lost Mode"
        loading={actionLoading}
        onCancel={() => setModal(null)}
        onConfirm={async (reason) => {
          await runAction(async () => {
            await apiClient.markDeviceLost(targetDeviceId, reason);
          });
        }}
      />

      <SensitiveActionModal
        open={modal === 'confirmStolen'}
        title="Confirm Stolen"
        description="This is an elevated decision and should only be used after verification."
        confirmLabel="Confirm Theft"
        danger
        loading={actionLoading}
        onCancel={() => setModal(null)}
        onConfirm={async (reason) => {
          if (!selectedIncident) return;
          await runAction(async () => {
            await apiClient.confirmDeviceStolen(selectedIncident.id, reason);
          });
        }}
      />

      <SensitiveActionModal
        open={modal === 'recover'}
        title="Mark Incident Recovered"
        description="Ends lost/stolen workflows and records the closure reason in immutable audit logs."
        confirmLabel="Mark Recovered"
        loading={actionLoading}
        onCancel={() => setModal(null)}
        onConfirm={async (reason) => {
          if (!selectedIncident) return;
          await runAction(async () => {
            await apiClient.recoverIncident(selectedIncident.id, reason);
          });
        }}
      />
    </div>
  );
}
