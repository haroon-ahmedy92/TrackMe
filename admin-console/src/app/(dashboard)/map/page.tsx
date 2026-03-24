'use client';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { LoadingCard } from '@/components/common/LoadingCard';
import { LocationPrecisionBadge } from '@/components/common/LocationPrecisionBadge';
import { GeoSignalMap } from '@/components/maps/GeoSignalMap';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { apiClient } from '@/lib/api/client';
import { formatDateTime } from '@/lib/format';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import { freshnessForTimestamp } from '@/lib/maps/provider';
import type { LocationPrecision } from '@/types/models';
import { useMemo, useState } from 'react';

export default function MapPage() {
  const [filter, setFilter] = useState<'all' | LocationPrecision>('all');
  const [windowHours, setWindowHours] = useState('24');

  const mapState = useAsyncData(
    async () => {
      const [devices, geofences, clusters] = await Promise.all([
        apiClient.getDevices(),
        apiClient.getGeofences(),
        apiClient.getDeviceClusters(Number(windowHours)),
      ]);
      return { devices, geofences, clusters };
    },
    [windowHours],
  );

  const devices = useMemo(() => mapState.data?.devices ?? [], [mapState.data?.devices]);
  const filteredDevices = useMemo(() => {
    if (filter === 'all') {
      return devices;
    }
    return devices.filter((device) => device.location.precision === filter);
  }, [devices, filter]);

  if (mapState.loading) {
    return (
      <div className="page">
        <LoadingCard />
      </div>
    );
  }

  if (mapState.error || !mapState.data) {
    return (
      <div className="page">
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{mapState.error ?? 'Could not load map data.'}</p>
        </Card>
      </div>
    );
  }

  const mappablePoints = filteredDevices
    .filter((device) => device.location.latitude != null && device.location.longitude != null)
    .map((device) => ({
      id: device.id,
      label: device.deviceName,
      latitude: device.location.latitude,
      longitude: device.location.longitude,
      precision: device.location.precision,
      confidenceScore: device.location.confidenceScore,
      sourceLabel: device.location.sourceLabel,
      collectedAt: device.location.collectedAt,
      isApproximate: device.location.isApproximate,
      freshness: freshnessForTimestamp(device.location.collectedAt, !device.online),
    }));

  return (
    <div className="page container stack">
      <div>
        <h1 className="page-title">Map & Last Known Location</h1>
        <p className="page-subtitle">
          Device markers are grouped for the org view, and approximate sources stay visually distinct from GPS or fused results.
        </p>
      </div>

      <Card>
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <div className="row">
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
            <Select
              label="History window"
              value={windowHours}
              onChange={(event) => setWindowHours(event.target.value)}
              options={[
                { label: '6 hours', value: '6' },
                { label: '24 hours', value: '24' },
                { label: '72 hours', value: '72' },
              ]}
            />
          </div>
          <div className="row">
            <Badge variant="neutral">{filteredDevices.length} devices</Badge>
            <Badge variant="neutral">{mapState.data.clusters.length} clusters</Badge>
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <GeoSignalMap
            title="Org dashboard clusters"
            subtitle="No recent lawful check-ins are available for the selected time window."
            points={mappablePoints}
            clusters={mapState.data.clusters}
            geofences={mapState.data.geofences}
            height={360}
          />
        </div>
      </Card>

      <div className="grid-2">
        {filteredDevices.map((device) => (
          <Card key={device.id}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <p style={{ margin: 0, fontWeight: 700 }}>{device.deviceName}</p>
              <Badge variant={device.online ? 'success' : 'warning'}>{device.online ? 'Online' : 'Offline'}</Badge>
            </div>

            <div className="row" style={{ marginTop: 10 }}>
              <LocationPrecisionBadge precision={device.location.precision} />
              <ConfidenceBadge score={device.location.confidenceScore} />
            </div>

            <div style={{ marginTop: 12 }}>
              <p style={{ margin: 0, fontWeight: 600 }}>
                {device.location.latitude != null && device.location.longitude != null
                  ? `${device.location.latitude.toFixed(5)}, ${device.location.longitude.toFixed(5)}`
                  : 'Coordinates unavailable'}
              </p>
              <p className="text-muted" style={{ margin: '6px 0 0', fontSize: 13 }}>
                {device.location.sourceLabel}
              </p>
              <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
                Last update: {formatDateTime(device.location.collectedAt)}
              </p>
              {device.location.isApproximate ? (
                <p className="warning-note" style={{ marginTop: 10 }}>
                  Approximate location only. Use this as broad context, not an exact recovery point.
                </p>
              ) : null}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
