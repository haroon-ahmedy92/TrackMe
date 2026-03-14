'use client';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { LoadingCard } from '@/components/common/LoadingCard';
import { LocationPrecisionBadge } from '@/components/common/LocationPrecisionBadge';
import { GeoSignalMap } from '@/components/maps/GeoSignalMap';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { apiClient } from '@/lib/api/client';
import { formatDateTime } from '@/lib/format';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useState } from 'react';

export default function DeviceDetailsPage() {
  const params = useParams<{ id: string }>();
  const deviceId = params.id;
  const [windowHours, setWindowHours] = useState('24');

  const state = useAsyncData(
    async () => {
      const [device, lastKnownLocation, locationHistory, geofenceEvents, geofences] = await Promise.all([
        apiClient.getDeviceById(deviceId),
        apiClient.getLastKnownLocation(deviceId),
        apiClient.getLocationHistory(deviceId, Number(windowHours)),
        apiClient.getGeofenceEvents(deviceId, Number(windowHours)),
        apiClient.getGeofences(),
      ]);
      return { device, lastKnownLocation, locationHistory, geofenceEvents, geofences };
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

  const { device, lastKnownLocation, locationHistory, geofenceEvents, geofences } = state.data;
  const deviceGeofences = geofences.filter((geofence) => geofence.deviceId === device.id);

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
      </div>

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
            points={lastKnownLocation ? [{ id: 'last-known', ...lastKnownLocation, label: device.deviceName }] : []}
            routePoints={locationHistory}
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
    </div>
  );
}
