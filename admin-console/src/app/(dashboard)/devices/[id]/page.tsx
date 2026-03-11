'use client';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { LoadingCard } from '@/components/common/LoadingCard';
import { LocationPrecisionBadge } from '@/components/common/LocationPrecisionBadge';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { apiClient } from '@/lib/api/client';
import { formatDateTime } from '@/lib/format';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import Link from 'next/link';
import { useParams } from 'next/navigation';

export default function DeviceDetailsPage() {
  const params = useParams<{ id: string }>();
  const deviceId = params.id;

  const { data: device, loading, error, refresh } = useAsyncData(
    () => apiClient.getDeviceById(deviceId),
    [deviceId],
  );

  if (loading) {
    return (
      <div className="page">
        <LoadingCard />
      </div>
    );
  }

  if (error || !device) {
    return (
      <div className="page">
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{error ?? 'Device not found.'}</p>
          <div className="row" style={{ marginTop: 12 }}>
            <Button onClick={() => void refresh()}>Retry</Button>
            <Link href="/devices">Back to inventory</Link>
          </div>
        </Card>
      </div>
    );
  }

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
          <p className="text-muted" style={{ margin: 0 }}>Managed state</p>
          <p style={{ margin: '8px 0', fontWeight: 700 }}>{device.status.replace('_', ' ')}</p>
          <Badge variant={device.online ? 'success' : 'warning'}>{device.online ? 'Online' : 'Offline'}</Badge>
          <p className="text-muted" style={{ marginTop: 10, fontSize: 13 }}>
            Last check-in: {formatDateTime(device.lastCheckInAt)}
          </p>
        </Card>

        <Card>
          <p className="text-muted" style={{ margin: 0 }}>Location quality</p>
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
          <p className="text-muted" style={{ margin: 0 }}>Battery</p>
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
        <h2 style={{ marginTop: 0, marginBottom: 8 }}>Last Known Location</h2>
        <p className="page-subtitle">
          Approximate methods (for example backend IP geolocation) are never treated as exact recovery points.
        </p>

        <div className="grid-2" style={{ marginTop: 14 }}>
          <div className="stack" style={{ gap: 8 }}>
            <p style={{ margin: 0 }}>
              Latitude: <strong>{device.location.latitude ?? 'N/A'}</strong>
            </p>
            <p style={{ margin: 0 }}>
              Longitude: <strong>{device.location.longitude ?? 'N/A'}</strong>
            </p>
            <p style={{ margin: 0 }}>
              Accuracy: <strong>{device.location.accuracyMeters ?? 'Unknown'} meters</strong>
            </p>
            <p style={{ margin: 0 }}>
              Captured: <strong>{formatDateTime(device.location.collectedAt)}</strong>
            </p>
          </div>

          <div
            style={{
              borderRadius: 12,
              border: '1px solid var(--border)',
              background: 'var(--surface-muted)',
              minHeight: 180,
              padding: 12,
            }}
          >
            <p style={{ margin: 0, fontWeight: 700 }}>Map provider placeholder</p>
            <p className="text-muted" style={{ marginTop: 6, fontSize: 13 }}>
              TODO: render interactive map through provider abstraction (Google Maps / Mapbox).
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
