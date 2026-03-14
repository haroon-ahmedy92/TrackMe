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
  sourceMethods?: string[];
  isApproximate?: boolean;
  geofenceTransition?: string | null;
  notes?: string;
}

export interface LocationHistoryPoint extends LocationSnapshot {
  id: string;
  deviceId: string;
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

export interface CaseNoteRecord {
  id: string;
  incidentId: string;
  author: string;
  body: string;
  pinned: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CaseAttachmentRecord {
  id: string;
  incidentId: string;
  uploadedBy: string;
  fileName: string;
  mediaType: string;
  byteSize: number;
  sha256?: string;
  description?: string;
  storageKey?: string;
  createdAt: string;
}

export interface EvidenceExportRecord {
  id: string;
  incidentId: string;
  requestedBy: string;
  format: 'json' | 'pdf';
  status: 'generated' | 'failed';
  reason: string;
  redactFields: string[];
  summary: Record<string, string | number | boolean | null>;
  downloadPlaceholder?: string;
  createdAt: string;
  generatedAt?: string;
}

export interface CaseEvidenceEntryRecord {
  id: string;
  kind: 'incident_event' | 'location' | 'geofence' | 'remote_action' | 'attachment' | 'note' | 'audit';
  title: string;
  summary: string;
  occurredAt: string;
  actor?: string | null;
  mutable: boolean;
  data: Record<string, string | number | boolean | null>;
}

export interface GeofenceRecord {
  id: string;
  name: string;
  deviceId: string;
  deviceName?: string;
  centerLat: number;
  centerLng: number;
  radiusMeters: number;
  active: boolean;
  createdAt: string;
}

export interface GeofenceEventRecord {
  id: string;
  geofenceId: string;
  geofenceName: string;
  deviceId: string;
  eventType: 'enter' | 'exit';
  precision: LocationPrecision;
  confidenceScore: number;
  alertEmitted: boolean;
  suppressedReason?: string;
  triggeredAt: string;
}

export interface DeviceClusterRecord {
  id: string;
  centerLat: number;
  centerLng: number;
  deviceCount: number;
  approximateCount: number;
  preciseCount: number;
  moderateCount: number;
  latestCapturedAt?: string;
  deviceIds: string[];
}

export interface IncidentRouteRecord {
  incidentId: string;
  deviceId: string;
  startedAt: string;
  endedAt: string;
  points: LocationHistoryPoint[];
  geofenceEvents: GeofenceEventRecord[];
}

export interface CaseActionRecord {
  id: string;
  actionKind: 'enter_lost_mode' | 'display_recovery_message' | 'lock' | 'wipe';
  state: 'pending' | 'sent' | 'delivered' | 'acked' | 'failed' | 'expired';
  reason: string;
  requestedBy: string;
  requestedAt: string;
  sentAt?: string;
  deliveredAt?: string;
  ackedAt?: string;
  failedAt?: string;
  lastError?: string;
}

export interface CaseEvidenceChainRecord {
  incidentId: string;
  incidentState: IncidentState;
  ticketReference: string;
  recoveryMessage?: string | null;
  actionsTaken: CaseActionRecord[];
  notes: CaseNoteRecord[];
  attachments: CaseAttachmentRecord[];
  exports: EvidenceExportRecord[];
  entries: CaseEvidenceEntryRecord[];
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
