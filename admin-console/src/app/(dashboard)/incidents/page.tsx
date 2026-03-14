'use client';

import { LoadingCard } from '@/components/common/LoadingCard';
import { SensitiveActionModal } from '@/components/common/SensitiveActionModal';
import { GeoSignalMap } from '@/components/maps/GeoSignalMap';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { Select } from '@/components/ui/Select';
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

  const runAction = async (runner: () => Promise<void>) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await runner();
      await incidentsState.refresh();
      await devicesState.refresh();
      await Promise.all([timelineState.refresh(), routeState.refresh()]);
      setModal(null);
    } catch (errorValue) {
      setActionError(errorValue instanceof Error ? errorValue.message : 'Operation failed');
    } finally {
      setActionLoading(false);
    }
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
        <p className="page-subtitle">Use explicit workflows for loss, theft confirmation, recovery, and audit-backed decisions.</p>
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
          <Button
            style={{ marginTop: 23 }}
            disabled={!targetDeviceId}
            onClick={() => {
              setModal('markLost');
            }}
          >
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
                  style={{
                    border: 0,
                    background: 'transparent',
                    textAlign: 'left',
                    cursor: 'pointer',
                    color: 'var(--text)',
                    padding: 0,
                  }}
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
              cell: (incident) =>
                incident.highFrequencyUntil ? formatDateTime(incident.highFrequencyUntil) : 'Not active',
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
              Actions are visible, explicit, and always auditable.
            </p>

            <div className="row" style={{ marginTop: 10 }}>
              <Button
                variant="danger"
                onClick={() => setModal('confirmStolen')}
                disabled={selectedIncident.state !== 'SUSPECTED_LOST'}
              >
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
              <h2 style={{ marginTop: 0, marginBottom: 8 }}>Incident Route View</h2>
              <p className="page-subtitle">
                Playback stays inside a bounded time window and keeps approximate points visually separate.
              </p>
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
              points={
                routeState.data?.points.length
                  ? [routeState.data.points[routeState.data.points.length - 1]]
                  : []
              }
              height={340}
            />
          </div>

          <div className="grid-2" style={{ marginTop: 16 }}>
            <div className="stack">
              <p style={{ margin: 0, fontWeight: 700 }}>Route summary</p>
              <p className="text-muted" style={{ margin: 0 }}>
                {routeState.loading
                  ? 'Loading bounded incident route...'
                  : `${routeState.data?.points.length ?? 0} points from ${routeState.data ? formatDateTime(routeState.data.startedAt) : 'N/A'} to ${routeState.data ? formatDateTime(routeState.data.endedAt) : 'N/A'}`}
              </p>
            </div>
            <div className="stack">
              <p style={{ margin: 0, fontWeight: 700 }}>Geofence transitions</p>
              {(routeState.data?.geofenceEvents ?? []).length ? (
                routeState.data?.geofenceEvents.slice(-4).reverse().map((event) => (
                  <div key={event.id} style={{ borderLeft: '2px solid var(--border)', paddingLeft: 10 }}>
                    <p style={{ margin: 0, fontWeight: 600 }}>
                      {event.eventType.toUpperCase()} • {event.geofenceName}
                    </p>
                    <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
                      {formatDateTime(event.triggeredAt)}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-muted" style={{ margin: 0 }}>
                  No geofence events were recorded in the selected window.
                </p>
              )}
            </div>
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
          if (!selectedIncident) {
            return;
          }
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
          if (!selectedIncident) {
            return;
          }
          await runAction(async () => {
            await apiClient.recoverIncident(selectedIncident.id, reason);
          });
        }}
      />
    </div>
  );
}
