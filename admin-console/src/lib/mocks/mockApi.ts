import { ApiError } from '@/lib/api/errors';
import type { ApiClient } from '@/lib/api/types';
import {
  mockAuditLogs,
  mockDeviceClusters,
  mockDevices,
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
  DeviceClusterRecord,
  GeofenceRecord,
  GeofenceEventRecord,
  IncidentRecord,
  IncidentRouteRecord,
  LoginRequest,
  LoginResponse,
  LocationHistoryPoint,
  LocationSnapshot,
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
let locationHistory = clone(mockLocationHistory);
let geofenceEvents = clone(mockGeofenceEvents);
let incidentRoutes = clone(mockIncidentRoutes);
let deviceClusters = clone(mockDeviceClusters);

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

  async getLastKnownLocation(deviceId: string): Promise<LocationSnapshot | null> {
    await wait();
    const history = locationHistory[deviceId] ?? [];
    return clone(history[history.length - 1] ?? devices.find((item) => item.id === deviceId)?.location ?? null);
  },

  async getLocationHistory(deviceId: string): Promise<LocationHistoryPoint[]> {
    await wait();
    return clone(locationHistory[deviceId] ?? []);
  },

  async getDeviceClusters(): Promise<DeviceClusterRecord[]> {
    await wait();
    return clone(deviceClusters);
  },

  async getIncidents() {
    await wait();
    return clone(incidents);
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
      deviceId,
      title: `${device.deviceName} suspected lost`,
      state: 'SUSPECTED_LOST',
      openedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ownerName: 'Operations Team',
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
};
