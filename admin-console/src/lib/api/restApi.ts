import { httpClient } from '@/lib/api/httpClient';
import type { ApiClient } from '@/lib/api/types';
import { authStorage } from '@/lib/auth/storage';
import type {
  AccessHistoryRecord,
  AuditLogRecord,
  CaseActionRecord,
  CaseAttachmentRecord,
  CaseEvidenceChainRecord,
  CaseEvidenceEntryRecord,
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
  format: 'csv' | 'json' | 'pdf';
  status: 'generated' | 'failed' | 'pending_approval';
  reason: string;
  redact_fields: string[];
  summary: Record<string, string | number | boolean | null>;
  download_placeholder?: string | null;
  approval_request_id?: string | null;
  policy_reason?: string | null;
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
  approvalRequestId: payload.approval_request_id ?? undefined,
  policyReason: payload.policy_reason ?? undefined,
  createdAt: payload.created_at,
  generatedAt: payload.generated_at ?? undefined,
});

const toEvidenceShare = (payload: {
  export_id: string;
  incident_id: string;
  recipient_label: string;
  reason: string;
  shared_by_sub: string;
  shared_at: string;
}): EvidenceShareRecord => ({
  exportId: payload.export_id,
  incidentId: payload.incident_id,
  recipientLabel: payload.recipient_label,
  reason: payload.reason,
  sharedBy: payload.shared_by_sub,
  sharedAt: payload.shared_at,
});

const toIncident = (payload: {
  incident_id: string;
  org_id: string;
  device_id: string;
  ticket_reference: string;
  state: IncidentRecord['state'];
  assigned_operator_sub?: string | null;
  recovery_message?: string | null;
  lost_mode_until?: string | null;
  created_at: string;
  updated_at: string;
}): IncidentRecord => ({
  id: payload.incident_id,
  orgId: payload.org_id,
  deviceId: payload.device_id,
  title: `Case ${payload.ticket_reference}`,
  state: payload.state,
  openedAt: payload.created_at,
  updatedAt: payload.updated_at,
  ownerName: payload.assigned_operator_sub ?? 'Unassigned',
  assignedOperator: payload.assigned_operator_sub ?? undefined,
  highFrequencyUntil: payload.lost_mode_until ?? undefined,
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

const toOwnershipBinding = (payload: {
  ownership_binding_id: string;
  org_id: string;
  device_id: string;
  owner_subject?: string | null;
  ownership_type: 'single_user' | 'organization_owned';
  proof_kind: string;
  consent_version: string;
  consent_captured_at: string;
  is_active: boolean;
  created_at: string;
  ended_at?: string | null;
}): OwnershipBindingRecord => ({
  id: payload.ownership_binding_id,
  orgId: payload.org_id,
  deviceId: payload.device_id,
  ownerSubject: payload.owner_subject ?? undefined,
  ownershipType: payload.ownership_type,
  proofKind: payload.proof_kind,
  consentVersion: payload.consent_version,
  consentCapturedAt: payload.consent_captured_at,
  isActive: payload.is_active,
  createdAt: payload.created_at,
  endedAt: payload.ended_at ?? undefined,
});

const toAccessHistory = (payload: {
  audit_log_id: string;
  actor_sub: string;
  action: string;
  occurred_at: string;
  reason?: string | null;
  result?: string | null;
  metadata?: Record<string, string | number | boolean | null>;
}): AccessHistoryRecord => ({
  id: payload.audit_log_id,
  actor: payload.actor_sub,
  action: payload.action,
  occurredAt: payload.occurred_at,
  reason: payload.reason ?? undefined,
  result: payload.result ?? undefined,
  metadata: payload.metadata ?? {},
});

const toPlatformSettings = (payload: {
  org_id: string;
  timezone: string;
  default_map_provider: 'google' | 'mapbox';
  retention_policy: {
    location_event_days: number;
    audit_log_days: number;
    incident_evidence_days: number;
    locate_reason_min_length?: number;
    require_incident_for_locate?: boolean;
    lock_requires_active_incident?: boolean;
    wipe_requires_policy_approval?: boolean;
    wipe_requires_confirmed_stolen?: boolean;
    high_risk_actions_require_two_person?: boolean;
    evidence_export_requires_permission?: boolean;
  };
  privacy_defaults: {
    explicit_consent_required: boolean;
    visible_app_required: boolean;
    background_location_requires_explanation: boolean;
    owner_access_history_visible: boolean;
    approximate_locations_clearly_labeled: boolean;
    short_retention_default: boolean;
  };
  updated_at?: string | null;
  updated_by_sub?: string | null;
}): PlatformSettings => ({
  orgId: payload.org_id,
  timezone: payload.timezone,
  defaultMapProvider: payload.default_map_provider,
  retentionPolicy: {
    locationEventDays: payload.retention_policy.location_event_days,
    auditLogDays: payload.retention_policy.audit_log_days,
    incidentEvidenceDays: payload.retention_policy.incident_evidence_days,
    locateReasonMinLength: payload.retention_policy.locate_reason_min_length,
    requireIncidentForLocate: payload.retention_policy.require_incident_for_locate,
    lockRequiresActiveIncident: payload.retention_policy.lock_requires_active_incident,
    wipeRequiresPolicyApproval: payload.retention_policy.wipe_requires_policy_approval,
    wipeRequiresConfirmedStolen: payload.retention_policy.wipe_requires_confirmed_stolen,
    highRiskActionsRequireTwoPerson: payload.retention_policy.high_risk_actions_require_two_person,
    evidenceExportRequiresPermission: payload.retention_policy.evidence_export_requires_permission,
  },
  privacyDefaults: {
    explicitConsentRequired: payload.privacy_defaults.explicit_consent_required,
    visibleAppRequired: payload.privacy_defaults.visible_app_required,
    backgroundLocationRequiresExplanation: payload.privacy_defaults.background_location_requires_explanation,
    ownerAccessHistoryVisible: payload.privacy_defaults.owner_access_history_visible,
    approximateLocationsClearlyLabeled: payload.privacy_defaults.approximate_locations_clearly_labeled,
    shortRetentionDefault: payload.privacy_defaults.short_retention_default,
  },
  updatedAt: payload.updated_at ?? undefined,
  updatedBySub: payload.updated_by_sub ?? undefined,
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

  getDeviceBinding: async (deviceId: string) => {
    const payload = await httpClient.get<{
      ownership_binding_id: string;
      org_id: string;
      device_id: string;
      owner_subject?: string | null;
      ownership_type: 'single_user' | 'organization_owned';
      proof_kind: string;
      consent_version: string;
      consent_captured_at: string;
      is_active: boolean;
      created_at: string;
      ended_at?: string | null;
    }>(`/ownership/devices/${deviceId}/binding?org_id=${encodeURIComponent(orgId())}`);
    return payload ? toOwnershipBinding(payload) : null;
  },

  getDeviceTrustStatus: async (deviceId: string) => {
    const payload = await httpClient.get<{
      device_id: string;
      org_id: string;
      status: 'trusted' | 'caution' | 'unavailable';
      summary: string;
      reasons: string[];
      integrity_status?: string | null;
      root_suspicion: boolean;
      debug_suspicion: boolean;
      mock_location_suspicion: boolean;
      trusted_telemetry_seen: boolean;
      observed_at?: string | null;
    } | null>(`/platform/devices/${deviceId}/trust-status?org_id=${encodeURIComponent(orgId())}`);
    if (!payload) {
      return null;
    }
    return {
      status: payload.status,
      summary: payload.summary,
      reasons: payload.reasons,
      integrityStatus: payload.integrity_status ?? undefined,
      rootSuspicion: payload.root_suspicion,
      debugSuspicion: payload.debug_suspicion,
      mockLocationSuspicion: payload.mock_location_suspicion,
      trustedTelemetrySeen: payload.trusted_telemetry_seen,
      observedAt: payload.observed_at ?? undefined,
    };
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

  locateDevice: async (deviceId: string, reason: string) => {
    const payload = await httpClient.post<{
      device_id: string;
      org_id: string;
      requested_at: string;
      precision: 'precise' | 'moderate' | 'approximate' | null;
      confidence_score: number | null;
      is_approximate: boolean;
      latitude: number | null;
      longitude: number | null;
      accuracy_meters: number | null;
      captured_at: string | null;
      source_methods: string[];
    }>(`/ownership/devices/${deviceId}/locate?org_id=${encodeURIComponent(orgId())}`, { reason });
    if (!payload.captured_at) {
      return null;
    }
    return {
      latitude: payload.latitude,
      longitude: payload.longitude,
      accuracyMeters: payload.accuracy_meters,
      precision: payload.precision ?? 'approximate',
      confidenceScore: payload.confidence_score ?? 0,
      collectedAt: payload.captured_at,
      sourceLabel: payload.is_approximate ? 'Approximate location result' : 'Authorized locate result',
      sourceMethods: payload.source_methods,
      isApproximate: payload.is_approximate,
      notes: payload.is_approximate ? 'Approximate location only. Do not treat this as exact recovery position.' : undefined,
    };
  },

  getDeviceAccessHistory: async (deviceId: string) => {
    const payload = await httpClient.get<
      Array<{
        audit_log_id: string;
        actor_sub: string;
        action: string;
        occurred_at: string;
        reason?: string | null;
        result?: string | null;
        metadata?: Record<string, string | number | boolean | null>;
      }>
    >(`/ownership/devices/${deviceId}/access-history?org_id=${encodeURIComponent(orgId())}`);
    return payload.map(toAccessHistory);
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

  getIncidents: async (filters = {}) => {
    const query = new URLSearchParams();
    query.set('org_id', filters.tenantId ?? orgId());
    if (filters.state && filters.state !== 'ALL') {
      query.set('incident_state', filters.state);
    }
    if (filters.updatedFrom) {
      query.set('updated_from', filters.updatedFrom);
    }
    if (filters.updatedTo) {
      query.set('updated_to', filters.updatedTo);
    }
    if (filters.assignedOperator) {
      query.set('assigned_operator_sub', filters.assignedOperator);
    }
    if (filters.search) {
      query.set('search', filters.search);
    }
    const payload = await httpClient.get<
      Array<{
        incident_id: string;
        org_id: string;
        device_id: string;
        ticket_reference: string;
        state: IncidentRecord['state'];
        assigned_operator_sub?: string | null;
        recovery_message?: string | null;
        lost_mode_until?: string | null;
        created_at: string;
        updated_at: string;
      }>
    >(`/platform/incidents?${query.toString()}`);
    return payload.map(toIncident);
  },

  assignIncident: async (incidentId, payload) => {
    const incident = await httpClient.post<{
      incident_id: string;
      org_id: string;
      device_id: string;
      ticket_reference: string;
      state: IncidentRecord['state'];
      assigned_operator_sub?: string | null;
      recovery_message?: string | null;
      lost_mode_until?: string | null;
      created_at: string;
      updated_at: string;
    }>(`/platform/cases/${incidentId}/assign`, {
      org_id: orgId(),
      operator_sub: payload.operatorSub,
      reason: payload.reason,
    });
    return toIncident(incident);
  },

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
        format: 'csv' | 'json' | 'pdf';
        status: 'generated' | 'failed';
        reason: string;
        redact_fields: string[];
        summary: Record<string, string | number | boolean | null>;
        download_placeholder?: string | null;
        created_at: string;
        generated_at?: string | null;
      }>;
      location_timeline?: Array<{
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
      audit_trail?: Array<{
        audit_id?: string;
        audit_log_id?: string;
        org_id?: string | null;
        actor_sub: string;
        action: string;
        entity_type: string;
        entity_id: string;
        metadata: Record<string, string | number | boolean | null>;
        occurred_at: string;
        previous_hash?: string | null;
        event_hash?: string;
      }>;
      command_history?: Array<{
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
      geofence_events?: Array<{
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
      external_shares?: Array<{
        export_id: string;
        incident_id: string;
        recipient_label: string;
        reason: string;
        shared_by_sub: string;
        shared_at: string;
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
      incidentSummary: payload.incident as Record<string, string | number | boolean | null>,
      locationTimeline: (payload.location_timeline ?? []).map((entry) => toHistoryPoint(camelLocation(entry))),
      auditTrail: (payload.audit_trail ?? []).map((entry) => ({
        id: entry.audit_id ?? entry.audit_log_id ?? `${entry.action}-${entry.occurred_at}`,
        createdAt: entry.occurred_at,
        actor: entry.actor_sub,
        action: entry.action,
        targetType: entry.entity_type,
        targetId: entry.entity_id,
        metadata: entry.metadata,
      })),
      commandHistory: (payload.command_history ?? payload.actions_taken).map(toCaseAction),
      geofenceEvents: (payload.geofence_events ?? []).map(toGeofenceEvent),
      actionsTaken: payload.actions_taken.map(toCaseAction),
      notes: payload.notes.map(toCaseNote),
      attachments: payload.attachments.map(toCaseAttachment),
      exports: payload.exports.map(toEvidenceExport),
      externalShares: (payload.external_shares ?? []).map(toEvidenceShare),
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
      format: 'csv' | 'json' | 'pdf';
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

  shareEvidenceExport: async (incidentId, exportId, payload) => {
    const shareRecord = await httpClient.post<{
      export_id: string;
      incident_id: string;
      recipient_label: string;
      reason: string;
      shared_by_sub: string;
      shared_at: string;
    }>(`/platform/cases/${incidentId}/exports/${exportId}/share`, {
      org_id: orgId(),
      recipient_label: payload.recipientLabel,
      reason: payload.reason,
    });
    return toEvidenceShare(shareRecord);
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

  getSettings: async () => {
    const payload = await httpClient.get<{
      org_id: string;
      timezone: string;
      default_map_provider: 'google' | 'mapbox';
      retention_policy: {
        location_event_days: number;
        audit_log_days: number;
        incident_evidence_days: number;
      };
      privacy_defaults: {
        explicit_consent_required: boolean;
        visible_app_required: boolean;
        background_location_requires_explanation: boolean;
        owner_access_history_visible: boolean;
        approximate_locations_clearly_labeled: boolean;
        short_retention_default: boolean;
      };
      updated_at?: string | null;
      updated_by_sub?: string | null;
    }>(`/platform/settings?org_id=${encodeURIComponent(orgId())}`);
    return toPlatformSettings(payload);
  },

  updateRetentionPolicy: async (policy, reason) => {
    const payload = await httpClient.put<{
      location_event_days: number;
      audit_log_days: number;
      incident_evidence_days: number;
    }>('/platform/settings/retention-policy', {
      org_id: orgId(),
      location_event_days: policy.locationEventDays,
      audit_log_days: policy.auditLogDays,
      incident_evidence_days: policy.incidentEvidenceDays,
      reason,
    });
    return {
      locationEventDays: payload.location_event_days,
      auditLogDays: payload.audit_log_days,
      incidentEvidenceDays: payload.incident_evidence_days,
    };
  },

  submitAbuseReport: async (payload) => {
    await httpClient.post<void>('/platform/abuse-reports', {
      org_id: orgId(),
      device_id: payload.deviceId,
      category: payload.category,
      description: payload.description,
      contact_email: payload.contactEmail,
    });
  },

  deprovisionDevice: async (deviceId, reason) => {
    await httpClient.post<void>(`/ownership/devices/${deviceId}/deprovision?org_id=${encodeURIComponent(orgId())}`, {
      reason,
    });
  },
};
