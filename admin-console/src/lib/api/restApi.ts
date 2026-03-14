import { httpClient } from '@/lib/api/httpClient';
import type { ApiClient } from '@/lib/api/types';
import { authStorage } from '@/lib/auth/storage';
import type {
  AuditLogRecord,
  CaseActionRecord,
  CaseAttachmentRecord,
  CaseEvidenceChainRecord,
  CaseEvidenceEntryRecord,
  CaseNoteRecord,
  DeviceClusterRecord,
  DeviceRecord,
  EvidenceExportRecord,
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

const toCaseNote = (payload: {
  note_id: string;
  incident_id: string;
  author_sub: string;
  body: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}): CaseNoteRecord => ({
  id: payload.note_id,
  incidentId: payload.incident_id,
  author: payload.author_sub,
  body: payload.body,
  pinned: payload.is_pinned,
  createdAt: payload.created_at,
  updatedAt: payload.updated_at,
});

const toCaseAttachment = (payload: {
  attachment_id: string;
  incident_id: string;
  uploaded_by_sub: string;
  file_name: string;
  media_type: string;
  byte_size: number;
  sha256?: string | null;
  description?: string | null;
  storage_key?: string | null;
  created_at: string;
}): CaseAttachmentRecord => ({
  id: payload.attachment_id,
  incidentId: payload.incident_id,
  uploadedBy: payload.uploaded_by_sub,
  fileName: payload.file_name,
  mediaType: payload.media_type,
  byteSize: payload.byte_size,
  sha256: payload.sha256 ?? undefined,
  description: payload.description ?? undefined,
  storageKey: payload.storage_key ?? undefined,
  createdAt: payload.created_at,
});

const toEvidenceExport = (payload: {
  export_id: string;
  incident_id: string;
  requested_by_sub: string;
  format: 'json' | 'pdf';
  status: 'generated' | 'failed';
  reason: string;
  redact_fields: string[];
  summary: Record<string, string | number | boolean | null>;
  download_placeholder?: string | null;
  created_at: string;
  generated_at?: string | null;
}): EvidenceExportRecord => ({
  id: payload.export_id,
  incidentId: payload.incident_id,
  requestedBy: payload.requested_by_sub,
  format: payload.format,
  status: payload.status,
  reason: payload.reason,
  redactFields: payload.redact_fields,
  summary: payload.summary,
  downloadPlaceholder: payload.download_placeholder ?? undefined,
  createdAt: payload.created_at,
  generatedAt: payload.generated_at ?? undefined,
});

const toCaseEvidenceEntry = (payload: {
  entry_id: string;
  kind: CaseEvidenceEntryRecord['kind'];
  title: string;
  summary: string;
  occurred_at: string;
  actor_sub?: string | null;
  mutable: boolean;
  data: Record<string, string | number | boolean | null>;
}): CaseEvidenceEntryRecord => ({
  id: payload.entry_id,
  kind: payload.kind,
  title: payload.title,
  summary: payload.summary,
  occurredAt: payload.occurred_at,
  actor: payload.actor_sub ?? undefined,
  mutable: payload.mutable,
  data: payload.data,
});

const toCaseAction = (payload: {
  remote_action_id: string;
  action_kind: CaseActionRecord['actionKind'];
  state: CaseActionRecord['state'];
  reason: string;
  requested_by_sub: string;
  requested_at: string;
  sent_at?: string | null;
  delivered_at?: string | null;
  acked_at?: string | null;
  failed_at?: string | null;
  last_error?: string | null;
}): CaseActionRecord => ({
  id: payload.remote_action_id,
  actionKind: payload.action_kind,
  state: payload.state,
  reason: payload.reason,
  requestedBy: payload.requested_by_sub,
  requestedAt: payload.requested_at,
  sentAt: payload.sent_at ?? undefined,
  deliveredAt: payload.delivered_at ?? undefined,
  ackedAt: payload.acked_at ?? undefined,
  failedAt: payload.failed_at ?? undefined,
  lastError: payload.last_error ?? undefined,
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

  getCaseEvidenceChain: async (incidentId: string, redactFields = []) => {
    const query = redactFields.map((field) => `redact_fields=${encodeURIComponent(field)}`).join('&');
    const payload = await httpClient.get<{
      incident: {
        incident_id: string;
        ticket_reference: string;
        state: string;
        recovery_message?: string | null;
      };
      actions_taken: Array<{
        remote_action_id: string;
        action_kind: CaseActionRecord['actionKind'];
        state: CaseActionRecord['state'];
        reason: string;
        requested_by_sub: string;
        requested_at: string;
        sent_at?: string | null;
        delivered_at?: string | null;
        acked_at?: string | null;
        failed_at?: string | null;
        last_error?: string | null;
      }>;
      notes: Array<{
        note_id: string;
        incident_id: string;
        author_sub: string;
        body: string;
        is_pinned: boolean;
        created_at: string;
        updated_at: string;
      }>;
      attachments: Array<{
        attachment_id: string;
        incident_id: string;
        uploaded_by_sub: string;
        file_name: string;
        media_type: string;
        byte_size: number;
        sha256?: string | null;
        description?: string | null;
        storage_key?: string | null;
        created_at: string;
      }>;
      exports: Array<{
        export_id: string;
        incident_id: string;
        requested_by_sub: string;
        format: 'json' | 'pdf';
        status: 'generated' | 'failed';
        reason: string;
        redact_fields: string[];
        summary: Record<string, string | number | boolean | null>;
        download_placeholder?: string | null;
        created_at: string;
        generated_at?: string | null;
      }>;
      entries: Array<{
        entry_id: string;
        kind: CaseEvidenceEntryRecord['kind'];
        title: string;
        summary: string;
        occurred_at: string;
        actor_sub?: string | null;
        mutable: boolean;
        data: Record<string, string | number | boolean | null>;
      }>;
    }>(`/platform/cases/${incidentId}/evidence-chain?org_id=${encodeURIComponent(orgId())}${query ? `&${query}` : ''}`);
    return {
      incidentId: payload.incident.incident_id,
      incidentState: payload.incident.state as CaseEvidenceChainRecord['incidentState'],
      ticketReference: payload.incident.ticket_reference,
      recoveryMessage: payload.incident.recovery_message,
      actionsTaken: payload.actions_taken.map(toCaseAction),
      notes: payload.notes.map(toCaseNote),
      attachments: payload.attachments.map(toCaseAttachment),
      exports: payload.exports.map(toEvidenceExport),
      entries: payload.entries.map(toCaseEvidenceEntry),
    };
  },

  addCaseNote: async (incidentId, payload) => {
    const note = await httpClient.post<{
      note_id: string;
      incident_id: string;
      author_sub: string;
      body: string;
      is_pinned: boolean;
      created_at: string;
      updated_at: string;
    }>(`/platform/cases/${incidentId}/notes`, {
      org_id: orgId(),
      body: payload.body,
      is_pinned: payload.pinned ?? false,
    });
    return toCaseNote(note);
  },

  updateCaseNote: async (incidentId, noteId, payload) => {
    const note = await httpClient.put<{
      note_id: string;
      incident_id: string;
      author_sub: string;
      body: string;
      is_pinned: boolean;
      created_at: string;
      updated_at: string;
    }>(`/platform/cases/${incidentId}/notes/${noteId}`, {
      org_id: orgId(),
      body: payload.body,
      is_pinned: payload.pinned ?? false,
    });
    return toCaseNote(note);
  },

  addCaseAttachment: async (incidentId, payload) => {
    const attachment = await httpClient.post<{
      attachment_id: string;
      incident_id: string;
      uploaded_by_sub: string;
      file_name: string;
      media_type: string;
      byte_size: number;
      sha256?: string | null;
      description?: string | null;
      storage_key?: string | null;
      created_at: string;
    }>(`/platform/cases/${incidentId}/attachments`, {
      org_id: orgId(),
      file_name: payload.fileName,
      media_type: payload.mediaType,
      byte_size: payload.byteSize,
      sha256: payload.sha256,
      description: payload.description,
    });
    return toCaseAttachment(attachment);
  },

  requestEvidenceExport: async (incidentId, payload) => {
    const exportRecord = await httpClient.post<{
      export_id: string;
      incident_id: string;
      requested_by_sub: string;
      format: 'json' | 'pdf';
      status: 'generated' | 'failed';
      reason: string;
      redact_fields: string[];
      summary: Record<string, string | number | boolean | null>;
      download_placeholder?: string | null;
      created_at: string;
      generated_at?: string | null;
    }>(`/platform/cases/${incidentId}/exports`, {
      org_id: orgId(),
      format: payload.format,
      reason: payload.reason,
      redact_fields: payload.redactFields,
    });
    return toEvidenceExport(exportRecord);
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
