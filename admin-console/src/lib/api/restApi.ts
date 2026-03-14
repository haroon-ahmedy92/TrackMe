import { httpClient } from '@/lib/api/httpClient';
import type { ApiClient } from '@/lib/api/types';
import { authStorage } from '@/lib/auth/storage';
import type {
  AuditLogRecord,
  DeviceClusterRecord,
  DeviceRecord,
  GeofenceRecord,
  GeofenceEventRecord,
  IncidentRecord,
  IncidentRouteRecord,
  IncidentTimelineEvent,
  LoginRequest,
  LoginResponse,
  LocationHistoryPoint,
  LocationSnapshot,
  PlatformSettings,
  RemoteActionRecord,
} from '@/types/models';

const orgId = () => authStorage.getProfile()?.tenantId ?? 'org-001';

const buildWindowQuery = (windowHours = 24) => {
  const endsAt = new Date();
  const startsAt = new Date(endsAt.getTime() - windowHours * 60 * 60 * 1000);
  return `starts_at=${encodeURIComponent(startsAt.toISOString())}&ends_at=${encodeURIComponent(endsAt.toISOString())}`;
};

const camelLocation = (payload: {
  event_id: string;
  device_id: string;
  captured_at: string;
  latitude: number | null;
  longitude: number | null;
  accuracy_meters: number | null;
  precision: 'precise' | 'moderate' | 'approximate';
  confidence_score: number;
  source_label: string;
  source_methods?: string[];
  is_ip_approximate?: boolean;
}) => ({
  id: payload.event_id,
  deviceId: payload.device_id,
  latitude: payload.latitude,
  longitude: payload.longitude,
  accuracyMeters: payload.accuracy_meters,
  precision: payload.precision,
  confidenceScore: payload.confidence_score,
  collectedAt: payload.captured_at,
  sourceLabel: payload.source_label,
  sourceMethods: payload.source_methods ?? [],
  isApproximate: payload.is_ip_approximate ?? payload.precision === 'approximate',
});

const toLocationSnapshot = (payload: ReturnType<typeof camelLocation>): LocationSnapshot => ({
  latitude: payload.latitude,
  longitude: payload.longitude,
  accuracyMeters: payload.accuracyMeters,
  precision: payload.precision,
  confidenceScore: payload.confidenceScore,
  collectedAt: payload.collectedAt,
  sourceLabel: payload.sourceLabel,
  sourceMethods: payload.sourceMethods,
  isApproximate: payload.isApproximate,
});

const toHistoryPoint = (payload: ReturnType<typeof camelLocation>): LocationHistoryPoint => payload;

const toGeofence = (payload: {
  geofence_id: string;
  device_id: string | null;
  name: string;
  center_latitude: number;
  center_longitude: number;
  radius_meters: number;
  is_enabled: boolean;
  created_at: string;
}): GeofenceRecord => ({
  id: payload.geofence_id,
  deviceId: payload.device_id ?? '',
  name: payload.name,
  centerLat: payload.center_latitude,
  centerLng: payload.center_longitude,
  radiusMeters: payload.radius_meters,
  active: payload.is_enabled,
  createdAt: payload.created_at,
});

const toGeofenceEvent = (payload: {
  geofence_event_id: string;
  geofence_id: string;
  geofence_name?: string | null;
  device_id: string;
  event_type: 'enter' | 'exit';
  precision: 'precise' | 'moderate' | 'approximate';
  confidence_score: number;
  alert_emitted: boolean;
  suppressed_reason?: string | null;
  triggered_at: string;
}): GeofenceEventRecord => ({
  id: payload.geofence_event_id,
  geofenceId: payload.geofence_id,
  geofenceName: payload.geofence_name ?? 'Geofence',
  deviceId: payload.device_id,
  eventType: payload.event_type,
  precision: payload.precision,
  confidenceScore: payload.confidence_score,
  alertEmitted: payload.alert_emitted,
  suppressedReason: payload.suppressed_reason ?? undefined,
  triggeredAt: payload.triggered_at,
});

const toCluster = (payload: {
  cluster_id: string;
  center_latitude: number;
  center_longitude: number;
  device_count: number;
  approximate_count: number;
  precise_count: number;
  moderate_count: number;
  latest_captured_at?: string | null;
  device_ids: string[];
}): DeviceClusterRecord => ({
  id: payload.cluster_id,
  centerLat: payload.center_latitude,
  centerLng: payload.center_longitude,
  deviceCount: payload.device_count,
  approximateCount: payload.approximate_count,
  preciseCount: payload.precise_count,
  moderateCount: payload.moderate_count,
  latestCapturedAt: payload.latest_captured_at ?? undefined,
  deviceIds: payload.device_ids,
});

export const restApiClient: ApiClient = {
  login: (payload: LoginRequest) => httpClient.post<LoginResponse>('/auth/login', payload),

  getDevices: () => httpClient.get<DeviceRecord[]>(`/platform/devices?org_id=${encodeURIComponent(orgId())}`),

  getDeviceById: async (deviceId: string) => {
    const devices = await httpClient.get<DeviceRecord[]>(`/platform/devices?org_id=${encodeURIComponent(orgId())}`);
    const device = devices.find((entry) => entry.id === deviceId);
    if (!device) {
      throw new Error('Device not found');
    }
    return device;
  },

  getLastKnownLocation: async (deviceId: string) => {
    const payload = await httpClient.get<{
      event_id: string;
      device_id: string;
      captured_at: string;
      latitude: number | null;
      longitude: number | null;
      accuracy_meters: number | null;
      precision: 'precise' | 'moderate' | 'approximate';
      confidence_score: number;
      source_label: string;
      source_methods?: string[];
      is_ip_approximate?: boolean;
    } | null>(`/platform/devices/${deviceId}/last-location?org_id=${encodeURIComponent(orgId())}`);
    return payload ? toLocationSnapshot(camelLocation(payload)) : null;
  },

  getLocationHistory: async (deviceId: string, windowHours = 24) => {
    const payload = await httpClient.get<
      Array<{
        event_id: string;
        device_id: string;
        captured_at: string;
        latitude: number | null;
        longitude: number | null;
        accuracy_meters: number | null;
        precision: 'precise' | 'moderate' | 'approximate';
        confidence_score: number;
        source_label: string;
        source_methods?: string[];
        is_ip_approximate?: boolean;
      }>
    >(`/platform/devices/${deviceId}/location-history?org_id=${encodeURIComponent(orgId())}&${buildWindowQuery(windowHours)}`);
    return payload.map((entry) => toHistoryPoint(camelLocation(entry)));
  },

  getDeviceClusters: async (windowHours = 24, cellSizeMeters = 10000) => {
    const payload = await httpClient.get<
      Array<{
        cluster_id: string;
        center_latitude: number;
        center_longitude: number;
        device_count: number;
        approximate_count: number;
        precise_count: number;
        moderate_count: number;
        latest_captured_at?: string | null;
        device_ids: string[];
      }>
    >(
      `/platform/devices/clusters?org_id=${encodeURIComponent(orgId())}&${buildWindowQuery(windowHours)}&cell_size_meters=${cellSizeMeters}`,
    );
    return payload.map(toCluster);
  },

  getIncidents: () => httpClient.get<IncidentRecord[]>(`/platform/incidents?org_id=${encodeURIComponent(orgId())}`),

  getIncidentTimeline: (incidentId: string) =>
    httpClient.get<IncidentTimelineEvent[]>(`/platform/cases/${incidentId}/events?org_id=${encodeURIComponent(orgId())}`),

  getIncidentRoute: async (incidentId: string, windowHours = 24) => {
    const payload = await httpClient.get<{
      incident_id: string;
      device_id: string;
      started_at: string;
      ended_at: string;
      points: Array<{
        event_id: string;
        device_id: string;
        captured_at: string;
        latitude: number | null;
        longitude: number | null;
        accuracy_meters: number | null;
        precision: 'precise' | 'moderate' | 'approximate';
        confidence_score: number;
        source_label: string;
        source_methods?: string[];
        is_ip_approximate?: boolean;
      }>;
      geofence_events: Array<{
        geofence_event_id: string;
        geofence_id: string;
        geofence_name?: string | null;
        device_id: string;
        event_type: 'enter' | 'exit';
        precision: 'precise' | 'moderate' | 'approximate';
        confidence_score: number;
        alert_emitted: boolean;
        suppressed_reason?: string | null;
        triggered_at: string;
      }>;
    }>(`/platform/cases/${incidentId}/route?org_id=${encodeURIComponent(orgId())}&${buildWindowQuery(windowHours)}`);

    return {
      incidentId: payload.incident_id,
      deviceId: payload.device_id,
      startedAt: payload.started_at,
      endedAt: payload.ended_at,
      points: payload.points.map((entry) => toHistoryPoint(camelLocation(entry))),
      geofenceEvents: payload.geofence_events.map(toGeofenceEvent),
    };
  },

  markDeviceLost: (deviceId: string, reason: string) => httpClient.post<void>(`/platform/devices/${deviceId}/mark-lost`, { reason }),

  confirmDeviceStolen: (incidentId: string, reason: string) =>
    httpClient.post<void>(`/platform/incidents/${incidentId}/confirm-stolen`, { reason }),

  recoverIncident: (incidentId: string, reason: string) =>
    httpClient.post<void>(`/platform/incidents/${incidentId}/recover`, { reason }),

  getGeofences: async () => {
    const payload = await httpClient.get<
      Array<{
        geofence_id: string;
        device_id: string | null;
        name: string;
        center_latitude: number;
        center_longitude: number;
        radius_meters: number;
        is_enabled: boolean;
        created_at: string;
      }>
    >(`/platform/geofences?org_id=${encodeURIComponent(orgId())}`);
    return payload.map(toGeofence);
  },

  getGeofenceEvents: async (deviceId: string, windowHours = 24) => {
    const payload = await httpClient.get<
      Array<{
        geofence_event_id: string;
        geofence_id: string;
        geofence_name?: string | null;
        device_id: string;
        event_type: 'enter' | 'exit';
        precision: 'precise' | 'moderate' | 'approximate';
        confidence_score: number;
        alert_emitted: boolean;
        suppressed_reason?: string | null;
        triggered_at: string;
      }>
    >(`/platform/devices/${deviceId}/geofence-events?org_id=${encodeURIComponent(orgId())}&${buildWindowQuery(windowHours)}`);
    return payload.map(toGeofenceEvent);
  },

  upsertGeofence: async (geofence) => {
    const body = {
      org_id: orgId(),
      device_id: geofence.deviceId || null,
      name: geofence.name,
      center_latitude: geofence.centerLat,
      center_longitude: geofence.centerLng,
      radius_meters: geofence.radiusMeters,
      is_enabled: geofence.active,
    };
    const payload = geofence.id
      ? await httpClient.put<{
          geofence_id: string;
          device_id: string | null;
          name: string;
          center_latitude: number;
          center_longitude: number;
          radius_meters: number;
          is_enabled: boolean;
          created_at: string;
        }>(`/platform/geofences/${geofence.id}`, body)
      : await httpClient.post<{
          geofence_id: string;
          device_id: string | null;
          name: string;
          center_latitude: number;
          center_longitude: number;
          radius_meters: number;
          is_enabled: boolean;
          created_at: string;
        }>('/platform/geofences', body);
    return toGeofence(payload);
  },

  deleteGeofence: (geofenceId: string, reason: string) =>
    httpClient.delete<void>(
      `/platform/geofences/${geofenceId}?org_id=${encodeURIComponent(orgId())}&reason=${encodeURIComponent(reason)}`,
    ),

  getAuditLogs: () => httpClient.get<AuditLogRecord[]>(`/platform/audit-logs?org_id=${encodeURIComponent(orgId())}`),

  getRemoteActions: () => httpClient.get<RemoteActionRecord[]>('/platform/remote-actions'),

  approveRemoteAction: (actionId: string, reason: string) =>
    httpClient.post<void>(`/platform/remote-actions/${actionId}/approve`, { reason }),

  rejectRemoteAction: (actionId: string, reason: string) =>
    httpClient.post<void>(`/platform/remote-actions/${actionId}/reject`, { reason }),

  getSettings: () => httpClient.get<PlatformSettings>('/platform/settings'),

  updateRetentionPolicy: (policy, reason) =>
    httpClient.put<PlatformSettings['retentionPolicy']>('/platform/settings/retention-policy', {
      ...policy,
      reason,
    }),
};
