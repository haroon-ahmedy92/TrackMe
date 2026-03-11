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

export interface ApiClient {
  login(payload: LoginRequest): Promise<LoginResponse>;
  getDevices(): Promise<DeviceRecord[]>;
  getDeviceById(deviceId: string): Promise<DeviceRecord>;
  getIncidents(): Promise<IncidentRecord[]>;
  getIncidentTimeline(incidentId: string): Promise<IncidentTimelineEvent[]>;
  markDeviceLost(deviceId: string, reason: string): Promise<void>;
  confirmDeviceStolen(incidentId: string, reason: string): Promise<void>;
  recoverIncident(incidentId: string, reason: string): Promise<void>;
  getGeofences(): Promise<GeofenceRecord[]>;
  upsertGeofence(geofence: Omit<GeofenceRecord, 'id' | 'createdAt'> & { id?: string }): Promise<GeofenceRecord>;
  deleteGeofence(geofenceId: string, reason: string): Promise<void>;
  getAuditLogs(): Promise<AuditLogRecord[]>;
  getRemoteActions(): Promise<RemoteActionRecord[]>;
  approveRemoteAction(actionId: string, reason: string): Promise<void>;
  rejectRemoteAction(actionId: string, reason: string): Promise<void>;
  getSettings(): Promise<PlatformSettings>;
  updateRetentionPolicy(
    policy: PlatformSettings['retentionPolicy'],
    reason: string,
  ): Promise<PlatformSettings['retentionPolicy']>;
}
