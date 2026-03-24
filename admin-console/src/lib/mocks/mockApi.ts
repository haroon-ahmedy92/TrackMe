import { ApiError } from '@/lib/api/errors';
import type { ApiClient } from '@/lib/api/types';
import {
  mockAuditLogs,
  mockCaseAttachments,
  mockCaseEvidenceChains,
  mockCaseNotes,
  mockDeviceClusters,
  mockDevices,
  mockEvidenceExports,
  mockGeofences,
  mockGeofenceEvents,
  mockIncidentTimeline,
  mockIncidentRoutes,
  mockIncidents,
  mockLocationHistory,
  mockRemoteActions,
  mockSettings,
} from '@/lib/mocks/data';
import type {
  AccessHistoryRecord,
  CaseAttachmentRecord,
  CaseEvidenceChainRecord,
  CaseNoteRecord,
  DeviceClusterRecord,
  DeviceTrustRecord,
  EvidenceShareRecord,
  GeofenceRecord,
  GeofenceEventRecord,
  EvidenceExportRecord,
  IncidentFilters,
  IncidentRecord,
  IncidentRouteRecord,
  LoginRequest,
  LoginResponse,
  LocationHistoryPoint,
  LocationSnapshot,
  NotificationEventRecord,
  OwnershipBindingRecord,
  RemoteActionRecord,
} from '@/types/models';

const SIMULATED_LATENCY_MS = 500;

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

const wait = async () => {
  await new Promise((resolve) => setTimeout(resolve, SIMULATED_LATENCY_MS));
};

let devices = clone(mockDevices);
let incidents = clone(mockIncidents);
let timeline = clone(mockIncidentTimeline);
let geofences = clone(mockGeofences);
let auditLogs = clone(mockAuditLogs);
let remoteActions = clone(mockRemoteActions);
let settings = clone(mockSettings);
const notifications: NotificationEventRecord[] = [
  {
    id: 'notif-1',
    orgId: 'org-001',
    incidentId: 'inc-002',
    deviceId: 'device-002',
    channel: 'internal',
    template: 'incident_escalation',
    payload: {
      title: 'Recovery Incident Started',
      body: 'Lost-mode recovery incident is active. Review the case timeline and latest location quality.',
    },
    status: 'SENT',
    createdAt: new Date(Date.now() - 30 * 60_000).toISOString(),
    sentAt: new Date(Date.now() - 30 * 60_000).toISOString(),
  },
];
const locationHistory = clone(mockLocationHistory);
const geofenceEvents = clone(mockGeofenceEvents);
const incidentRoutes = clone(mockIncidentRoutes);
const deviceClusters = clone(mockDeviceClusters);
const caseNotes = clone(mockCaseNotes);
const caseAttachments = clone(mockCaseAttachments);
const evidenceExports = clone(mockEvidenceExports);
const caseEvidenceChains = clone(mockCaseEvidenceChains);

const appendAudit = (entry: {
  action: string;
  targetType: string;
  targetId: string;
  reason: string;
  actor?: string;
}) => {
  auditLogs = [
    {
      id: `aud-${Date.now()}`,
      createdAt: new Date().toISOString(),
      actor: entry.actor ?? 'web.admin@local',
      action: entry.action,
      targetType: entry.targetType,
      targetId: entry.targetId,
      reason: entry.reason,
    },
    ...auditLogs,
  ];
};

const findIncidentForDevice = (deviceId: string): IncidentRecord | undefined =>
  incidents.find((incident) => incident.deviceId === deviceId && !['RECOVERED', 'WIPED', 'DECOMMISSIONED'].includes(incident.state));

export const mockApiClient: ApiClient = {
  async login(payload: LoginRequest): Promise<LoginResponse> {
    await wait();
    if (!payload.email || !payload.password) {
      throw new ApiError('Email and password are required.', 400);
    }

    return {
      accessToken: 'mock-token',
      profile: {
        id: 'usr-1',
        fullName: 'Local Admin',
        email: payload.email,
        role: 'admin',
        tenantId: 'org-001',
      },
    };
  },

  async getDevices() {
    await wait();
    return clone(devices);
  },

  async getDeviceById(deviceId: string) {
    await wait();
    const device = devices.find((item) => item.id === deviceId);
    if (!device) {
      throw new ApiError('Device not found', 404);
    }
    return clone(device);
  },

  async getDeviceBinding(deviceId: string): Promise<OwnershipBindingRecord | null> {
    await wait();
    const device = devices.find((item) => item.id === deviceId);
    if (!device) {
      throw new ApiError('Device not found', 404);
    }
    return {
      id: `binding-${deviceId}`,
      orgId: device.tenantId,
      deviceId,
      ownerSubject: 'owner@local',
      ownershipType: 'organization_owned',
      proofKind: 'enrollment_token',
      consentVersion: '2026-03-10',
      consentCapturedAt: device.enrollmentDate,
      isActive: true,
      createdAt: device.enrollmentDate,
    };
  },

  async getDeviceTrustStatus(deviceId: string): Promise<DeviceTrustRecord | null> {
    await wait();
    const device = devices.find((item) => item.id === deviceId);
    if (!device) {
      throw new ApiError('Device not found', 404);
    }
    return clone(device.trust ?? null);
  },

  async issuePairingToken(payload) {
    await wait();
    return {
      pairingTokenId: `pair-${Date.now()}`,
      orgId: payload.orgId,
      deviceId: payload.deviceId,
      token: `trackme-${Math.random().toString(36).slice(2)}${Math.random().toString(36).slice(2)}`,
      tokenHint: 'trackme-••••',
      pairingUri: `trackme://pair?token=mock-${Math.random().toString(36).slice(2)}`,
      expiresAt: new Date(Date.now() + payload.expiresInMinutes * 60_000).toISOString(),
    };
  },

  async getLastKnownLocation(deviceId: string): Promise<LocationSnapshot | null> {
    await wait();
    const history = locationHistory[deviceId] ?? [];
    return clone(history[history.length - 1] ?? devices.find((item) => item.id === deviceId)?.location ?? null);
  },

  async locateDevice(deviceId: string, reason: string): Promise<LocationSnapshot | null> {
    await wait();
    appendAudit({ action: 'LOCATION_LOOKUP_REQUESTED', targetType: 'device', targetId: deviceId, reason });
    const location = await this.getLastKnownLocation(deviceId);
    appendAudit({
      action: 'LOCATION_LOOKUP_RESULT',
      targetType: 'device',
      targetId: deviceId,
      reason: location ? 'Locate request returned last known location' : 'Locate request returned no location',
    });
    return location;
  },

  async getNotifications(): Promise<NotificationEventRecord[]> {
    await wait();
    return clone(notifications);
  },

  async getDeviceAccessHistory(deviceId: string): Promise<AccessHistoryRecord[]> {
    await wait();
    return clone(
      auditLogs
        .filter(
          (entry) =>
            entry.targetType === 'device' &&
            entry.targetId === deviceId &&
            ['LOCATION_LOOKUP_REQUESTED', 'LOCATION_LOOKUP_RESULT', 'DEVICE_DEPROVISIONED'].includes(entry.action),
        )
        .map((entry) => ({
          id: entry.id,
          actor: entry.actor,
          action: entry.action,
          occurredAt: entry.createdAt,
          reason: entry.reason,
          result:
            entry.action === 'LOCATION_LOOKUP_REQUESTED'
              ? 'requested'
              : entry.action === 'LOCATION_LOOKUP_RESULT'
                ? 'success'
                : 'completed',
          metadata: entry.metadata ?? {},
        })),
    );
  },

  async getLocationHistory(deviceId: string): Promise<LocationHistoryPoint[]> {
    await wait();
    return clone(locationHistory[deviceId] ?? []);
  },

  async getDeviceClusters(): Promise<DeviceClusterRecord[]> {
    await wait();
    return clone(deviceClusters);
  },

  async getIncidents(filters: IncidentFilters = {}) {
    await wait();
    return clone(
      incidents.filter((incident) => {
        if (filters.tenantId && incident.orgId !== filters.tenantId) return false;
        if (filters.state && filters.state !== 'ALL' && incident.state !== filters.state) return false;
        if (filters.assignedOperator && incident.assignedOperator !== filters.assignedOperator) return false;
        if (filters.updatedFrom && incident.updatedAt < filters.updatedFrom) return false;
        if (filters.updatedTo && incident.updatedAt > filters.updatedTo) return false;
        if (filters.search) {
          const haystack = `${incident.title} ${incident.id} ${incident.assignedOperator ?? ''}`.toLowerCase();
          if (!haystack.includes(filters.search.toLowerCase())) return false;
        }
        return true;
      }),
    );
  },

  async assignIncident(incidentId: string, payload: { operatorSub: string; reason: string }): Promise<IncidentRecord> {
    await wait();
    const incident = incidents.find((item) => item.id === incidentId);
    if (!incident) {
      throw new ApiError('Incident not found', 404);
    }
    incident.assignedOperator = payload.operatorSub;
    incident.ownerName = payload.operatorSub;
    incident.updatedAt = new Date().toISOString();
    appendAudit({
      action: 'INCIDENT_ASSIGNED_OPERATOR',
      targetType: 'incident',
      targetId: incidentId,
      reason: payload.reason,
    });
    return clone(incident);
  },

  async getIncidentTimeline(incidentId: string) {
    await wait();
    return clone(timeline.filter((event) => event.incidentId === incidentId));
  },

  async getIncidentRoute(incidentId: string): Promise<IncidentRouteRecord> {
    await wait();
    const route = incidentRoutes[incidentId];
    if (!route) {
      throw new ApiError('Incident route not found', 404);
    }
    return clone(route);
  },

  async getCaseEvidenceChain(incidentId: string): Promise<CaseEvidenceChainRecord> {
    await wait();
    const chain = caseEvidenceChains[incidentId];
    if (!chain) {
      throw new ApiError('Evidence chain not found', 404);
    }
    return clone(chain);
  },

  async addCaseNote(incidentId: string, payload: { body: string; pinned?: boolean }): Promise<CaseNoteRecord> {
    await wait();
    const note: CaseNoteRecord = {
      id: `note-${Date.now()}`,
      incidentId,
      author: 'web.admin@local',
      body: payload.body,
      pinned: Boolean(payload.pinned),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    caseNotes[incidentId] = [note, ...(caseNotes[incidentId] ?? [])];
    caseEvidenceChains[incidentId] = {
      ...caseEvidenceChains[incidentId],
      notes: caseNotes[incidentId],
      entries: [
        {
          id: `entry-note-${Date.now()}`,
          kind: 'note',
          title: 'Analyst note',
          summary: payload.body,
          occurredAt: note.updatedAt,
          actor: note.author,
          mutable: true,
          data: { pinned: note.pinned },
        },
        ...(caseEvidenceChains[incidentId]?.entries ?? []),
      ],
    };
    appendAudit({ action: 'CASE_NOTE_CREATED', targetType: 'incident_note', targetId: note.id, reason: payload.body });
    return clone(note);
  },

  async updateCaseNote(incidentId: string, noteId: string, payload: { body: string; pinned?: boolean }): Promise<CaseNoteRecord> {
    await wait();
    const note = (caseNotes[incidentId] ?? []).find((item) => item.id === noteId);
    if (!note) {
      throw new ApiError('Note not found', 404);
    }
    note.body = payload.body;
    note.pinned = Boolean(payload.pinned);
    note.updatedAt = new Date().toISOString();
    appendAudit({ action: 'CASE_NOTE_UPDATED', targetType: 'incident_note', targetId: noteId, reason: payload.body });
    return clone(note);
  },

  async addCaseAttachment(
    incidentId: string,
    payload: { fileName: string; mediaType: string; byteSize: number; sha256?: string; description?: string },
  ): Promise<CaseAttachmentRecord> {
    await wait();
    const attachment: CaseAttachmentRecord = {
      id: `attachment-${Date.now()}`,
      incidentId,
      uploadedBy: 'web.admin@local',
      fileName: payload.fileName,
      mediaType: payload.mediaType,
      byteSize: payload.byteSize,
      sha256: payload.sha256,
      description: payload.description,
      storageBackend: 'mock-local',
      storageKey: `placeholder://incident/${incidentId}/${payload.fileName}`,
      downloadUrl: '#mock-download',
      createdAt: new Date().toISOString(),
    };
    caseAttachments[incidentId] = [attachment, ...(caseAttachments[incidentId] ?? [])];
    caseEvidenceChains[incidentId] = {
      ...caseEvidenceChains[incidentId],
      attachments: caseAttachments[incidentId],
      entries: [
        {
          id: `entry-attachment-${Date.now()}`,
          kind: 'attachment',
          title: payload.fileName,
          summary: payload.description ?? payload.mediaType,
          occurredAt: attachment.createdAt,
          actor: attachment.uploadedBy,
          mutable: false,
          data: { mediaType: payload.mediaType, byteSize: payload.byteSize },
        },
        ...(caseEvidenceChains[incidentId]?.entries ?? []),
      ],
    };
    appendAudit({ action: 'CASE_ATTACHMENT_ADDED', targetType: 'incident_attachment', targetId: attachment.id, reason: payload.description ?? payload.fileName });
    return clone(attachment);
  },

  async uploadCaseAttachment(incidentId: string, payload: { file: File; description?: string }): Promise<CaseAttachmentRecord> {
    return this.addCaseAttachment(incidentId, {
      fileName: payload.file.name,
      mediaType: payload.file.type || 'application/octet-stream',
      byteSize: payload.file.size,
      description: payload.description,
    });
  },

  async requestEvidenceExport(
    incidentId: string,
    payload: { format: 'csv' | 'json' | 'pdf'; reason: string; redactFields: string[] },
  ): Promise<EvidenceExportRecord> {
    await wait();
    const record: EvidenceExportRecord = {
      id: `export-${Date.now()}`,
      incidentId,
      requestedBy: 'web.admin@local',
      format: payload.format,
      status: 'generated',
      reason: payload.reason,
      redactFields: payload.redactFields,
      summary: { placeholder: true, format: payload.format },
      downloadPlaceholder: `placeholder://exports/${incidentId}.${payload.format}`,
      createdAt: new Date().toISOString(),
      generatedAt: new Date().toISOString(),
    };
    evidenceExports[incidentId] = [record, ...(evidenceExports[incidentId] ?? [])];
    caseEvidenceChains[incidentId] = {
      ...caseEvidenceChains[incidentId],
      exports: evidenceExports[incidentId],
    };
    appendAudit({ action: 'CASE_EVIDENCE_EXPORT_CREATED', targetType: 'evidence_export', targetId: record.id, reason: payload.reason });
    return clone(record);
  },

  async shareEvidenceExport(
    incidentId: string,
    exportId: string,
    payload: { recipientLabel: string; reason: string },
  ): Promise<EvidenceShareRecord> {
    await wait();
    const chain = caseEvidenceChains[incidentId];
    if (!chain) {
      throw new ApiError('Evidence chain not found', 404);
    }
    const exportRecord = (evidenceExports[incidentId] ?? []).find((item) => item.id === exportId);
    if (!exportRecord) {
      throw new ApiError('Export not found', 404);
    }
    const share: EvidenceShareRecord = {
      exportId,
      incidentId,
      recipientLabel: payload.recipientLabel,
      reason: payload.reason,
      sharedBy: 'web.admin@local',
      sharedAt: new Date().toISOString(),
    };
    chain.externalShares = [share, ...(chain.externalShares ?? [])];
    appendAudit({
      action: 'CASE_EVIDENCE_EXPORT_SHARED_EXTERNALLY',
      targetType: 'evidence_export',
      targetId: exportId,
      reason: payload.reason,
    });
    return clone(share);
  },

  async markDeviceLost(deviceId: string, reason: string) {
    await wait();
    const device = devices.find((item) => item.id === deviceId);
    if (!device) {
      throw new ApiError('Device not found', 404);
    }

    const existing = findIncidentForDevice(deviceId);
    if (existing) {
      throw new ApiError('Active incident already exists for this device', 409);
    }

    const incident: IncidentRecord = {
      id: `inc-${Date.now()}`,
      orgId: 'org-001',
      deviceId,
      title: `${device.deviceName} suspected lost`,
      state: 'SUSPECTED_LOST',
      openedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ownerName: 'Operations Team',
      assignedOperator: undefined,
      highFrequencyUntil: new Date(Date.now() + 1000 * 60 * 60 * 12).toISOString(),
    };

    incidents = [incident, ...incidents];
    device.status = 'lost_mode';
    device.incidentState = 'SUSPECTED_LOST';

    timeline = [
      {
        id: `evt-${Date.now()}`,
        incidentId: incident.id,
        createdAt: new Date().toISOString(),
        actor: 'web.admin@local',
        eventType: 'INCIDENT_CREATED',
        reason,
        details: 'Lost mode activated with temporary higher frequency reporting window.',
      },
      ...timeline,
    ];

    appendAudit({ action: 'MARK_DEVICE_LOST', targetType: 'device', targetId: deviceId, reason });
  },

  async confirmDeviceStolen(incidentId: string, reason: string) {
    await wait();
    const incident = incidents.find((item) => item.id === incidentId);
    if (!incident) {
      throw new ApiError('Incident not found', 404);
    }
    incident.state = 'CONFIRMED_STOLEN';
    incident.updatedAt = new Date().toISOString();

    const device = devices.find((item) => item.id === incident.deviceId);
    if (device) {
      device.incidentState = 'CONFIRMED_STOLEN';
    }

    timeline = [
      {
        id: `evt-${Date.now()}`,
        incidentId,
        createdAt: new Date().toISOString(),
        actor: 'web.admin@local',
        eventType: 'CONFIRM_STOLEN',
        reason,
      },
      ...timeline,
    ];

    appendAudit({ action: 'CONFIRM_STOLEN', targetType: 'incident', targetId: incidentId, reason });
  },

  async recoverIncident(incidentId: string, reason: string) {
    await wait();
    const incident = incidents.find((item) => item.id === incidentId);
    if (!incident) {
      throw new ApiError('Incident not found', 404);
    }

    incident.state = 'RECOVERED';
    incident.updatedAt = new Date().toISOString();

    const device = devices.find((item) => item.id === incident.deviceId);
    if (device) {
      device.status = 'protected';
      device.incidentState = 'RECOVERED';
    }

    timeline = [
      {
        id: `evt-${Date.now()}`,
        incidentId,
        createdAt: new Date().toISOString(),
        actor: 'web.admin@local',
        eventType: 'MARK_RECOVERED',
        reason,
      },
      ...timeline,
    ];

    appendAudit({ action: 'MARK_RECOVERED', targetType: 'incident', targetId: incidentId, reason });
  },

  async getGeofences() {
    await wait();
    return clone(geofences);
  },

  async getGeofenceEvents(deviceId: string): Promise<GeofenceEventRecord[]> {
    await wait();
    return clone(geofenceEvents.filter((event) => event.deviceId === deviceId));
  },

  async upsertGeofence(geofenceInput) {
    await wait();
    const now = new Date().toISOString();
    let geofence: GeofenceRecord;

    if (geofenceInput.id) {
      const existing = geofences.find((item) => item.id === geofenceInput.id);
      if (!existing) {
        throw new ApiError('Geofence not found', 404);
      }
      geofence = {
        ...existing,
        ...geofenceInput,
      };
      geofences = geofences.map((item) => (item.id === geofence.id ? geofence : item));
      appendAudit({ action: 'UPDATE_GEOFENCE', targetType: 'geofence', targetId: geofence.id, reason: 'Policy update from admin console' });
      return clone(geofence);
    }

    geofence = {
      ...geofenceInput,
      id: `geo-${Date.now()}`,
      createdAt: now,
    };

    geofences = [geofence, ...geofences];
    appendAudit({ action: 'CREATE_GEOFENCE', targetType: 'geofence', targetId: geofence.id, reason: 'New opt-in geofence rule created.' });
    return clone(geofence);
  },

  async deleteGeofence(geofenceId: string, reason: string) {
    await wait();
    geofences = geofences.filter((item) => item.id !== geofenceId);
    appendAudit({ action: 'DELETE_GEOFENCE', targetType: 'geofence', targetId: geofenceId, reason });
  },

  async getAuditLogs() {
    await wait();
    return clone(auditLogs);
  },

  async getRemoteActions() {
    await wait();
    return clone(remoteActions);
  },

  async approveRemoteAction(actionId: string, reason: string) {
    await wait();
    remoteActions = remoteActions.map((item): RemoteActionRecord =>
      item.id === actionId ? { ...item, status: 'APPROVED' } : item,
    );
    appendAudit({ action: 'APPROVE_REMOTE_ACTION', targetType: 'remote_action', targetId: actionId, reason });
  },

  async rejectRemoteAction(actionId: string, reason: string) {
    await wait();
    remoteActions = remoteActions.map((item): RemoteActionRecord =>
      item.id === actionId ? { ...item, status: 'REJECTED' } : item,
    );
    appendAudit({ action: 'REJECT_REMOTE_ACTION', targetType: 'remote_action', targetId: actionId, reason });
  },

  async getSettings() {
    await wait();
    return clone(settings);
  },

  async updateRetentionPolicy(policy, reason) {
    await wait();
    settings = {
      ...settings,
      retentionPolicy: policy,
    };
    appendAudit({ action: 'UPDATE_RETENTION_POLICY', targetType: 'settings', targetId: 'retention-policy', reason });
    return clone(settings.retentionPolicy);
  },

  async submitAbuseReport(payload) {
    await wait();
    appendAudit({
      action: 'ABUSE_REPORT_SUBMITTED',
      targetType: 'abuse_report',
      targetId: payload.deviceId ?? `org-${Date.now()}`,
      reason: payload.description,
    });
  },

  async deprovisionDevice(deviceId: string, reason: string) {
    await wait();
    devices = devices.map((item) =>
      item.id === deviceId
        ? { ...item, status: 'unenrolled', online: false }
        : item,
    );
    appendAudit({ action: 'DEVICE_DEPROVISIONED', targetType: 'device', targetId: deviceId, reason });
  },
};
