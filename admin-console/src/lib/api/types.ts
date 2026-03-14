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

export interface ApiClient {
  login(payload: LoginRequest): Promise<LoginResponse>;
  getDevices(): Promise<DeviceRecord[]>;
  getDeviceById(deviceId: string): Promise<DeviceRecord>;
  getLastKnownLocation(deviceId: string): Promise<LocationSnapshot | null>;
  getLocationHistory(deviceId: string, windowHours?: number): Promise<LocationHistoryPoint[]>;
  getDeviceClusters(windowHours?: number, cellSizeMeters?: number): Promise<DeviceClusterRecord[]>;
  getIncidents(): Promise<IncidentRecord[]>;
  getIncidentTimeline(incidentId: string): Promise<IncidentTimelineEvent[]>;
  getIncidentRoute(incidentId: string, windowHours?: number): Promise<IncidentRouteRecord>;
  markDeviceLost(deviceId: string, reason: string): Promise<void>;
  confirmDeviceStolen(incidentId: string, reason: string): Promise<void>;
  recoverIncident(incidentId: string, reason: string): Promise<void>;
  getGeofences(): Promise<GeofenceRecord[]>;
  getGeofenceEvents(deviceId: string, windowHours?: number): Promise<GeofenceEventRecord[]>;
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
