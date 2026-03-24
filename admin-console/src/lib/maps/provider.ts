import type { DeviceClusterRecord, GeofenceRecord, LocationPrecision } from '@/types/models';

export type SupportedMapProvider = 'google' | 'mapbox';
export type MapFreshness = 'recent' | 'stale' | 'offline';

export interface MapPoint {
  id: string;
  latitude: number;
  longitude: number;
  precision: LocationPrecision;
  isApproximate?: boolean;
  collectedAt?: string;
  freshness?: MapFreshness;
  label?: string;
}

export interface StaticMapRequest {
  points?: MapPoint[];
  routePoints?: MapPoint[];
  geofences?: GeofenceRecord[];
  clusters?: DeviceClusterRecord[];
  width: number;
  height: number;
}

export interface MapRenderResult {
  provider: SupportedMapProvider;
  staticMapUrl: string | null;
  interactiveUrl: string | null;
  configured: boolean;
}

const defaultProvider = (process.env.NEXT_PUBLIC_MAP_PROVIDER ?? 'google').toLowerCase() as SupportedMapProvider;
const googleMapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_STATIC_MAPS_API_KEY ?? '';
const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN ?? '';
const mapboxUsername = process.env.NEXT_PUBLIC_MAPBOX_USERNAME ?? 'mapbox';
const mapboxStyleId = process.env.NEXT_PUBLIC_MAPBOX_STYLE_ID ?? 'streets-v12';

const colorByPoint = (point: MapPoint) => {
  if (point.freshness === 'offline') return '#64748b';
  if (point.freshness === 'stale') return '#c2410c';
  if (point.isApproximate || point.precision === 'approximate') return '#6b7280';
  if (point.precision === 'moderate') return '#a16207';
  return '#0f766e';
};

const markerLabel = (point: MapPoint) => {
  if (point.freshness === 'offline') return 'O';
  if (point.freshness === 'stale') return 'S';
  if (point.isApproximate || point.precision === 'approximate') return 'A';
  if (point.precision === 'moderate') return 'M';
  return 'P';
};

const approximateCircle = (lat: number, lng: number, radiusMeters: number, points = 24) => {
  const earthRadius = 6_371_000;
  const angularDistance = radiusMeters / earthRadius;
  const latRad = (lat * Math.PI) / 180;
  const lngRad = (lng * Math.PI) / 180;

  return Array.from({ length: points + 1 }, (_, index) => {
    const bearing = (2 * Math.PI * index) / points;
    const pointLat = Math.asin(
      Math.sin(latRad) * Math.cos(angularDistance) +
        Math.cos(latRad) * Math.sin(angularDistance) * Math.cos(bearing),
    );
    const pointLng =
      lngRad +
      Math.atan2(
        Math.sin(bearing) * Math.sin(angularDistance) * Math.cos(latRad),
        Math.cos(angularDistance) - Math.sin(latRad) * Math.sin(pointLat),
      );
    return {
      latitude: (pointLat * 180) / Math.PI,
      longitude: (pointLng * 180) / Math.PI,
    };
  });
};

const googleColor = (hex: string) => `0x${hex.replace('#', '')}`;

function buildGoogleMap(request: StaticMapRequest): MapRenderResult {
  const points = request.points ?? [];
  const routePoints = request.routePoints ?? [];
  const geofences = request.geofences ?? [];
  const allCoordinates = [
    ...points.map((point) => `${point.latitude},${point.longitude}`),
    ...routePoints.map((point) => `${point.latitude},${point.longitude}`),
    ...geofences.map((geofence) => `${geofence.centerLat},${geofence.centerLng}`),
  ];

  if (!allCoordinates.length || !googleMapsApiKey) {
    return {
      provider: 'google',
      configured: Boolean(googleMapsApiKey),
      staticMapUrl: null,
      interactiveUrl: null,
    };
  }

  const searchParams = new URLSearchParams({
    size: `${Math.min(request.width, 640)}x${Math.min(request.height, 640)}`,
    scale: '2',
    key: googleMapsApiKey,
  });

  allCoordinates.forEach((coordinate) => searchParams.append('visible', coordinate));

  if (routePoints.length > 1) {
    searchParams.append(
      'path',
      `color:${googleColor('#006f8b')}AA|weight:4|${routePoints.map((point) => `${point.latitude},${point.longitude}`).join('|')}`,
    );
  }

  geofences.forEach((geofence) => {
    const polygon = approximateCircle(geofence.centerLat, geofence.centerLng, geofence.radiusMeters)
      .map((point) => `${point.latitude},${point.longitude}`)
      .join('|');
    searchParams.append(
      'path',
      `fillcolor:${googleColor('#15a4c3')}22|color:${googleColor(geofence.active ? '#006f8b' : '#64748b')}AA|weight:2|${polygon}`,
    );
  });

  points.forEach((point) => {
    searchParams.append(
      'markers',
      `size:mid|color:${googleColor(colorByPoint(point))}|label:${markerLabel(point)}|${point.latitude},${point.longitude}`,
    );
  });

  const staticMapUrl = `https://maps.googleapis.com/maps/api/staticmap?${searchParams.toString()}`;
  const primary = points[0] ?? routePoints[0];
  const interactiveUrl = primary
    ? `https://www.google.com/maps/search/?api=1&query=${primary.latitude},${primary.longitude}`
    : 'https://www.google.com/maps';
  return {
    provider: 'google',
    configured: true,
    staticMapUrl,
    interactiveUrl,
  };
}

function buildMapboxMap(request: StaticMapRequest): MapRenderResult {
  const points = request.points ?? [];
  const routePoints = request.routePoints ?? [];
  const geofences = request.geofences ?? [];
  const clusters = request.clusters ?? [];

  if ((!points.length && !routePoints.length && !geofences.length && !clusters.length) || !mapboxToken) {
    return {
      provider: 'mapbox',
      configured: Boolean(mapboxToken),
      staticMapUrl: null,
      interactiveUrl: null,
    };
  }

  const features: Array<Record<string, unknown>> = [];

  if (routePoints.length > 1) {
    features.push({
      type: 'Feature',
      properties: { stroke: '#006f8b', 'stroke-width': 4, 'stroke-opacity': 0.85 },
      geometry: {
        type: 'LineString',
        coordinates: routePoints.map((point) => [point.longitude, point.latitude]),
      },
    });
  }

  geofences.forEach((geofence) => {
    features.push({
      type: 'Feature',
      properties: {
        stroke: geofence.active ? '#006f8b' : '#64748b',
        'stroke-width': 2,
        'fill-opacity': 0.08,
        fill: '#15a4c3',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [approximateCircle(geofence.centerLat, geofence.centerLng, geofence.radiusMeters).map((point) => [point.longitude, point.latitude])],
      },
    });
  });

  points.forEach((point) => {
    features.push({
      type: 'Feature',
      properties: {
        'marker-color': colorByPoint(point),
        'marker-size': point.isApproximate ? 'small' : 'medium',
        title: point.label ?? markerLabel(point),
      },
      geometry: {
        type: 'Point',
        coordinates: [point.longitude, point.latitude],
      },
    });
  });

  clusters.forEach((cluster) => {
    features.push({
      type: 'Feature',
      properties: {
        'marker-color': cluster.approximateCount > 0 ? '#6b7280' : '#0f766e',
        'marker-size': 'large',
        title: `${cluster.deviceCount} devices`,
      },
      geometry: {
        type: 'Point',
        coordinates: [cluster.centerLng, cluster.centerLat],
      },
    });
  });

  const overlay = encodeURIComponent(JSON.stringify({ type: 'FeatureCollection', features }));
  const staticMapUrl = `https://api.mapbox.com/styles/v1/${mapboxUsername}/${mapboxStyleId}/static/geojson(${overlay})/auto/${Math.min(request.width, 1280)}x${Math.min(request.height, 1280)}?padding=48&access_token=${encodeURIComponent(mapboxToken)}`;
  return {
    provider: 'mapbox',
    configured: true,
    staticMapUrl,
    interactiveUrl: null,
  };
}

export function buildStaticMap(request: StaticMapRequest): MapRenderResult {
  return defaultProvider === 'mapbox' ? buildMapboxMap(request) : buildGoogleMap(request);
}

export function freshnessForTimestamp(collectedAt?: string, offline = false): MapFreshness {
  if (offline) return 'offline';
  if (!collectedAt) return 'stale';
  const ageMs = Date.now() - new Date(collectedAt).getTime();
  return ageMs > 30 * 60 * 1000 ? 'stale' : 'recent';
}
