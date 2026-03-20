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
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

export default function SupportPage() {
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

  const incidents = incidentsState.data ?? [];
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

  if (incidentsState.loading) {
    return (
      <div className="page">
        <LoadingCard />
      </div>
    );
  }

  if (incidentsState.error) {
    return (
      <div className="page">
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{incidentsState.error}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="page container stack">
      <div>
        <h1 className="page-title">Operator Support Dashboard</h1>
        <p className="page-subtitle">
          Filter case queues, assign operators, and review export-ready incidents without mixing mutable notes into immutable audit evidence.
        </p>
      </div>

      <div className="grid-4">
        <Card>
          <p className="text-muted" style={{ margin: 0 }}>Total cases</p>
          <h2 style={{ margin: '8px 0 0' }}>{counts.total}</h2>
        </Card>
        <Card>
          <p className="text-muted" style={{ margin: 0 }}>Suspected lost</p>
          <h2 style={{ margin: '8px 0 0' }}>{counts.suspected}</h2>
        </Card>
        <Card>
          <p className="text-muted" style={{ margin: 0 }}>Confirmed stolen</p>
          <h2 style={{ margin: '8px 0 0' }}>{counts.stolen}</h2>
        </Card>
        <Card>
          <p className="text-muted" style={{ margin: 0 }}>Unassigned</p>
          <h2 style={{ margin: '8px 0 0' }}>{counts.unassigned}</h2>
        </Card>
      </div>

      <Card>
        <h2 style={{ marginTop: 0 }}>Filters</h2>
        <div className="grid-2">
          <Input label="Tenant" value={tenantId} onChange={(event) => setTenantId(event.target.value)} />
          <Select
            label="Case state"
            value={stateFilter}
            onChange={(event) => setStateFilter(event.target.value as typeof stateFilter)}
            options={[
              { label: 'All states', value: 'ALL' },
              { label: 'Suspected lost', value: 'SUSPECTED_LOST' },
              { label: 'Confirmed stolen', value: 'CONFIRMED_STOLEN' },
              { label: 'Recovered', value: 'RECOVERED' },
            ]}
          />
          <Input label="Updated from (ISO)" value={updatedFrom} onChange={(event) => setUpdatedFrom(event.target.value)} />
          <Input label="Updated to (ISO)" value={updatedTo} onChange={(event) => setUpdatedTo(event.target.value)} />
          <Input
            label="Assigned operator"
            value={assignedOperatorFilter}
            onChange={(event) => setAssignedOperatorFilter(event.target.value)}
          />
          <Input label="Search" value={search} onChange={(event) => setSearch(event.target.value)} />
        </div>
      </Card>

      <Card>
        <DataTable
          rows={incidents}
          rowKey={(incident) => incident.id}
          columns={[
            {
              key: 'case',
              header: 'Case',
              cell: (incident) => (
                <button
                  type="button"
                  onClick={() => setSelectedIncidentId(incident.id)}
                  style={{ border: 0, background: 'transparent', padding: 0, textAlign: 'left', color: 'var(--text)', cursor: 'pointer' }}
                >
                  <strong>{incident.title}</strong>
                  <span className="text-muted" style={{ display: 'block', fontSize: 12 }}>
                    {incident.id}
                  </span>
                </button>
              ),
            },
            { key: 'tenant', header: 'Tenant', cell: (incident) => incident.orgId },
            {
              key: 'state',
              header: 'State',
              cell: (incident) => (
                <Badge variant={incident.state === 'CONFIRMED_STOLEN' ? 'danger' : 'warning'}>{incident.state}</Badge>
              ),
            },
            {
              key: 'operator',
              header: 'Assigned Operator',
              cell: (incident) => incident.assignedOperator ?? 'Unassigned',
            },
            { key: 'updated', header: 'Updated', cell: (incident) => formatDateTime(incident.updatedAt) },
          ]}
          emptyMessage="No cases matched the current filters."
        />
      </Card>

      {selectedIncident ? (
        <Card>
          <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h2 style={{ marginTop: 0, marginBottom: 8 }}>Selected Support Case</h2>
              <p className="text-muted" style={{ margin: 0 }}>
                {selectedIncident.title} • {selectedIncident.state}
              </p>
              <p className="text-muted" style={{ marginTop: 8 }}>
                Current operator: <strong>{selectedIncident.assignedOperator ?? 'Unassigned'}</strong>
              </p>
            </div>
            <Link href="/incidents" style={{ color: 'var(--primary)', fontWeight: 600 }}>
              Open detailed case view
            </Link>
          </div>

          {assignError ? <p style={{ color: 'var(--danger)' }}>{assignError}</p> : null}

          <div className="row" style={{ marginTop: 12 }}>
            <Input
              label="Assign operator subject"
              value={assignmentCandidate}
              onChange={(event) => setAssignmentCandidate(event.target.value)}
            />
            <Button style={{ marginTop: 23 }} onClick={() => setAssignModalOpen(true)} disabled={!assignmentCandidate.trim()}>
              Assign Case
            </Button>
          </div>
        </Card>
      ) : null}

      <SensitiveActionModal
        open={assignModalOpen}
        title="Assign Case Operator"
        description="Assignment changes are audited so support teams can review who took ownership of the case."
        confirmLabel="Assign Operator"
        loading={assignLoading}
        onCancel={() => setAssignModalOpen(false)}
        onConfirm={assignOperator}
      />
    </div>
  );
}
