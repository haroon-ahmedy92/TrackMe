'use client';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { LoadingCard } from '@/components/common/LoadingCard';
import { LocationPrecisionBadge } from '@/components/common/LocationPrecisionBadge';
import { SensitiveActionModal } from '@/components/common/SensitiveActionModal';
import { TrustStatusBadge } from '@/components/common/TrustStatusBadge';
import { GeoSignalMap } from '@/components/maps/GeoSignalMap';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { apiClient } from '@/lib/api/client';
import { formatDateTime } from '@/lib/format';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import { freshnessForTimestamp } from '@/lib/maps/provider';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useState } from 'react';

export default function DeviceDetailsPage() {
  const params = useParams<{ id: string }>();
  const deviceId = params.id;
  const [windowHours, setWindowHours] = useState('24');
  const [locateOpen, setLocateOpen] = useState(false);
  const [deprovisionOpen, setDeprovisionOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const state = useAsyncData(
    async () => {
      const [device, binding, trust, lastKnownLocation, locationHistory, geofenceEvents, geofences, accessHistory] = await Promise.all([
        apiClient.getDeviceById(deviceId),
        apiClient.getDeviceBinding(deviceId),
        apiClient.getDeviceTrustStatus(deviceId),
        apiClient.getLastKnownLocation(deviceId),
        apiClient.getLocationHistory(deviceId, Number(windowHours)),
        apiClient.getGeofenceEvents(deviceId, Number(windowHours)),
        apiClient.getGeofences(),
        apiClient.getDeviceAccessHistory(deviceId),
      ]);
      return { device, binding, trust, lastKnownLocation, locationHistory, geofenceEvents, geofences, accessHistory };
    },
    [deviceId, windowHours],
  );

  if (state.loading) {
    return (
      <div className="page">
        <LoadingCard />
      </div>
    );
  }

  if (state.error || !state.data) {
    return (
      <div className="page">
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{state.error ?? 'Device not found.'}</p>
          <div className="row" style={{ marginTop: 12 }}>
            <Button onClick={() => void state.refresh()}>Retry</Button>
            <Link href="/devices">Back to inventory</Link>
          </div>
        </Card>
      </div>
    );
  }

  const { device, binding, trust, lastKnownLocation, locationHistory, geofenceEvents, geofences, accessHistory } = state.data;
  const deviceGeofences = geofences.filter((geofence) => geofence.deviceId === device.id);

  const locateDevice = async (reason: string) => {
    setActionError(null);
    try {
      await apiClient.locateDevice(deviceId, reason);
      setLocateOpen(false);
      await state.refresh();
    } catch (errorValue) {
      setActionError(errorValue instanceof Error ? errorValue.message : 'Failed to locate device.');
      throw errorValue;
    }
  };

  const deprovisionDevice = async (reason: string) => {
    setActionError(null);
    try {
      await apiClient.deprovisionDevice(deviceId, reason);
      setDeprovisionOpen(false);
      await state.refresh();
    } catch (errorValue) {
      setActionError(errorValue instanceof Error ? errorValue.message : 'Failed to deprovision device.');
      throw errorValue;
    }
  };

  return (
    <div className="page container stack">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">{device.deviceName}</h1>
          <p className="page-subtitle">
            {device.model} • Device ID <span className="code">{device.id}</span>
          </p>
        </div>
        <Link href="/devices" className="text-muted">
          Back to inventory
        </Link>
      </div>

      <div className="grid-3">
        <Card>
          <p className="text-muted" style={{ margin: 0 }}>
            Managed state
          </p>
          <p style={{ margin: '8px 0', fontWeight: 700 }}>{device.status.replace('_', ' ')}</p>
          <Badge variant={device.online ? 'success' : 'warning'}>{device.online ? 'Online' : 'Offline'}</Badge>
          <p className="text-muted" style={{ marginTop: 10, fontSize: 13 }}>
            Last check-in: {formatDateTime(device.lastCheckInAt)}
          </p>
        </Card>

        <Card>
          <p className="text-muted" style={{ margin: 0 }}>
            Location quality
          </p>
          <div className="row" style={{ marginTop: 10 }}>
            <LocationPrecisionBadge precision={device.location.precision} />
            <ConfidenceBadge score={device.location.confidenceScore} />
          </div>
          <p className="text-muted" style={{ marginTop: 10, fontSize: 13 }}>
            Source: {device.location.sourceLabel}
          </p>
          {device.location.notes ? (
            <p className="text-muted" style={{ marginTop: 4, fontSize: 12 }}>
              {device.location.notes}
            </p>
          ) : null}
        </Card>

        <Card>
          <p className="text-muted" style={{ margin: 0 }}>
            Consent record
          </p>
          <p style={{ margin: '8px 0', fontWeight: 700 }}>{binding?.consentVersion ?? 'Not available'}</p>
          <p className="text-muted" style={{ margin: 0, fontSize: 13 }}>
            Captured: {binding ? formatDateTime(binding.consentCapturedAt) : 'Unknown'}
          </p>
          <p className="text-muted" style={{ marginTop: 6, fontSize: 12 }}>
            Ownership: {binding?.ownershipType?.replace('_', ' ') ?? 'Unknown'}
          </p>
        </Card>

        <Card>
          <p className="text-muted" style={{ margin: 0 }}>
            Battery
          </p>
          <p style={{ margin: '8px 0', fontWeight: 700 }}>{device.batteryLevel}%</p>
          <p className="text-muted" style={{ margin: 0, fontSize: 13 }}>
            Enrolled: {formatDateTime(device.enrollmentDate)}
          </p>
          <p className="text-muted" style={{ marginTop: 6, fontSize: 12 }}>
            Managed notice visible: {device.managedNoticeVisible ? 'Yes' : 'No'}
          </p>
        </Card>

        <Card>
          <p className="text-muted" style={{ margin: 0 }}>
            Advisory trust state
          </p>
          <div style={{ marginTop: 10 }}>
            <TrustStatusBadge trust={trust} />
          </div>
          <p className="text-muted" style={{ marginTop: 10, fontSize: 13 }}>
            {trust?.summary ?? 'No recent trust summary available yet.'}
          </p>
          {trust?.observedAt ? (
            <p className="text-muted" style={{ marginTop: 6, fontSize: 12 }}>
              Observed: {formatDateTime(trust.observedAt)}
            </p>
          ) : null}
        </Card>
      </div>

      <Card>
        <h2 style={{ marginTop: 0, marginBottom: 8 }}>Trust signal details</h2>
        <p className="page-subtitle">
          These are advisory indicators only. Suspicious signals do not by themselves prove compromise.
        </p>
        <div className="grid-2" style={{ marginTop: 16 }}>
          <div className="stack" style={{ gap: 8 }}>
            <p style={{ margin: 0 }}>
              Integrity status: <strong>{trust?.integrityStatus ?? 'Unknown'}</strong>
            </p>
            <p style={{ margin: 0 }}>
              Root suspicion placeholder: <strong>{trust?.rootSuspicion ? 'Observed' : 'Not observed'}</strong>
            </p>
            <p style={{ margin: 0 }}>
              Debug suspicion placeholder: <strong>{trust?.debugSuspicion ? 'Observed' : 'Not observed'}</strong>
            </p>
            <p style={{ margin: 0 }}>
              Mock-location heuristic: <strong>{trust?.mockLocationSuspicion ? 'Observed' : 'Not observed'}</strong>
            </p>
          </div>
          <div className="stack" style={{ gap: 8 }}>
            <p style={{ margin: 0, fontWeight: 700 }}>Reasons</p>
            {trust?.reasons?.length ? (
              trust.reasons.map((reason) => (
                <Badge key={reason} variant="neutral">
                  {reason}
                </Badge>
              ))
            ) : (
              <p className="text-muted" style={{ margin: 0 }}>
                No additional caution reasons captured.
              </p>
            )}
          </div>
        </div>
      </Card>

      {actionError ? (
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{actionError}</p>
        </Card>
      ) : null}

      <Card>
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ marginTop: 0, marginBottom: 8 }}>Policy-safe actions</h2>
            <p className="page-subtitle">
              Locate actions require a reason and are always audited. Deprovision removes this device from active managed workflows.
            </p>
          </div>
          <div className="row">
            <Button onClick={() => setLocateOpen(true)}>Locate now</Button>
            <Button variant="danger" onClick={() => setDeprovisionOpen(true)}>
              Deprovision
            </Button>
          </div>
        </div>
        <p className="warning-note" style={{ marginTop: 16, marginBottom: 0 }}>
          Approximate or stale results are shown as lower confidence and must not be presented as exact live recovery coordinates.
        </p>
      </Card>

      <Card>
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <div>
            <h2 style={{ marginTop: 0, marginBottom: 8 }}>Last Known Location & Route</h2>
            <p className="page-subtitle">
              History playback is time bounded. Approximate methods stay clearly separated from fused or GPS fixes.
            </p>
          </div>
          <Select
            label="Playback window"
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
            title="No mappable history for this device yet"
            points={
              lastKnownLocation
                ? [
                    {
                      id: 'last-known',
                      ...lastKnownLocation,
                      label: device.deviceName,
                      freshness: freshnessForTimestamp(lastKnownLocation.collectedAt, !device.online),
                    },
                  ]
                : []
            }
            routePoints={locationHistory.map((point) => ({
              ...point,
              freshness: freshnessForTimestamp(point.collectedAt),
            }))}
            geofences={deviceGeofences}
            height={340}
          />
        </div>

        <div className="grid-2" style={{ marginTop: 16 }}>
          <div className="stack" style={{ gap: 8 }}>
            <p style={{ margin: 0 }}>
              Latitude: <strong>{lastKnownLocation?.latitude ?? 'N/A'}</strong>
            </p>
            <p style={{ margin: 0 }}>
              Longitude: <strong>{lastKnownLocation?.longitude ?? 'N/A'}</strong>
            </p>
            <p style={{ margin: 0 }}>
              Accuracy: <strong>{lastKnownLocation?.accuracyMeters ?? 'Unknown'} meters</strong>
            </p>
            <p style={{ margin: 0 }}>
              Captured: <strong>{lastKnownLocation ? formatDateTime(lastKnownLocation.collectedAt) : 'N/A'}</strong>
            </p>
          </div>

          <div className="stack" style={{ gap: 8 }}>
            <p style={{ margin: 0, fontWeight: 700 }}>Geofence activity</p>
            {geofenceEvents.length ? (
              geofenceEvents.slice(-4).reverse().map((event) => (
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
                No recent geofence events in this playback window.
              </p>
            )}
          </div>
        </div>
      </Card>

      <Card>
        <h2 style={{ marginTop: 0, marginBottom: 8 }}>Access history</h2>
        <p className="page-subtitle">Owners and authorized admins can review who requested location or changed device access state.</p>
        <div className="stack" style={{ gap: 10, marginTop: 16 }}>
          {accessHistory.length ? (
            accessHistory.map((entry) => (
              <div key={entry.id} style={{ borderLeft: '2px solid var(--border)', paddingLeft: 12 }}>
                <p style={{ margin: 0, fontWeight: 700 }}>{entry.action.replaceAll('_', ' ')}</p>
                <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 13 }}>
                  {entry.actor} • {formatDateTime(entry.occurredAt)}
                </p>
                {entry.reason ? (
                  <p style={{ margin: '6px 0 0' }}>
                    Reason: <strong>{entry.reason}</strong>
                  </p>
                ) : null}
                {entry.result ? (
                  <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
                    Result: {entry.result}
                  </p>
                ) : null}
              </div>
            ))
          ) : (
            <p className="text-muted" style={{ margin: 0 }}>
              No locate or deprovision activity has been recorded for this device yet.
            </p>
          )}
        </div>
      </Card>

      <SensitiveActionModal
        open={locateOpen}
        title="Locate device"
        description="Explain why this lookup is necessary. The reason, actor, timestamp, device, and result will be written to the audit trail."
        confirmLabel="Run locate"
        onCancel={() => setLocateOpen(false)}
        onConfirm={locateDevice}
      />

      <SensitiveActionModal
        open={deprovisionOpen}
        title="Deprovision device"
        description="Explain why management should end. This action removes active locate permissions and records an immutable audit event."
        confirmLabel="Deprovision device"
        danger
        onCancel={() => setDeprovisionOpen(false)}
        onConfirm={deprovisionDevice}
      />
    </div>
  );
}
