import type {
  AuditLogRecord,
  DeviceRecord,
  GeofenceRecord,
  IncidentRecord,
  IncidentTimelineEvent,
  PlatformSettings,
  RemoteActionRecord,
} from '@/types/models';

export const mockDevices: DeviceRecord[] = [
  {
    id: 'dev-001',
    tenantId: 'org-001',
    deviceName: 'Warehouse Scanner A1',
    model: 'Samsung XCover',
    platform: 'android',
    appVersion: '1.0.0',
    status: 'protected',
    incidentState: 'NORMAL',
    online: true,
    batteryLevel: 76,
    lastCheckInAt: '2026-03-10T08:30:00Z',
    enrollmentDate: '2026-01-20T09:00:00Z',
    managedNoticeVisible: true,
    location: {
      latitude: -6.7924,
      longitude: 39.2083,
      accuracyMeters: 14,
      precision: 'precise',
      confidenceScore: 92,
      collectedAt: '2026-03-10T08:29:40Z',
      sourceLabel: 'Fused GPS + geofence',
      notes: 'High confidence from recent GNSS fix.'
    },
  },
  {
    id: 'dev-002',
    tenantId: 'org-001',
    deviceName: 'Field Tablet K3',
    model: 'Lenovo Tab M10',
    platform: 'android',
    appVersion: '1.0.0',
    status: 'lost_mode',
    incidentState: 'SUSPECTED_LOST',
    online: false,
    batteryLevel: 21,
    lastCheckInAt: '2026-03-09T22:10:00Z',
    enrollmentDate: '2026-02-01T11:15:00Z',
    managedNoticeVisible: true,
    location: {
      latitude: -3.3869,
      longitude: 36.683,
      accuracyMeters: 180,
      precision: 'moderate',
      confidenceScore: 58,
      collectedAt: '2026-03-09T22:05:00Z',
      sourceLabel: 'Last known fused location + network context',
      notes: 'Signal age increased due to intermittent connectivity.'
    },
  },
  {
    id: 'dev-003',
    tenantId: 'org-001',
    deviceName: 'Delivery Phone C7',
    model: 'Tecno Spark',
    platform: 'android',
    appVersion: '1.0.0',
    status: 'protected',
    incidentState: 'NORMAL',
    online: false,
    batteryLevel: 49,
    lastCheckInAt: '2026-03-08T16:41:00Z',
    enrollmentDate: '2026-02-15T10:30:00Z',
    managedNoticeVisible: true,
    location: {
      latitude: -2.5164,
      longitude: 32.9175,
      accuracyMeters: null,
      precision: 'approximate',
      confidenceScore: 24,
      collectedAt: '2026-03-08T16:40:00Z',
      sourceLabel: 'Backend IP geolocation fallback',
      notes: 'Approximate district-level signal only. Not exact recovery location.'
    },
  },
];

export const mockIncidents: IncidentRecord[] = [
  {
    id: 'inc-102',
    deviceId: 'dev-002',
    title: 'Field Tablet K3 suspected lost',
    state: 'SUSPECTED_LOST',
    openedAt: '2026-03-09T21:55:00Z',
    updatedAt: '2026-03-10T07:00:00Z',
    ownerName: 'Regional Ops Team',
    highFrequencyUntil: '2026-03-10T13:55:00Z',
  },
];

export const mockIncidentTimeline: IncidentTimelineEvent[] = [
  {
    id: 'evt-1',
    incidentId: 'inc-102',
    createdAt: '2026-03-09T21:55:00Z',
    actor: 'ops.admin@org.tz',
    eventType: 'INCIDENT_CREATED',
    reason: 'Device not returned after shift handover.',
  },
  {
    id: 'evt-2',
    incidentId: 'inc-102',
    createdAt: '2026-03-09T22:00:00Z',
    actor: 'system',
    eventType: 'LOST_MODE_ENABLED',
    reason: 'Automatic workflow after admin confirmation.',
    details: 'High-frequency reporting enabled for 16 hours.'
  },
  {
    id: 'evt-3',
    incidentId: 'inc-102',
    createdAt: '2026-03-10T07:00:00Z',
    actor: 'security.lead@org.tz',
    eventType: 'NOTIFICATION_ESCALATED',
    reason: 'No successful check-in for 9 hours.',
  },
];

export const mockGeofences: GeofenceRecord[] = [
  {
    id: 'geo-1',
    name: 'Dar HQ',
    deviceId: 'dev-001',
    centerLat: -6.7924,
    centerLng: 39.2083,
    radiusMeters: 300,
    active: true,
    createdAt: '2026-02-03T09:20:00Z',
  },
  {
    id: 'geo-2',
    name: 'Arusha Depot',
    deviceId: 'dev-002',
    centerLat: -3.3869,
    centerLng: 36.683,
    radiusMeters: 500,
    active: true,
    createdAt: '2026-02-10T11:00:00Z',
  },
];

export const mockAuditLogs: AuditLogRecord[] = [
  {
    id: 'aud-1',
    createdAt: '2026-03-10T07:00:00Z',
    actor: 'security.lead@org.tz',
    action: 'ESCALATE_NOTIFICATION',
    targetType: 'incident',
    targetId: 'inc-102',
    reason: 'No check-in after lost mode activation.',
  },
  {
    id: 'aud-2',
    createdAt: '2026-03-09T22:00:00Z',
    actor: 'ops.admin@org.tz',
    action: 'ENABLE_LOST_MODE',
    targetType: 'device',
    targetId: 'dev-002',
    reason: 'User-reported loss event validated by supervisor.',
  },
  {
    id: 'aud-3',
    createdAt: '2026-03-08T15:10:00Z',
    actor: 'compliance.admin@org.tz',
    action: 'UPDATE_RETENTION_POLICY',
    targetType: 'settings',
    targetId: 'retention-policy',
    reason: 'Align with org records policy.',
    metadata: { locationDays: 90, auditDays: 365 },
  },
];

export const mockRemoteActions: RemoteActionRecord[] = [
  {
    id: 'act-1',
    deviceId: 'dev-002',
    deviceName: 'Field Tablet K3',
    type: 'LOCK',
    status: 'PENDING',
    requestedBy: 'ops.admin@org.tz',
    requestedAt: '2026-03-10T06:45:00Z',
    reason: 'Prevent unauthorized access while recovery team investigates.',
    deviceOnline: false,
    lastCheckInAt: '2026-03-09T22:10:00Z',
  },
  {
    id: 'act-2',
    deviceId: 'dev-002',
    deviceName: 'Field Tablet K3',
    type: 'SHOW_RECOVERY_MESSAGE',
    status: 'DISPATCHED',
    requestedBy: 'security.lead@org.tz',
    requestedAt: '2026-03-09T22:03:00Z',
    reason: 'Display return contact instructions on lock screen.',
    deviceOnline: false,
    lastCheckInAt: '2026-03-09T22:10:00Z',
  },
];

export const mockSettings: PlatformSettings = {
  timezone: 'Africa/Dar_es_Salaam',
  defaultMapProvider: 'google',
  retentionPolicy: {
    locationEventDays: 90,
    auditLogDays: 365,
    incidentEvidenceDays: 180,
  },
};
