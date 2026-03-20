import type {
  AccessHistoryRecord,
  AuditLogRecord,
  CaseAttachmentRecord,
  CaseEvidenceChainRecord,
  CaseNoteRecord,
  DeviceClusterRecord,
  DeviceRecord,
  EvidenceShareRecord,
  EvidenceExportRecord,
  GeofenceRecord,
  GeofenceEventRecord,
  IncidentFilters,
  IncidentRecord,
  IncidentRouteRecord,
  IncidentTimelineEvent,
  LoginRequest,
  LoginResponse,
  LocationHistoryPoint,
  LocationSnapshot,
  OwnershipBindingRecord,
  PlatformSettings,
  DeviceTrustRecord,
  RemoteActionRecord,
} from '@/types/models';

export interface ApiClient {
  login(payload: LoginRequest): Promise<LoginResponse>;
  getDevices(): Promise<DeviceRecord[]>;
  getDeviceById(deviceId: string): Promise<DeviceRecord>;
  getDeviceBinding(deviceId: string): Promise<OwnershipBindingRecord | null>;
  getDeviceTrustStatus(deviceId: string): Promise<DeviceTrustRecord | null>;
  getLastKnownLocation(deviceId: string): Promise<LocationSnapshot | null>;
  locateDevice(deviceId: string, reason: string): Promise<LocationSnapshot | null>;
  getDeviceAccessHistory(deviceId: string): Promise<AccessHistoryRecord[]>;
  getLocationHistory(deviceId: string, windowHours?: number): Promise<LocationHistoryPoint[]>;
  getDeviceClusters(windowHours?: number, cellSizeMeters?: number): Promise<DeviceClusterRecord[]>;
  getIncidents(filters?: IncidentFilters): Promise<IncidentRecord[]>;
  assignIncident(incidentId: string, payload: { operatorSub: string; reason: string }): Promise<IncidentRecord>;
  getIncidentTimeline(incidentId: string): Promise<IncidentTimelineEvent[]>;
  getIncidentRoute(incidentId: string, windowHours?: number): Promise<IncidentRouteRecord>;
  getCaseEvidenceChain(incidentId: string, redactFields?: string[]): Promise<CaseEvidenceChainRecord>;
  addCaseNote(incidentId: string, payload: { body: string; pinned?: boolean }): Promise<CaseNoteRecord>;
  updateCaseNote(incidentId: string, noteId: string, payload: { body: string; pinned?: boolean }): Promise<CaseNoteRecord>;
  addCaseAttachment(
    incidentId: string,
    payload: { fileName: string; mediaType: string; byteSize: number; sha256?: string; description?: string },
  ): Promise<CaseAttachmentRecord>;
  requestEvidenceExport(
    incidentId: string,
    payload: { format: 'csv' | 'json' | 'pdf'; reason: string; redactFields: string[] },
  ): Promise<EvidenceExportRecord>;
  shareEvidenceExport(
    incidentId: string,
    exportId: string,
    payload: { recipientLabel: string; reason: string },
  ): Promise<EvidenceShareRecord>;
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
  submitAbuseReport(payload: { category: string; description: string; contactEmail?: string; deviceId?: string }): Promise<void>;
  deprovisionDevice(deviceId: string, reason: string): Promise<void>;
}
