'use client';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { LoadingCard } from '@/components/common/LoadingCard';
import { LocationPrecisionBadge } from '@/components/common/LocationPrecisionBadge';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { apiClient } from '@/lib/api/client';
import { formatDateTime } from '@/lib/format';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import { useMemo, useState } from 'react';

export default function MapPage() {
  const { data: devices, loading, error } = useAsyncData(() => apiClient.getDevices(), []);
  const [filter, setFilter] = useState<'all' | 'precise' | 'moderate' | 'approximate'>('all');

  const filtered = useMemo(() => {
    if (!devices) {
      return [];
    }
    if (filter === 'all') {
      return devices;
    }
    return devices.filter((device) => device.location.precision === filter);
  }, [devices, filter]);

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
          <p style={{ margin: 0, color: 'var(--danger)' }}>{error ?? 'Could not load map data.'}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="page container stack">
      <div>
        <h1 className="page-title">Map & Last Known Location</h1>
        <p className="page-subtitle">
          Confidence is shown with each marker. Approximate sources are clearly labeled and not exact recovery points.
        </p>
      </div>

      <Card>
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <Select
            label="Precision filter"
            value={filter}
            onChange={(event) => setFilter(event.target.value as typeof filter)}
            options={[
              { label: 'All', value: 'all' },
              { label: 'Precise', value: 'precise' },
              { label: 'Moderate', value: 'moderate' },
              { label: 'Approximate', value: 'approximate' },
            ]}
          />
          <Badge variant="neutral">{filtered.length} visible devices</Badge>
        </div>

        <div
          style={{
            marginTop: 12,
            borderRadius: 12,
            border: '1px dashed var(--border)',
            minHeight: 220,
            padding: 14,
            background: 'linear-gradient(120deg, color-mix(in srgb, var(--primary) 7%, transparent), transparent 45%)',
          }}
        >
          <p style={{ margin: 0, fontWeight: 700 }}>Map renderer placeholder</p>
          <p className="text-muted" style={{ marginTop: 6, fontSize: 13 }}>
            TODO: integrate map provider abstraction layer for Google Maps / Mapbox tiles and markers.
          </p>
          <p className="warning-note" style={{ marginTop: 12 }}>
            IP/network-derived location is approximate and may represent area-level context only.
          </p>
        </div>
      </Card>

      <div className="grid-2">
        {filtered.map((device) => (
          <Card key={device.id}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <p style={{ margin: 0, fontWeight: 700 }}>{device.deviceName}</p>
              <Badge variant={device.online ? 'success' : 'warning'}>{device.online ? 'Online' : 'Offline'}</Badge>
            </div>

            <div className="row" style={{ marginTop: 10 }}>
              <LocationPrecisionBadge precision={device.location.precision} />
              <ConfidenceBadge score={device.location.confidenceScore} />
            </div>

            <p className="text-muted" style={{ margin: '10px 0 0', fontSize: 13 }}>
              {device.location.latitude != null && device.location.longitude != null
                ? `${device.location.latitude.toFixed(5)}, ${device.location.longitude.toFixed(5)}`
                : 'Coordinates unavailable'}
            </p>
            <p className="text-muted" style={{ margin: '5px 0 0', fontSize: 12 }}>
              Source: {device.location.sourceLabel}
            </p>
            <p className="text-muted" style={{ margin: '5px 0 0', fontSize: 12 }}>
              Last update: {formatDateTime(device.location.collectedAt)}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
