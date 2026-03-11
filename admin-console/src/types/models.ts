export type LocationPrecision = 'precise' | 'moderate' | 'approximate';

export type DeviceStatus = 'protected' | 'unenrolled' | 'lost_mode';

export type IncidentState =
  | 'NORMAL'
  | 'SUSPECTED_LOST'
  | 'CONFIRMED_STOLEN'
  | 'RECOVERED'
  | 'WIPED'
  | 'DECOMMISSIONED';

export type RemoteActionType = 'LOCK' | 'WIPE' | 'PLAY_SOUND' | 'SHOW_RECOVERY_MESSAGE';

export type RemoteActionStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'DISPATCHED' | 'EXECUTED' | 'FAILED';

export type Role = 'owner' | 'admin' | 'security';

export interface UserProfile {
  id: string;
  fullName: string;
  email: string;
  role: Role;
  tenantId: string;
}

export interface LocationSnapshot {
  latitude: number | null;
  longitude: number | null;
  accuracyMeters: number | null;
  precision: LocationPrecision;
  confidenceScore: number;
  collectedAt: string;
  sourceLabel: string;
  notes?: string;
}

export interface DeviceRecord {
  id: string;
  tenantId: string;
  deviceName: string;
  model: string;
  platform: 'android';
  appVersion: string;
  status: DeviceStatus;
  incidentState: IncidentState;
  online: boolean;
  batteryLevel: number;
  lastCheckInAt: string;
  enrollmentDate: string;
  managedNoticeVisible: boolean;
  location: LocationSnapshot;
}

export interface IncidentRecord {
  id: string;
  deviceId: string;
  title: string;
  state: IncidentState;
  openedAt: string;
  updatedAt: string;
  ownerName: string;
  highFrequencyUntil?: string;
}

export interface IncidentTimelineEvent {
  id: string;
  incidentId: string;
  createdAt: string;
  actor: string;
  eventType: string;
  reason: string;
  details?: string;
}

export interface GeofenceRecord {
  id: string;
  name: string;
  deviceId: string;
  centerLat: number;
  centerLng: number;
  radiusMeters: number;
  active: boolean;
  createdAt: string;
}

export interface AuditLogRecord {
  id: string;
  createdAt: string;
  actor: string;
  action: string;
  targetType: string;
  targetId: string;
  reason?: string;
  metadata?: Record<string, string | number | boolean | null>;
}

export interface RemoteActionRecord {
  id: string;
  deviceId: string;
  deviceName: string;
  type: RemoteActionType;
  status: RemoteActionStatus;
  requestedBy: string;
  requestedAt: string;
  reason: string;
  deviceOnline: boolean;
  lastCheckInAt: string;
}

export interface RetentionPolicy {
  locationEventDays: number;
  auditLogDays: number;
  incidentEvidenceDays: number;
}

export interface PlatformSettings {
  timezone: string;
  defaultMapProvider: 'google' | 'mapbox';
  retentionPolicy: RetentionPolicy;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  accessToken: string;
  profile: UserProfile;
}
