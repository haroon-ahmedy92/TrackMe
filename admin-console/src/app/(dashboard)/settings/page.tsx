'use client';

import { LoadingCard } from '@/components/common/LoadingCard';
import { SensitiveActionModal } from '@/components/common/SensitiveActionModal';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { apiClient } from '@/lib/api/client';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import { useEffect, useState } from 'react';

export default function SettingsPage() {
  const settingsState = useAsyncData(() => apiClient.getSettings(), []);

  const [locationDays, setLocationDays] = useState('90');
  const [auditDays, setAuditDays] = useState('365');
  const [incidentDays, setIncidentDays] = useState('180');
  const [mapProvider, setMapProvider] = useState<'google' | 'mapbox'>('google');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const settings = settingsState.data;
    if (!settings) {
      return;
    }
    setLocationDays(String(settings.retentionPolicy.locationEventDays));
    setAuditDays(String(settings.retentionPolicy.auditLogDays));
    setIncidentDays(String(settings.retentionPolicy.incidentEvidenceDays));
    setMapProvider(settings.defaultMapProvider);
  }, [settingsState.data]);

  const onSave = async (reason: string) => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await apiClient.updateRetentionPolicy(
        {
          locationEventDays: Number(locationDays),
          auditLogDays: Number(auditDays),
          incidentEvidenceDays: Number(incidentDays),
        },
        reason,
      );
      setConfirmOpen(false);
      setSuccess('Retention policy updated and recorded in audit logs.');
      await settingsState.refresh();
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : 'Unable to update settings.');
    } finally {
      setSaving(false);
    }
  };

  if (settingsState.loading) {
    return (
      <div className="page">
        <LoadingCard />
      </div>
    );
  }

  if (settingsState.error || !settingsState.data) {
    return (
      <div className="page">
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{settingsState.error ?? 'Failed to load settings.'}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="page container stack">
      <div>
        <h1 className="page-title">Settings & Data Retention</h1>
        <p className="page-subtitle">Retention changes are sensitive and always require reason-based confirmation.</p>
      </div>

      {error ? (
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{error}</p>
        </Card>
      ) : null}

      {success ? (
        <Card>
          <p style={{ margin: 0, color: 'var(--success)' }}>{success}</p>
        </Card>
      ) : null}

      <div className="grid-2">
        <Card>
          <h2 style={{ marginTop: 0 }}>Platform Preferences</h2>
          <div className="stack">
            <Input label="Timezone" value={settingsState.data.timezone} disabled />
            <Select
              label="Map provider"
              value={mapProvider}
              onChange={(event) => setMapProvider(event.target.value as 'google' | 'mapbox')}
              options={[
                { label: 'Google Maps', value: 'google' },
                { label: 'Mapbox', value: 'mapbox' },
              ]}
            />
            <p className="text-muted" style={{ margin: 0, fontSize: 12 }}>
              TODO: map provider selection is currently UI-only until backend endpoint is finalized.
            </p>
          </div>
        </Card>

        <Card>
          <h2 style={{ marginTop: 0 }}>Retention Policy</h2>
          <div className="stack">
            <Input
              label="Location events retention (days)"
              type="number"
              min={1}
              value={locationDays}
              onChange={(event) => setLocationDays(event.target.value)}
            />
            <Input
              label="Audit logs retention (days)"
              type="number"
              min={30}
              value={auditDays}
              onChange={(event) => setAuditDays(event.target.value)}
            />
            <Input
              label="Incident evidence retention (days)"
              type="number"
              min={30}
              value={incidentDays}
              onChange={(event) => setIncidentDays(event.target.value)}
            />

            <p className="warning-note" style={{ margin: 0 }}>
              Shorter retention may reduce investigation capacity. Longer retention increases compliance and storage obligations.
            </p>

            <div className="row">
              <Badge variant="warning">Sensitive Action</Badge>
              <Button onClick={() => setConfirmOpen(true)}>Save Retention Policy</Button>
            </div>
          </div>
        </Card>
      </div>

      <SensitiveActionModal
        open={confirmOpen}
        title="Confirm retention policy change"
        description="Provide business/compliance reason for changing retained evidence durations."
        confirmLabel="Apply Policy"
        loading={saving}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={onSave}
      />
    </div>
  );
}
