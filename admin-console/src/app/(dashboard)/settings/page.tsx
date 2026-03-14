'use client';

import { LoadingCard } from '@/components/common/LoadingCard';
import { SensitiveActionModal } from '@/components/common/SensitiveActionModal';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { apiClient } from '@/lib/api/client';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import { useEffect, useState } from 'react';

export default function SettingsPage() {
  const settingsState = useAsyncData(() => apiClient.getSettings(), []);

  const [locationDays, setLocationDays] = useState('30');
  const [auditDays, setAuditDays] = useState('90');
  const [incidentDays, setIncidentDays] = useState('60');
  const [mapProvider, setMapProvider] = useState<'google' | 'mapbox'>('google');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [abuseCategory, setAbuseCategory] = useState('unauthorized_lookup');
  const [abuseDescription, setAbuseDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [submittingAbuse, setSubmittingAbuse] = useState(false);
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

  const onSubmitAbuseReport = async () => {
    setSubmittingAbuse(true);
    setError(null);
    setSuccess(null);
    try {
      await apiClient.submitAbuseReport({
        category: abuseCategory,
        description: abuseDescription,
      });
      setAbuseDescription('');
      setSuccess('Abuse report submitted and linked to the audit trail.');
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : 'Unable to submit abuse report.');
    } finally {
      setSubmittingAbuse(false);
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

      <div className="grid-2">
        <Card>
          <h2 style={{ marginTop: 0 }}>Privacy Dashboard</h2>
          <div className="stack">
            <div className="row">
              <Badge variant="success">{settingsState.data.privacyDefaults.visibleAppRequired ? 'Visible app required' : 'Review needed'}</Badge>
              <Badge variant="success">
                {settingsState.data.privacyDefaults.explicitConsentRequired ? 'Explicit consent required' : 'Review needed'}
              </Badge>
            </div>
            <div className="row">
              <Badge variant="success">
                {settingsState.data.privacyDefaults.backgroundLocationRequiresExplanation
                  ? 'Background location explained'
                  : 'Review needed'}
              </Badge>
              <Badge variant="warning">
                {settingsState.data.privacyDefaults.shortRetentionDefault ? 'Short retention default' : 'Long retention profile'}
              </Badge>
            </div>
            <p className="text-muted" style={{ margin: 0, fontSize: 13 }}>
              Approximate results are always labeled, owner/admin access history remains visible, and hidden or deceptive behavior is out of scope.
            </p>
            <p className="text-muted" style={{ margin: 0, fontSize: 12 }}>
              Last settings update: {settingsState.data.updatedAt ?? 'Unknown'} by {settingsState.data.updatedBySub ?? 'system default'}
            </p>
          </div>
        </Card>

        <Card>
          <h2 style={{ marginTop: 0 }}>Abuse Reporting</h2>
          <div className="stack">
            <Select
              label="Category"
              value={abuseCategory}
              onChange={(event) => setAbuseCategory(event.target.value)}
              options={[
                { label: 'Unauthorized locate lookups', value: 'unauthorized_lookup' },
                { label: 'Policy confusion', value: 'policy_confusion' },
                { label: 'Unexpected access', value: 'unexpected_access' },
              ]}
            />
            <Textarea
              label="Report description"
              value={abuseDescription}
              onChange={(event) => setAbuseDescription(event.target.value)}
              placeholder="Describe the behavior, who was affected, and why it appears inconsistent with policy."
            />
            <p className="text-muted" style={{ margin: 0, fontSize: 12 }}>
              Reports are audit-linked and should describe visible product misuse, not covert monitoring features.
            </p>
            <Button disabled={submittingAbuse || abuseDescription.trim().length < 8} onClick={() => void onSubmitAbuseReport()}>
              Submit Abuse Report
            </Button>
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
