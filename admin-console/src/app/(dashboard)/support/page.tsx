'use client';

import { LoadingCard } from '@/components/common/LoadingCard';
import { SensitiveActionModal } from '@/components/common/SensitiveActionModal';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { apiClient } from '@/lib/api/client';
import { authStorage } from '@/lib/auth/storage';
import { formatDateTime } from '@/lib/format';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import { getCopy } from '@/lib/i18n/copy';
import type { EnrollmentType, OwnershipType, PairingTokenRecord } from '@/types/models';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

export default function SupportPage() {
  const ui = getCopy(typeof navigator === 'undefined' ? 'en' : navigator.language);
  const [tenantId, setTenantId] = useState(authStorage.getProfile()?.tenantId ?? 'org-001');
  const [stateFilter, setStateFilter] = useState<'ALL' | 'SUSPECTED_LOST' | 'CONFIRMED_STOLEN' | 'RECOVERED'>('ALL');
  const [updatedFrom, setUpdatedFrom] = useState('');
  const [updatedTo, setUpdatedTo] = useState('');
  const [assignedOperatorFilter, setAssignedOperatorFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [assignmentCandidate, setAssignmentCandidate] = useState('');
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);
  const [assignLoading, setAssignLoading] = useState(false);
  const [enrollmentType, setEnrollmentType] = useState<EnrollmentType>('org_managed');
  const [ownershipType, setOwnershipType] = useState<OwnershipType>('organization_owned');
  const [selectedDeviceId, setSelectedDeviceId] = useState('');
  const [ownerSubject, setOwnerSubject] = useState('');
  const [consentVersion, setConsentVersion] = useState(new Date().toISOString().slice(0, 10));
  const [expiresInMinutes, setExpiresInMinutes] = useState('30');
  const [issuedPairing, setIssuedPairing] = useState<PairingTokenRecord | null>(null);
  const [enrollmentLoading, setEnrollmentLoading] = useState(false);
  const [enrollmentError, setEnrollmentError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<'token' | 'link' | null>(null);

  const incidentsState = useAsyncData(
    () =>
      apiClient.getIncidents({
        tenantId,
        state: stateFilter,
        updatedFrom: updatedFrom || undefined,
        updatedTo: updatedTo || undefined,
        assignedOperator: assignedOperatorFilter || undefined,
        search: search || undefined,
      }),
    [tenantId, stateFilter, updatedFrom, updatedTo, assignedOperatorFilter, search],
  );
  const notificationsState = useAsyncData(() => apiClient.getNotifications(10), [tenantId]);

  const incidents = useMemo(() => incidentsState.data ?? [], [incidentsState.data]);
  const devicesState = useAsyncData(() => apiClient.getDevices(), []);
  const devices = useMemo(() => devicesState.data ?? [], [devicesState.data]);
  const notifications = useMemo(() => notificationsState.data ?? [], [notificationsState.data]);
  const selectedIncident = useMemo(
    () => incidents.find((incident) => incident.id === selectedIncidentId) ?? incidents[0] ?? null,
    [incidents, selectedIncidentId],
  );

  useEffect(() => {
    setAssignmentCandidate(selectedIncident?.assignedOperator ?? '');
  }, [selectedIncident?.id, selectedIncident?.assignedOperator]);

  const counts = useMemo(
    () => ({
      total: incidents.length,
      suspected: incidents.filter((incident) => incident.state === 'SUSPECTED_LOST').length,
      stolen: incidents.filter((incident) => incident.state === 'CONFIRMED_STOLEN').length,
      unassigned: incidents.filter((incident) => !incident.assignedOperator).length,
    }),
    [incidents],
  );

  const assignOperator = async (reason: string) => {
    if (!selectedIncident || !assignmentCandidate.trim()) {
      setAssignError('Enter the operator subject before assigning the case.');
      return;
    }
    setAssignLoading(true);
    setAssignError(null);
    try {
      await apiClient.assignIncident(selectedIncident.id, {
        operatorSub: assignmentCandidate.trim(),
        reason,
      });
      await incidentsState.refresh();
      setAssignModalOpen(false);
    } catch (errorValue) {
      setAssignError(errorValue instanceof Error ? errorValue.message : 'Could not assign incident');
    } finally {
      setAssignLoading(false);
    }
  };

  const copyValue = async (field: 'token' | 'link', value: string) => {
    await navigator.clipboard.writeText(value);
    setCopiedField(field);
    window.setTimeout(() => setCopiedField((current) => (current === field ? null : current)), 1800);
  };

  const issuePairingToken = async () => {
    setEnrollmentLoading(true);
    setEnrollmentError(null);
    try {
      if (ownershipType === 'single_user' && !ownerSubject.trim()) {
        throw new Error(ui.support.ownerSubjectHint);
      }
      const result = await apiClient.issuePairingToken({
        orgId: tenantId,
        deviceId: selectedDeviceId || undefined,
        ownerSubject: ownerSubject.trim() || undefined,
        enrollmentType,
        ownershipType,
        consentVersion,
        expiresInMinutes: Number(expiresInMinutes) || 30,
      });
      setIssuedPairing(result);
    } catch (errorValue) {
      setEnrollmentError(errorValue instanceof Error ? errorValue.message : 'Could not issue enrollment token');
    } finally {
      setEnrollmentLoading(false);
    }
  };

  if (incidentsState.loading || devicesState.loading || notificationsState.loading) {
    return (
      <div className="page">
        <LoadingCard />
      </div>
    );
  }

  if (incidentsState.error || devicesState.error || notificationsState.error) {
    return (
      <div className="page">
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>
            {incidentsState.error ?? devicesState.error ?? notificationsState.error}
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="page container stack">
      <div>
        <h1 className="page-title">{ui.support.title}</h1>
        <p className="page-subtitle">{ui.support.subtitle}</p>
      </div>

      <div className="grid-4">
        <Card>
          <p className="text-muted" style={{ margin: 0 }}>{ui.support.totalCases}</p>
          <h2 style={{ margin: '8px 0 0' }}>{counts.total}</h2>
        </Card>
        <Card>
          <p className="text-muted" style={{ margin: 0 }}>{ui.support.suspectedLost}</p>
          <h2 style={{ margin: '8px 0 0' }}>{counts.suspected}</h2>
        </Card>
        <Card>
          <p className="text-muted" style={{ margin: 0 }}>{ui.support.stolenCases}</p>
          <h2 style={{ margin: '8px 0 0' }}>{counts.stolen}</h2>
        </Card>
        <Card>
          <p className="text-muted" style={{ margin: 0 }}>{ui.support.unassignedCases}</p>
          <h2 style={{ margin: '8px 0 0' }}>{counts.unassigned}</h2>
        </Card>
      </div>

      <Card>
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 360px' }}>
            <h2 style={{ marginTop: 0 }}>{ui.support.enrollmentTitle}</h2>
            <p className="page-subtitle">{ui.support.enrollmentSubtitle}</p>
            <div className="grid-2" style={{ marginTop: 16 }}>
              <Select
                label={ui.support.enrollmentType}
                value={enrollmentType}
                onChange={(event) => setEnrollmentType(event.target.value as EnrollmentType)}
                options={[
                  { label: 'Organization-managed', value: 'org_managed' },
                  { label: 'Owner-enrolled', value: 'owner_enrolled' },
                ]}
              />
              <Select
                label={ui.support.ownershipType}
                value={ownershipType}
                onChange={(event) => setOwnershipType(event.target.value as OwnershipType)}
                options={[
                  { label: 'Organization-owned', value: 'organization_owned' },
                  { label: 'Single-user owner', value: 'single_user' },
                ]}
              />
              <Select
                label={ui.support.existingDevice}
                value={selectedDeviceId}
                onChange={(event) => setSelectedDeviceId(event.target.value)}
                options={[
                  { label: ui.support.newDevice, value: '' },
                  ...devices.map((device) => ({
                    label: `${device.deviceName} (${device.model})`,
                    value: device.id,
                  })),
                ]}
              />
              <Input
                label={ui.support.ownerSubject}
                value={ownerSubject}
                onChange={(event) => setOwnerSubject(event.target.value)}
                placeholder="owner@example.com"
              />
              <Input label={ui.support.consentVersion} value={consentVersion} onChange={(event) => setConsentVersion(event.target.value)} />
              <Input
                label={ui.support.expiresInMinutes}
                value={expiresInMinutes}
                onChange={(event) => setExpiresInMinutes(event.target.value)}
                inputMode="numeric"
              />
            </div>

            {enrollmentError ? <p style={{ color: 'var(--danger)', marginTop: 12 }}>{enrollmentError}</p> : null}

            <Button onClick={() => void issuePairingToken()} loading={enrollmentLoading} style={{ marginTop: 16 }}>
              {ui.support.issueEnrollment}
            </Button>
          </div>

          <div style={{ flex: '1 1 340px' }}>
            <div style={{ border: '1px solid var(--border)', borderRadius: 18, padding: 18, background: 'var(--surface-muted)' }}>
              <h3 style={{ marginTop: 0, marginBottom: 8 }}>{ui.support.pairingReady}</h3>
              <p className="text-muted" style={{ marginTop: 0 }}>{ui.support.pairingHelp}</p>
              {issuedPairing ? (
                <div className="stack" style={{ gap: 14 }}>
                  <div>
                    <p className="text-muted" style={{ marginBottom: 6 }}>{ui.support.pairingToken}</p>
                    <code style={{ display: 'block', wordBreak: 'break-all', fontSize: 13 }}>{issuedPairing.token}</code>
                    <Button variant="ghost" onClick={() => void copyValue('token', issuedPairing.token)} style={{ marginTop: 8 }}>
                      {copiedField === 'token' ? ui.support.copied : ui.support.copyToken}
                    </Button>
                  </div>
                  <div>
                    <p className="text-muted" style={{ marginBottom: 6 }}>{ui.support.pairingLink}</p>
                    <code style={{ display: 'block', wordBreak: 'break-all', fontSize: 13 }}>{issuedPairing.pairingUri}</code>
                    <Button variant="ghost" onClick={() => void copyValue('link', issuedPairing.pairingUri)} style={{ marginTop: 8 }}>
                      {copiedField === 'link' ? ui.support.copied : ui.support.copyLink}
                    </Button>
                  </div>
                  <p className="text-muted" style={{ margin: 0 }}>
                    {ui.support.expiresAt}: {formatDateTime(issuedPairing.expiresAt)}
                  </p>
                </div>
              ) : (
                <p className="text-muted" style={{ marginBottom: 0 }}>
                  Issue a token here, then paste it into the Android enrollment screen or hand the pairing link to the operator managing setup.
                </p>
              )}
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <h2 style={{ marginTop: 0 }}>{ui.support.filtersTitle}</h2>
        <div className="grid-2">
          <Input label={ui.support.tenant} value={tenantId} onChange={(event) => setTenantId(event.target.value)} />
          <Select
            label={ui.support.caseState}
            value={stateFilter}
            onChange={(event) => setStateFilter(event.target.value as typeof stateFilter)}
            options={[
              { label: ui.support.allStates, value: 'ALL' },
              { label: ui.support.suspectedLost, value: 'SUSPECTED_LOST' },
              { label: ui.support.confirmedStolen, value: 'CONFIRMED_STOLEN' },
              { label: ui.support.recovered, value: 'RECOVERED' },
            ]}
          />
          <Input label={ui.support.updatedFrom} value={updatedFrom} onChange={(event) => setUpdatedFrom(event.target.value)} />
          <Input label={ui.support.updatedTo} value={updatedTo} onChange={(event) => setUpdatedTo(event.target.value)} />
          <Input label={ui.support.assignedOperator} value={assignedOperatorFilter} onChange={(event) => setAssignedOperatorFilter(event.target.value)} />
          <Input label={ui.support.search} value={search} onChange={(event) => setSearch(event.target.value)} />
        </div>
      </Card>

      <Card>
        <DataTable
          rows={incidents}
          rowKey={(incident) => incident.id}
          columns={[
            {
              key: 'case',
              header: ui.support.caseLabel,
              cell: (incident) => (
                <button
                  type="button"
                  onClick={() => setSelectedIncidentId(incident.id)}
                  style={{ border: 0, background: 'transparent', padding: 0, textAlign: 'left', color: 'var(--text)', cursor: 'pointer' }}
                  aria-label={`${ui.support.caseLabel}: ${incident.title}`}
                >
                  <strong>{incident.title}</strong>
                  <span className="text-muted" style={{ display: 'block', fontSize: 12 }}>
                    {incident.id}
                  </span>
                </button>
              ),
            },
            { key: 'tenant', header: ui.support.tenant, cell: (incident) => incident.orgId },
            {
              key: 'state',
              header: ui.support.stateLabel,
              cell: (incident) => (
                <Badge variant={incident.state === 'CONFIRMED_STOLEN' ? 'danger' : 'warning'}>{incident.state}</Badge>
              ),
            },
            {
              key: 'operator',
              header: ui.support.operatorLabel,
              cell: (incident) => incident.assignedOperator ?? ui.support.unassigned,
            },
            { key: 'updated', header: ui.support.updatedLabel, cell: (incident) => formatDateTime(incident.updatedAt) },
          ]}
          emptyMessage={ui.support.noCases}
        />
      </Card>

      <Card>
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ marginTop: 0, marginBottom: 8 }}>Recent notifications and escalation alerts</h2>
            <p className="page-subtitle">
              Incident escalations and device push attempts now show up here with an explicit sent or failed result.
            </p>
          </div>
          <Badge variant="neutral">{notifications.length} recent events</Badge>
        </div>
        <div className="stack" style={{ marginTop: 12 }}>
          {notifications.length === 0 ? <p className="text-muted">No recent notifications for this tenant yet.</p> : null}
          {notifications.map((event) => (
            <div key={event.id} style={{ borderLeft: '2px solid var(--border)', paddingLeft: 12 }}>
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <p style={{ margin: 0, fontWeight: 700 }}>{String(event.payload.title ?? event.template)}</p>
                <Badge variant={event.status === 'FAILED' ? 'danger' : 'success'}>{event.status}</Badge>
              </div>
              <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
                {formatDateTime(event.createdAt)} • {event.channel}
                {event.incidentId ? ` • incident ${event.incidentId}` : ''}
              </p>
              <p style={{ margin: '6px 0 0' }}>{String(event.payload.body ?? 'Notification event')}</p>
              {event.errorMessage ? (
                <p style={{ margin: '6px 0 0', color: 'var(--danger)', fontSize: 13 }}>{event.errorMessage}</p>
              ) : null}
            </div>
          ))}
        </div>
      </Card>

      {selectedIncident ? (
        <Card>
          <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h2 style={{ marginTop: 0, marginBottom: 8 }}>{ui.support.selectedCase}</h2>
              <p className="text-muted" style={{ margin: 0 }}>
                {selectedIncident.title} • {selectedIncident.state}
              </p>
              <p className="text-muted" style={{ marginTop: 8 }}>
                {ui.support.operatorLabel}: <strong>{selectedIncident.assignedOperator ?? ui.support.unassigned}</strong>
              </p>
              <p className="text-muted" style={{ marginTop: 8, marginBottom: 0 }}>{ui.support.selectedCaseHint}</p>
            </div>
            <Link href="/incidents" style={{ color: 'var(--primary)', fontWeight: 600 }}>
              Open detailed case view
            </Link>
          </div>

          {assignError ? <p style={{ color: 'var(--danger)' }}>{assignError}</p> : null}

          <div className="row" style={{ marginTop: 12 }}>
            <Input label={ui.support.assignField} value={assignmentCandidate} onChange={(event) => setAssignmentCandidate(event.target.value)} />
            <Button style={{ marginTop: 23 }} onClick={() => setAssignModalOpen(true)} disabled={!assignmentCandidate.trim()}>
              {ui.support.assignButton}
            </Button>
          </div>
        </Card>
      ) : null}

      <SensitiveActionModal
        open={assignModalOpen}
        title={ui.support.assignTitle}
        description={ui.support.assignDescription}
        confirmLabel={ui.support.assignConfirm}
        loading={assignLoading}
        onCancel={() => setAssignModalOpen(false)}
        onConfirm={assignOperator}
      />
    </div>
  );
}
