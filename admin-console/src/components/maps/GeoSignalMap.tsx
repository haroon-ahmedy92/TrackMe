'use client';

import { Badge } from '@/components/ui/Badge';
import type { DeviceClusterRecord, GeofenceRecord, LocationHistoryPoint, LocationPrecision } from '@/types/models';
import { useMemo } from 'react';

type MappablePoint = Pick<
  LocationHistoryPoint,
  'id' | 'latitude' | 'longitude' | 'precision' | 'confidenceScore' | 'sourceLabel' | 'collectedAt' | 'isApproximate'
> & {
  label?: string;
};

interface GeoSignalMapProps {
  points?: MappablePoint[];
  routePoints?: MappablePoint[];
  geofences?: GeofenceRecord[];
  clusters?: DeviceClusterRecord[];
  height?: number;
  title?: string;
  subtitle?: string;
}

const PADDING = 36;

const precisionColor = (precision: LocationPrecision) => {
  if (precision === 'precise') return 'var(--precise)';
  if (precision === 'moderate') return 'var(--moderate)';
  return 'var(--approximate)';
};

const toPoint = (
  latitude: number,
  longitude: number,
  bounds: { minLat: number; maxLat: number; minLng: number; maxLng: number },
  width: number,
  height: number,
) => {
  const usableWidth = width - PADDING * 2;
  const usableHeight = height - PADDING * 2;
  const lngRange = Math.max(bounds.maxLng - bounds.minLng, 0.02);
  const latRange = Math.max(bounds.maxLat - bounds.minLat, 0.02);

  const x = PADDING + ((longitude - bounds.minLng) / lngRange) * usableWidth;
  const y = height - PADDING - ((latitude - bounds.minLat) / latRange) * usableHeight;
  return { x, y };
};

const metersToPixels = (
  meters: number,
  bounds: { minLat: number; maxLat: number; minLng: number; maxLng: number },
  width: number,
) => {
  const lngRange = Math.max(bounds.maxLng - bounds.minLng, 0.02);
  const metersPerDegree = 111_320;
  const pxPerDegree = (width - PADDING * 2) / lngRange;
  return Math.max(8, (meters / metersPerDegree) * pxPerDegree);
};

export function GeoSignalMap({
  points = [],
  routePoints = [],
  geofences = [],
  clusters = [],
  height = 320,
  title,
  subtitle,
}: GeoSignalMapProps) {
  const width = 920;
  const normalizedPoints = useMemo(
    () => points.filter((point) => point.latitude != null && point.longitude != null),
    [points],
  );
  const normalizedRoute = useMemo(
    () => routePoints.filter((point) => point.latitude != null && point.longitude != null),
    [routePoints],
  );

  const bounds = useMemo(() => {
    const latitudes = [
      ...normalizedPoints.map((point) => point.latitude as number),
      ...normalizedRoute.map((point) => point.latitude as number),
      ...geofences.map((geofence) => geofence.centerLat),
      ...clusters.map((cluster) => cluster.centerLat),
    ];
    const longitudes = [
      ...normalizedPoints.map((point) => point.longitude as number),
      ...normalizedRoute.map((point) => point.longitude as number),
      ...geofences.map((geofence) => geofence.centerLng),
      ...clusters.map((cluster) => cluster.centerLng),
    ];

    if (!latitudes.length || !longitudes.length) {
      return null;
    }

    const minLat = Math.min(...latitudes) - 0.015;
    const maxLat = Math.max(...latitudes) + 0.015;
    const minLng = Math.min(...longitudes) - 0.015;
    const maxLng = Math.max(...longitudes) + 0.015;
    return { minLat, maxLat, minLng, maxLng };
  }, [clusters, geofences, normalizedPoints, normalizedRoute]);

  if (!bounds) {
    return (
      <div
        style={{
          minHeight: height,
          borderRadius: 18,
          border: '1px dashed var(--border)',
          background:
            'linear-gradient(135deg, color-mix(in srgb, var(--primary) 10%, transparent), transparent 42%), var(--surface-muted)',
          padding: 20,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: 8,
        }}
      >
        <p style={{ margin: 0, fontWeight: 700 }}>{title ?? 'No map data yet'}</p>
        <p className="text-muted" style={{ margin: 0 }}>
          {subtitle ?? 'A map will appear after lawful check-ins, route points, or geofence coordinates are available.'}
        </p>
      </div>
    );
  }

  const routePath = normalizedRoute
    .map((point, index) => {
      const projected = toPoint(point.latitude as number, point.longitude as number, bounds, width, height);
      return `${index === 0 ? 'M' : 'L'} ${projected.x} ${projected.y}`;
    })
    .join(' ');

  return (
    <div className="stack" style={{ gap: 10 }}>
      <div
        style={{
          borderRadius: 20,
          border: '1px solid var(--border)',
          background:
            'radial-gradient(circle at top right, color-mix(in srgb, var(--primary) 14%, transparent), transparent 30%), linear-gradient(180deg, color-mix(in srgb, var(--surface-muted) 84%, transparent), var(--surface))',
          overflow: 'hidden',
        }}
      >
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height }}>
          <defs>
            <pattern id="grid" width="52" height="52" patternUnits="userSpaceOnUse">
              <path
                d="M 52 0 L 0 0 0 52"
                fill="none"
                stroke="color-mix(in srgb, var(--border) 55%, transparent)"
                strokeWidth="1"
              />
            </pattern>
          </defs>
          <rect x="0" y="0" width={width} height={height} fill="url(#grid)" />

          {geofences.map((geofence) => {
            const center = toPoint(geofence.centerLat, geofence.centerLng, bounds, width, height);
            const radius = metersToPixels(geofence.radiusMeters, bounds, width);
            return (
              <g key={geofence.id}>
                <circle
                  cx={center.x}
                  cy={center.y}
                  r={radius}
                  fill="color-mix(in srgb, var(--primary) 12%, transparent)"
                  stroke={geofence.active ? 'var(--primary)' : 'var(--text-muted)'}
                  strokeDasharray={geofence.active ? '0' : '8 6'}
                  strokeWidth="2"
                />
                <text
                  x={center.x}
                  y={Math.max(18, center.y - radius - 8)}
                  textAnchor="middle"
                  style={{ fill: 'var(--text)', fontSize: 12, fontWeight: 700 }}
                >
                  {geofence.name}
                </text>
              </g>
            );
          })}

          {routePath ? (
            <path
              d={routePath}
              fill="none"
              stroke="color-mix(in srgb, var(--primary) 80%, white 10%)"
              strokeWidth="3"
              strokeDasharray="0"
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity="0.8"
            />
          ) : null}

          {clusters.map((cluster) => {
            const center = toPoint(cluster.centerLat, cluster.centerLng, bounds, width, height);
            const radius = Math.min(28, 10 + cluster.deviceCount * 3);
            const hasApproximate = cluster.approximateCount > 0;
            return (
              <g key={cluster.id}>
                <circle
                  cx={center.x}
                  cy={center.y}
                  r={radius}
                  fill={hasApproximate ? 'color-mix(in srgb, var(--approximate) 30%, var(--surface))' : 'color-mix(in srgb, var(--primary) 22%, var(--surface))'}
                  stroke={hasApproximate ? 'var(--approximate)' : 'var(--primary)'}
                  strokeWidth="2.5"
                />
                <text
                  x={center.x}
                  y={center.y + 4}
                  textAnchor="middle"
                  style={{ fill: 'var(--text)', fontSize: 12, fontWeight: 800 }}
                >
                  {cluster.deviceCount}
                </text>
              </g>
            );
          })}

          {normalizedPoints.map((point) => {
            const projected = toPoint(point.latitude as number, point.longitude as number, bounds, width, height);
            const color = precisionColor(point.precision);
            return (
              <g key={point.id}>
                <circle
                  cx={projected.x}
                  cy={projected.y}
                  r={point.isApproximate ? 10 : 7}
                  fill={`color-mix(in srgb, ${color} 28%, var(--surface))`}
                  stroke={color}
                  strokeWidth="3"
                  strokeDasharray={point.isApproximate ? '5 4' : '0'}
                />
                <circle cx={projected.x} cy={projected.y} r="2.8" fill={color} />
              </g>
            );
          })}
        </svg>
      </div>

      <div className="row" style={{ justifyContent: 'space-between' }}>
        <div className="row">
          <Badge variant="precise">Precise</Badge>
          <Badge variant="moderate">Moderate</Badge>
          <Badge variant="approximate">Approximate</Badge>
        </div>
        <p className="text-muted" style={{ margin: 0, fontSize: 12 }}>
          Approximate IP or network-derived signals are shown with a visually distinct outline and should not be treated as exact recovery points.
        </p>
      </div>
    </div>
  );
}
