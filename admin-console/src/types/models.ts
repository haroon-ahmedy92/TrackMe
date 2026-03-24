export type LocationPrecision = 'precise' | 'moderate' | 'approximate';
export type EnrollmentType = 'owner_enrolled' | 'org_managed';
export type OwnershipType = 'single_user' | 'organization_owned';

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
export type DeviceTrustStatus = 'trusted' | 'caution' | 'unavailable';

export interface DeviceTrustRecord {
  status: DeviceTrustStatus;
  summary: string;
  reasons: string[];
  integrityStatus?: string;
  rootSuspicion: boolean;
  debugSuspicion: boolean;
  mockLocationSuspicion: boolean;
  trustedTelemetrySeen: boolean;
  observedAt?: string;
}

export interface OwnershipBindingRecord {
  id: string;
  orgId: string;
  deviceId: string;
  ownerSubject?: string;
  ownershipType: OwnershipType;
  proofKind: string;
  consentVersion: string;
  consentCapturedAt: string;
  isActive: boolean;
  createdAt: string;
  endedAt?: string;
}

export interface PairingTokenRecord {
  pairingTokenId: string;
  orgId: string;
  deviceId?: string;
  token: string;
  tokenHint: string;
  pairingUri: string;
  expiresAt: string;
}

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
  trust?: DeviceTrustRecord;
}

export interface IncidentRecord {
  id: string;
  orgId: string;
  deviceId: string;
  title: string;
  state: IncidentState;
  openedAt: string;
  updatedAt: string;
  ownerName: string;
  assignedOperator?: string;
  highFrequencyUntil?: string;
}

export interface IncidentFilters {
  tenantId?: string;
  state?: IncidentState | 'ALL';
  updatedFrom?: string;
  updatedTo?: string;
  assignedOperator?: string;
  search?: string;
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
  storageBackend?: string;
  storageKey?: string;
  downloadUrl?: string;
  createdAt: string;
}

export interface EvidenceExportRecord {
  id: string;
  incidentId: string;
  requestedBy: string;
  format: 'csv' | 'json' | 'pdf';
  status: 'generated' | 'failed' | 'pending_approval';
  reason: string;
  redactFields: string[];
  summary: Record<string, string | number | boolean | null>;
  downloadPlaceholder?: string;
  approvalRequestId?: string;
  policyReason?: string;
  createdAt: string;
  generatedAt?: string;
}

export interface EvidenceShareRecord {
  exportId: string;
  incidentId: string;
  recipientLabel: string;
  reason: string;
  sharedBy: string;
  sharedAt: string;
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
  incidentSummary?: Record<string, string | number | boolean | null>;
  locationTimeline: LocationHistoryPoint[];
  auditTrail: AuditLogRecord[];
  commandHistory: CaseActionRecord[];
  geofenceEvents: GeofenceEventRecord[];
  actionsTaken: CaseActionRecord[];
  notes: CaseNoteRecord[];
  attachments: CaseAttachmentRecord[];
  exports: EvidenceExportRecord[];
  externalShares: EvidenceShareRecord[];
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

export interface NotificationEventRecord {
  id: string;
  orgId: string;
  incidentId?: string;
  deviceId?: string;
  remoteActionId?: string;
  recipientSub?: string;
  channel: string;
  template: string;
  payload: Record<string, string | number | boolean | null>;
  status: string;
  providerMessageId?: string;
  errorMessage?: string;
  createdAt: string;
  sentAt?: string;
}

export interface AccessHistoryRecord {
  id: string;
  actor: string;
  action: string;
  occurredAt: string;
  reason?: string;
  result?: string;
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
  approvalRequestId?: string;
  requiredApprovals?: number;
  approvalCount?: number;
  policyReason?: string;
}

export interface RetentionPolicy {
  locationEventDays: number;
  auditLogDays: number;
  incidentEvidenceDays: number;
  locateReasonMinLength?: number;
  requireIncidentForLocate?: boolean;
  lockRequiresActiveIncident?: boolean;
  wipeRequiresPolicyApproval?: boolean;
  wipeRequiresConfirmedStolen?: boolean;
  highRiskActionsRequireTwoPerson?: boolean;
  evidenceExportRequiresPermission?: boolean;
}

export interface PrivacyDefaults {
  explicitConsentRequired: boolean;
  visibleAppRequired: boolean;
  backgroundLocationRequiresExplanation: boolean;
  ownerAccessHistoryVisible: boolean;
  approximateLocationsClearlyLabeled: boolean;
  shortRetentionDefault: boolean;
}

export interface PlatformSettings {
  orgId: string;
  timezone: string;
  defaultMapProvider: 'google' | 'mapbox';
  retentionPolicy: RetentionPolicy;
  privacyDefaults: PrivacyDefaults;
  updatedAt?: string;
  updatedBySub?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  accessToken: string;
  profile: UserProfile;
}
