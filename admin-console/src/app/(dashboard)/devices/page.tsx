'use client';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { LoadingCard } from '@/components/common/LoadingCard';
import { LocationPrecisionBadge } from '@/components/common/LocationPrecisionBadge';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { apiClient } from '@/lib/api/client';
import { formatDateTime } from '@/lib/format';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import type { DeviceRecord } from '@/types/models';
import Link from 'next/link';

const statusVariant = (device: DeviceRecord) => {
  if (device.status === 'lost_mode') {
    return 'warning';
  }
  if (device.status === 'protected') {
    return 'success';
  }
  return 'neutral';
};

export default function DevicesPage() {
  const { data: devices, loading, error, refresh } = useAsyncData(() => apiClient.getDevices(), []);

  if (loading) {
    return (
      <div className="page">
        <LoadingCard />
      </div>
    );
  }

  if (error || !devices) {
    return (
      <div className="page">
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{error ?? 'Failed to load device inventory.'}</p>
          <Button onClick={() => void refresh()} style={{ marginTop: 12 }}>
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="page container stack">
      <div>
        <h1 className="page-title">Device Inventory</h1>
        <p className="page-subtitle">Only organization-owned or explicitly enrolled devices are listed.</p>
      </div>

      <Card>
        <DataTable
          rows={devices}
          rowKey={(device) => device.id}
          columns={[
            {
              key: 'device',
              header: 'Device',
              cell: (device) => (
                <div className="stack" style={{ gap: 3 }}>
                  <Link href={`/devices/${device.id}`} style={{ fontWeight: 700 }}>
                    {device.deviceName}
                  </Link>
                  <span className="text-muted" style={{ fontSize: 12 }}>
                    {device.model} • {device.appVersion}
                  </span>
                </div>
              ),
            },
            {
              key: 'managed',
              header: 'Managed Status',
              cell: (device) => (
                <div className="stack" style={{ gap: 6 }}>
                  <Badge variant={statusVariant(device)}>{device.status.replace('_', ' ')}</Badge>
                  <span className="text-muted" style={{ fontSize: 12 }}>
                    {device.managedNoticeVisible ? 'Managed notice visible' : 'Notice missing'}
                  </span>
                </div>
              ),
            },
            {
              key: 'location',
              header: 'Last Location Quality',
              cell: (device) => (
                <div className="stack" style={{ gap: 6 }}>
                  <LocationPrecisionBadge precision={device.location.precision} />
                  <ConfidenceBadge score={device.location.confidenceScore} />
                </div>
              ),
            },
            {
              key: 'checkin',
              header: 'Last Check-in',
              cell: (device) => (
                <div className="stack" style={{ gap: 4 }}>
                  <span>{formatDateTime(device.lastCheckInAt)}</span>
                  <span className="text-muted" style={{ fontSize: 12 }}>
                    {device.online ? 'Online' : 'Offline'} • Battery {device.batteryLevel}%
                  </span>
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
