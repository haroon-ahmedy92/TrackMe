import { httpClient } from '@/lib/api/httpClient';
import type { ApiClient } from '@/lib/api/types';
import type {
  AuditLogRecord,
  DeviceRecord,
  GeofenceRecord,
  IncidentRecord,
  IncidentTimelineEvent,
  LoginRequest,
  LoginResponse,
  PlatformSettings,
  RemoteActionRecord,
} from '@/types/models';

// TODO: align endpoint paths and payloads with backend contracts as they stabilize.
export const restApiClient: ApiClient = {
  login: (payload: LoginRequest) => httpClient.post<LoginResponse>('/auth/login', payload),

  getDevices: () => httpClient.get<DeviceRecord[]>('/platform/devices'),

  getDeviceById: (deviceId: string) => httpClient.get<DeviceRecord>(`/platform/devices/${deviceId}`),

  getIncidents: () => httpClient.get<IncidentRecord[]>('/platform/incidents'),

  getIncidentTimeline: (incidentId: string) =>
    httpClient.get<IncidentTimelineEvent[]>(`/platform/incidents/${incidentId}/events`),

  markDeviceLost: (deviceId: string, reason: string) =>
    httpClient.post<void>(`/platform/devices/${deviceId}/mark-lost`, { reason }),

  confirmDeviceStolen: (incidentId: string, reason: string) =>
    httpClient.post<void>(`/platform/incidents/${incidentId}/confirm-stolen`, { reason }),

  recoverIncident: (incidentId: string, reason: string) =>
    httpClient.post<void>(`/platform/incidents/${incidentId}/recover`, { reason }),

  getGeofences: () => httpClient.get<GeofenceRecord[]>('/platform/geofences'),

  upsertGeofence: (geofence) =>
    geofence.id
      ? httpClient.put<GeofenceRecord>(`/platform/geofences/${geofence.id}`, geofence)
      : httpClient.post<GeofenceRecord>('/platform/geofences', geofence),

  deleteGeofence: (geofenceId: string, reason: string) =>
    httpClient.delete<void>(`/platform/geofences/${geofenceId}`, { reason }),

  getAuditLogs: () => httpClient.get<AuditLogRecord[]>('/platform/audit-logs'),

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
