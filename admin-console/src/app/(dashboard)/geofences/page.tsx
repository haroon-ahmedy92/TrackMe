'use client';

import { LoadingCard } from '@/components/common/LoadingCard';
import { SensitiveActionModal } from '@/components/common/SensitiveActionModal';
import { GeoSignalMap } from '@/components/maps/GeoSignalMap';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { apiClient } from '@/lib/api/client';
import { formatDateTime } from '@/lib/format';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import { useState } from 'react';
import type { GeofenceRecord } from '@/types/models';

interface GeofenceDraft {
  id?: string;
  name: string;
  deviceId: string;
  centerLat: string;
  centerLng: string;
  radiusMeters: string;
  active: boolean;
}

const emptyDraft: GeofenceDraft = {
  name: '',
  deviceId: '',
  centerLat: '',
  centerLng: '',
  radiusMeters: '300',
  active: true,
};

export default function GeofencesPage() {
  const geofenceState = useAsyncData(() => apiClient.getGeofences(), []);
  const devicesState = useAsyncData(() => apiClient.getDevices(), []);

  const [draft, setDraft] = useState<GeofenceDraft>(emptyDraft);
  const [pendingDelete, setPendingDelete] = useState<GeofenceRecord | null>(null);
  const [confirmMode, setConfirmMode] = useState<'save' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const canSave = draft.name && draft.deviceId && draft.centerLat && draft.centerLng && draft.radiusMeters;
  const previewGeofences = [
    ...(geofenceState.data ?? []),
    ...(draft.centerLat && draft.centerLng && draft.name
      ? [
          {
            id: draft.id ?? 'draft-geofence',
            name: draft.name,
            deviceId: draft.deviceId,
            centerLat: Number(draft.centerLat),
            centerLng: Number(draft.centerLng),
            radiusMeters: Number(draft.radiusMeters),
            active: draft.active,
            createdAt: new Date().toISOString(),
          },
        ]
      : []),
  ];

  const handleEdit = (record: GeofenceRecord) => {
    setDraft({
      id: record.id,
      name: record.name,
      deviceId: record.deviceId,
      centerLat: String(record.centerLat),
      centerLng: String(record.centerLng),
      radiusMeters: String(record.radiusMeters),
      active: record.active,
    });
  };

  const resetDraft = () => setDraft(emptyDraft);

  const saveGeofence = async (reason: string) => {
    void reason;
    setSaving(true);
    setError(null);

    try {
      await apiClient.upsertGeofence({
        id: draft.id,
        name: draft.name,
        deviceId: draft.deviceId,
        centerLat: Number(draft.centerLat),
        centerLng: Number(draft.centerLng),
        radiusMeters: Number(draft.radiusMeters),
        active: draft.active,
      });
      await geofenceState.refresh();
      setConfirmMode(null);
      resetDraft();
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : 'Failed to save geofence.');
    } finally {
      setSaving(false);
    }
  };

  const deleteGeofence = async (reason: string) => {
    if (!pendingDelete) {
      return;
    }
    setSaving(true);
    setError(null);

    try {
      await apiClient.deleteGeofence(pendingDelete.id, reason);
      await geofenceState.refresh();
      setPendingDelete(null);
      if (draft.id === pendingDelete.id) {
        resetDraft();
      }
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : 'Failed to delete geofence.');
    } finally {
      setSaving(false);
    }
  };

  if (geofenceState.loading || devicesState.loading) {
    return (
      <div className="page">
        <LoadingCard />
      </div>
    );
  }

  if (geofenceState.error || devicesState.error) {
    return (
      <div className="page">
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>
            {geofenceState.error ?? devicesState.error ?? 'Could not load geofence data.'}
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="page container stack">
      <div>
        <h1 className="page-title">Geofence Management</h1>
        <p className="page-subtitle">Opt-in asset protection zones. No hidden tracking behavior.</p>
      </div>

      {error ? (
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{error}</p>
        </Card>
      ) : null}

      <div className="grid-2">
        <Card>
          <h2 style={{ marginTop: 0 }}>{draft.id ? 'Edit geofence' : 'Create geofence'}</h2>
          <div className="stack">
            <Input
              label="Name"
              value={draft.name}
              onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
            />
            <Select
              label="Device"
              value={draft.deviceId}
              onChange={(event) => setDraft((current) => ({ ...current, deviceId: event.target.value }))}
              options={[
                { label: 'Select device', value: '' },
                ...(devicesState.data ?? []).map((device) => ({ label: device.deviceName, value: device.id })),
              ]}
            />
            <Input
              label="Center Latitude"
              value={draft.centerLat}
              onChange={(event) => setDraft((current) => ({ ...current, centerLat: event.target.value }))}
            />
            <Input
              label="Center Longitude"
              value={draft.centerLng}
              onChange={(event) => setDraft((current) => ({ ...current, centerLng: event.target.value }))}
            />
            <Input
              label="Radius (meters)"
              value={draft.radiusMeters}
              onChange={(event) => setDraft((current) => ({ ...current, radiusMeters: event.target.value }))}
            />
            <Select
              label="Status"
              value={draft.active ? 'active' : 'inactive'}
              onChange={(event) => setDraft((current) => ({ ...current, active: event.target.value === 'active' }))}
              options={[
                { label: 'Active', value: 'active' },
                { label: 'Inactive', value: 'inactive' },
              ]}
            />

            <div className="row">
              <Button disabled={!canSave} onClick={() => setConfirmMode('save')}>
                {draft.id ? 'Update Geofence' : 'Create Geofence'}
              </Button>
              {draft.id ? (
                <Button variant="ghost" onClick={resetDraft}>
                  Cancel Edit
                </Button>
              ) : null}
            </div>
          </div>
        </Card>

        <Card>
          <h2 style={{ marginTop: 0, marginBottom: 10 }}>Zone map preview</h2>
          <GeoSignalMap
            title="Add coordinates to preview the geofence"
            geofences={previewGeofences}
            points={(devicesState.data ?? [])
              .filter((device) => device.location.latitude != null && device.location.longitude != null)
              .map((device) => ({
                id: device.id,
                label: device.deviceName,
                latitude: device.location.latitude,
                longitude: device.location.longitude,
                precision: device.location.precision,
                confidenceScore: device.location.confidenceScore,
                sourceLabel: device.location.sourceLabel,
                collectedAt: device.location.collectedAt,
                isApproximate: device.location.isApproximate,
              }))}
            height={300}
          />
        </Card>
      </div>

      <Card>
        <DataTable
          rows={geofenceState.data ?? []}
          rowKey={(item) => item.id}
          columns={[
            {
              key: 'name',
              header: 'Name',
              cell: (item) => (
                <div className="stack" style={{ gap: 4 }}>
                  <span style={{ fontWeight: 700 }}>{item.name}</span>
                  <span className="text-muted" style={{ fontSize: 12 }}>
                    {item.centerLat.toFixed(4)}, {item.centerLng.toFixed(4)}
                  </span>
                </div>
              ),
            },
            {
              key: 'radius',
              header: 'Radius',
              cell: (item) => `${item.radiusMeters}m`,
            },
            {
              key: 'status',
              header: 'Status',
              cell: (item) => (
                <Badge variant={item.active ? 'success' : 'neutral'}>{item.active ? 'Active' : 'Inactive'}</Badge>
              ),
            },
            {
              key: 'created',
              header: 'Created',
              cell: (item) => formatDateTime(item.createdAt),
            },
            {
              key: 'actions',
              header: 'Actions',
              cell: (item) => (
                <div className="row">
                  <Button variant="ghost" onClick={() => handleEdit(item)}>
                    Edit
                  </Button>
                  <Button variant="danger" onClick={() => setPendingDelete(item)}>
                    Delete
                  </Button>
                </div>
              ),
            },
          ]}
        />
      </Card>

      <SensitiveActionModal
        open={confirmMode === 'save'}
        title={draft.id ? 'Confirm geofence update' : 'Confirm new geofence'}
        description="Provide a reason so this configuration change is captured in audit history."
        confirmLabel={draft.id ? 'Update' : 'Create'}
        loading={saving}
        onCancel={() => setConfirmMode(null)}
        onConfirm={saveGeofence}
      />

      <SensitiveActionModal
        open={Boolean(pendingDelete)}
        title="Delete geofence"
        description="Removing this geofence may stop exit/entry alerts for the assigned device."
        confirmLabel="Delete geofence"
        danger
        loading={saving}
        onCancel={() => setPendingDelete(null)}
        onConfirm={deleteGeofence}
      />
    </div>
  );
}
