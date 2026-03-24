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
import { getCopy } from '@/lib/i18n/copy';
import { freshnessForTimestamp } from '@/lib/maps/provider';
import { useMemo, useState } from 'react';

export default function IncidentsPage() {
  const ui = getCopy(typeof navigator === 'undefined' ? 'en' : navigator.language);
  const incidentsState = useAsyncData(() => apiClient.getIncidents(), []);
  const devicesState = useAsyncData(() => apiClient.getDevices(), []);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [targetDeviceId, setTargetDeviceId] = useState<string>('');
  const [windowHours, setWindowHours] = useState('24');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [modal, setModal] = useState<null | 'markLost' | 'confirmStolen' | 'recover' | 'shareExport'>(null);
  const [noteBody, setNoteBody] = useState('');
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null);
  const [attachmentDescription, setAttachmentDescription] = useState('');
  const [exportFormat, setExportFormat] = useState<'csv' | 'json' | 'pdf'>('csv');
  const [redactionFields, setRedactionFields] = useState('latitude,longitude');
  const [shareRecipient, setShareRecipient] = useState('Regional legal desk');
  const [shareTargetExportId, setShareTargetExportId] = useState<string | null>(null);

  const incidents = useMemo(() => incidentsState.data ?? [], [incidentsState.data]);
  const devices = useMemo(() => devicesState.data ?? [], [devicesState.data]);

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
    if (!selectedIncident || !attachmentFile) {
      return;
    }
    await runAction(async () => {
      await apiClient.uploadCaseAttachment(selectedIncident.id, {
        file: attachmentFile,
        description: attachmentDescription.trim() || undefined,
      });
      setAttachmentFile(null);
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
        <h1 className="page-title">{ui.incidents.title}</h1>
        <p className="page-subtitle">{ui.incidents.subtitle}</p>
      </div>

      {actionError ? (
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{actionError}</p>
        </Card>
      ) : null}

      <Card>
        <h2 style={{ marginTop: 0, marginBottom: 10 }}>{ui.incidents.createTitle}</h2>
        <div className="row">
          <Select
            label={ui.incidents.targetDevice}
            value={targetDeviceId}
            onChange={(event) => setTargetDeviceId(event.target.value)}
            options={[
              { label: ui.incidents.selectDevice, value: '' },
              ...devices.map((device) => ({
                label: `${device.deviceName} (${device.incidentState})`,
                value: device.id,
              })),
            ]}
          />
          <Button style={{ marginTop: 23 }} disabled={!targetDeviceId} onClick={() => setModal('markLost')}>
            {ui.incidents.createButton}
          </Button>
        </div>
      </Card>

      <Card className="warning-note">
        <p style={{ margin: 0 }}>{ui.incidents.approximateWarning}</p>
      </Card>

      <Card>
        <DataTable
          rows={incidents}
          rowKey={(incident) => incident.id}
          columns={[
            {
              key: 'title',
              header: ui.incidents.incident,
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
              header: ui.incidents.lastUpdated,
              cell: (incident) => formatDateTime(incident.updatedAt),
            },
            {
              key: 'window',
              header: ui.incidents.highFrequencyWindow,
              cell: (incident) => (incident.highFrequencyUntil ? formatDateTime(incident.highFrequencyUntil) : ui.incidents.notActive),
            },
          ]}
          emptyMessage="No active incidents"
        />
      </Card>

      {selectedIncident ? (
        <div className="grid-2">
          <Card>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <h2 style={{ margin: 0 }}>{ui.incidents.selectedCase}</h2>
              <Badge variant={selectedIncident.state === 'CONFIRMED_STOLEN' ? 'danger' : 'warning'}>
                {selectedIncident.state}
              </Badge>
            </div>
            <p className="text-muted" style={{ marginTop: 10 }}>
              {ui.incidents.selectedCaseHint}
            </p>
            <p className="text-muted" style={{ marginTop: 8, marginBottom: 0 }}>
              Assigned operator: <strong>{selectedIncident.assignedOperator ?? 'Unassigned'}</strong>
            </p>
            <div className="row" style={{ marginTop: 10 }}>
              <Button variant="danger" onClick={() => setModal('confirmStolen')} disabled={selectedIncident.state !== 'SUSPECTED_LOST'}>
                {ui.incidents.stolenConfirm}
              </Button>
              <Button variant="ghost" onClick={() => setModal('recover')}>
                {ui.incidents.recoveredConfirm}
              </Button>
            </div>
          </Card>

          <Card>
            <h2 style={{ marginTop: 0 }}>{ui.incidents.timelineTitle}</h2>
            <div className="stack" style={{ marginTop: 8 }}>
              {timelineState.loading ? <p className="text-muted">{ui.incidents.timelineLoading}</p> : null}
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
              <h2 style={{ marginTop: 0, marginBottom: 8 }}>{ui.incidents.actionsTitle}</h2>
              <p className="page-subtitle">{ui.incidents.selectedCaseHint}</p>
            </div>
            <Badge variant="neutral">{evidenceState.data?.actionsTaken.length ?? 0} actions</Badge>
          </div>
          <div className="stack" style={{ marginTop: 14 }}>
            {evidenceState.loading ? <p className="text-muted">{ui.incidents.actionsLoading}</p> : null}
            {(evidenceState.data?.actionsTaken ?? []).length === 0 ? (
              <p className="text-muted">{ui.incidents.actionsEmpty}</p>
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
              <h2 style={{ marginTop: 0, marginBottom: 8 }}>{ui.incidents.routeTitle}</h2>
              <p className="page-subtitle">{ui.incidents.routeSubtitle}</p>
            </div>
            <Select
              label={ui.incidents.routeWindow}
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
              routePoints={(routeState.data?.points ?? []).map((point) => ({
                ...point,
                freshness: freshnessForTimestamp(point.collectedAt),
              }))}
              points={
                routeState.data?.points.length
                  ? [
                      {
                        ...routeState.data.points[routeState.data.points.length - 1],
                        freshness: freshnessForTimestamp(
                          routeState.data.points[routeState.data.points.length - 1].collectedAt,
                        ),
                      },
                    ]
                  : []
              }
              height={340}
            />
          </div>
        </Card>
      ) : null}

      {selectedIncident ? (
        <div className="grid-2">
          <Card>
            <h2 style={{ marginTop: 0 }}>{ui.incidents.notesTitle}</h2>
            <Textarea label={ui.incidents.noteLabel} value={noteBody} onChange={(event) => setNoteBody(event.target.value)} />
            <div className="row">
              <Button onClick={() => void submitNote()} disabled={!noteBody.trim() || actionLoading}>
                {ui.incidents.addNote}
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
            <h2 style={{ marginTop: 0 }}>{ui.incidents.attachmentsTitle}</h2>
            <label style={{ display: 'grid', gap: 6, color: 'var(--text-muted)', fontSize: 14 }}>
              Attachment file
              <input
                type="file"
                onChange={(event) => setAttachmentFile(event.target.files?.[0] ?? null)}
                style={{
                  padding: '10px 12px',
                  borderRadius: 12,
                  border: '1px solid var(--border)',
                  background: 'var(--surface-subtle)',
                  color: 'var(--text-primary)',
                }}
              />
            </label>
            {attachmentFile ? (
              <p className="text-muted" style={{ margin: '8px 0 0', fontSize: 12 }}>
                {attachmentFile.name} • {attachmentFile.type || 'application/octet-stream'} • {attachmentFile.size} bytes
              </p>
            ) : null}
            <Textarea label={ui.incidents.attachmentDescription} value={attachmentDescription} onChange={(event) => setAttachmentDescription(event.target.value)} />
            <div className="row">
              <Button onClick={() => void submitAttachment()} disabled={!attachmentFile || actionLoading}>
                {ui.incidents.addAttachment}
              </Button>
            </div>

            <div className="stack" style={{ marginTop: 14 }}>
              {(evidenceState.data?.attachments ?? []).map((attachment) => (
                <div key={attachment.id} style={{ borderLeft: '2px solid var(--border)', paddingLeft: 10 }}>
                  <p style={{ margin: 0, fontWeight: 600 }}>
                    {attachment.downloadUrl ? (
                      <a href={attachment.downloadUrl} style={{ color: 'inherit' }}>
                        {attachment.fileName}
                      </a>
                    ) : (
                      attachment.fileName
                    )}
                  </p>
                  <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
                    {attachment.mediaType} • {attachment.byteSize} bytes • {attachment.storageBackend ?? 'unknown storage'} •{' '}
                    {formatDateTime(attachment.createdAt)}
                  </p>
                  {attachment.description ? <p style={{ margin: '6px 0 0' }}>{attachment.description}</p> : null}
                </div>
              ))}
            </div>

            <div className="stack" style={{ marginTop: 18 }}>
              <Select
                label={ui.incidents.exportFormat}
                value={exportFormat}
                onChange={(event) => setExportFormat(event.target.value as 'csv' | 'json' | 'pdf')}
                options={[
                  { label: ui.incidents.csvExport, value: 'csv' },
                  { label: ui.incidents.jsonExport, value: 'json' },
                  { label: ui.incidents.pdfExport, value: 'pdf' },
                ]}
              />
              <Input label={ui.incidents.redactFields} value={redactionFields} onChange={(event) => setRedactionFields(event.target.value)} />
              <Input
                label={ui.incidents.externalRecipient}
                value={shareRecipient}
                onChange={(event) => setShareRecipient(event.target.value)}
              />
              <Button onClick={() => void submitExport()} disabled={actionLoading}>
                {ui.incidents.requestExport}
              </Button>
              {(evidenceState.data?.exports ?? []).map((item) => (
                <div key={item.id} className="warning-note">
                  <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>
                      {item.format.toUpperCase()} export • {item.status}
                      {item.policyReason ? ` • ${item.policyReason}` : ''}
                    </span>
                    <div className="row">
                      {item.downloadPlaceholder ? (
                        <a href={item.downloadPlaceholder} style={{ color: 'inherit' }}>
                          {ui.incidents.downloadBundle}
                        </a>
                      ) : (
                        <span>{item.status === 'pending_approval' ? ui.incidents.awaitingApproval : ui.incidents.placeholderOnly}</span>
                      )}
                      {item.downloadPlaceholder ? (
                        <Button
                          variant="ghost"
                          onClick={() => {
                            if (!shareRecipient.trim()) {
                              setActionError('Enter the external recipient before sharing an export.');
                              return;
                            }
                            setShareTargetExportId(item.id);
                            setModal('shareExport');
                          }}
                        >
                          {ui.incidents.shareExternally}
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
              {(evidenceState.data?.externalShares ?? []).map((share) => (
                <div key={`${share.exportId}-${share.sharedAt}`} className="warning-note">
                  Shared with {share.recipientLabel} • {formatDateTime(share.sharedAt)} • {share.sharedBy}
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
              <h2 style={{ marginTop: 0, marginBottom: 8 }}>{ui.incidents.evidenceChainTitle}</h2>
              <p className="page-subtitle">{ui.incidents.evidenceChainSubtitle}</p>
            </div>
            <Badge variant="neutral">{evidenceState.data?.entries.length ?? 0} entries</Badge>
          </div>
          <div className="stack" style={{ marginTop: 14 }}>
            {evidenceState.loading ? <p className="text-muted">{ui.incidents.evidenceLoading}</p> : null}
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
        open={modal === 'shareExport'}
        title={ui.incidents.shareTitle}
        description={ui.incidents.shareDescription}
        confirmLabel={ui.incidents.shareConfirm}
        danger
        loading={actionLoading}
        onCancel={() => setModal(null)}
        onConfirm={async (reason) => {
          if (!selectedIncident || !shareTargetExportId) return;
          await runAction(async () => {
            await apiClient.shareEvidenceExport(selectedIncident.id, shareTargetExportId, {
              recipientLabel: shareRecipient,
              reason,
            });
          });
        }}
      />

      <SensitiveActionModal
        open={modal === 'markLost'}
        title={ui.incidents.lostTitle}
        description={ui.incidents.lostDescription}
        confirmLabel={ui.incidents.lostConfirm}
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
        title={ui.incidents.stolenTitle}
        description={ui.incidents.stolenDescription}
        confirmLabel={ui.incidents.stolenConfirm}
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
        title={ui.incidents.recoveredTitle}
        description={ui.incidents.recoveredDescription}
        confirmLabel={ui.incidents.recoveredConfirm}
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
