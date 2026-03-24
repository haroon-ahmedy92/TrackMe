'use client';

import { LoadingCard } from '@/components/common/LoadingCard';
import { SensitiveActionModal } from '@/components/common/SensitiveActionModal';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { apiClient } from '@/lib/api/client';
import { formatDateTime } from '@/lib/format';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import { useMemo, useState } from 'react';

export default function RemoteActionsPage() {
  const actionState = useAsyncData(() => apiClient.getRemoteActions(), []);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [modal, setModal] = useState<'approve' | 'reject' | null>(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const actions = useMemo(() => actionState.data ?? [], [actionState.data]);
  const selectedAction = useMemo(
    () => actions.find((action) => action.id === selectedId) ?? actions[0] ?? null,
    [actions, selectedId],
  );

  const runAction = async (runner: () => Promise<void>) => {
    setProcessing(true);
    setError(null);
    try {
      await runner();
      await actionState.refresh();
      setModal(null);
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : 'Action failed');
    } finally {
      setProcessing(false);
    }
  };

  if (actionState.loading) {
    return (
      <div className="page">
        <LoadingCard />
      </div>
    );
  }

  if (actionState.error) {
    return (
      <div className="page">
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{actionState.error}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="page container stack">
      <div>
        <h1 className="page-title">Remote Action Approvals</h1>
        <p className="page-subtitle">
          Sensitive commands require explicit approval/rejection with audit reason. Device online state and last check-in are always visible.
        </p>
      </div>

      {error ? (
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{error}</p>
        </Card>
      ) : null}

      <Card>
        <DataTable
          rows={actions}
          rowKey={(action) => action.id}
          columns={[
            {
              key: 'action',
              header: 'Action',
              cell: (action) => (
                <button
                  type="button"
                  onClick={() => setSelectedId(action.id)}
                  style={{ border: 0, background: 'transparent', padding: 0, cursor: 'pointer', textAlign: 'left' }}
                >
                  <span style={{ fontWeight: 700 }}>{action.type}</span>
                  <span className="text-muted" style={{ display: 'block', fontSize: 12 }}>
                    {action.deviceName}
                  </span>
                </button>
              ),
            },
            {
              key: 'status',
              header: 'Status',
              cell: (action) => (
                <Badge variant={action.status === 'PENDING' ? 'warning' : action.status === 'REJECTED' ? 'danger' : 'success'}>
                  {action.status}
                </Badge>
              ),
            },
            {
              key: 'connectivity',
              header: 'Device Availability',
              cell: (action) => (
                <div className="stack" style={{ gap: 4 }}>
                  <Badge variant={action.deviceOnline ? 'success' : 'warning'}>
                    {action.deviceOnline ? 'Online' : 'Offline'}
                  </Badge>
                  <span className="text-muted" style={{ fontSize: 12 }}>
                    Last check-in: {formatDateTime(action.lastCheckInAt)}
                  </span>
                </div>
              ),
            },
            {
              key: 'requested',
              header: 'Requested',
              cell: (action) => `${formatDateTime(action.requestedAt)} by ${action.requestedBy}`,
            },
            {
              key: 'approval',
              header: 'Approval',
              cell: (action) =>
                action.requiredApprovals ? `${action.approvalCount ?? 0}/${action.requiredApprovals} approvals` : 'Not required',
            },
          ]}
          emptyMessage="No remote actions pending"
        />
      </Card>

      {selectedAction ? (
        <Card>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <h2 style={{ margin: 0 }}>Selected Action Details</h2>
            <Badge variant={selectedAction.deviceOnline ? 'success' : 'warning'}>
              Device {selectedAction.deviceOnline ? 'Online' : 'Offline'}
            </Badge>
          </div>
          <p className="text-muted" style={{ marginTop: 8 }}>
            Device: {selectedAction.deviceName} • Last check-in: {formatDateTime(selectedAction.lastCheckInAt)}
          </p>
          <p className="text-muted" style={{ marginTop: 6 }}>Reason: {selectedAction.reason}</p>
          {selectedAction.policyReason ? (
            <p className="warning-note" style={{ marginTop: 12, marginBottom: 0 }}>
              Policy: {selectedAction.policyReason}
              {selectedAction.requiredApprovals ? ` (${selectedAction.approvalCount ?? 0}/${selectedAction.requiredApprovals} approvals)` : ''}
            </p>
          ) : null}

          <div className="row" style={{ marginTop: 12 }}>
            <Button onClick={() => setModal('approve')} disabled={selectedAction.status !== 'PENDING'}>
              Approve
            </Button>
            <Button variant="danger" onClick={() => setModal('reject')} disabled={selectedAction.status !== 'PENDING'}>
              Reject
            </Button>
          </div>
        </Card>
      ) : null}

      <SensitiveActionModal
        open={modal === 'approve'}
        title="Approve Remote Action"
        description="Confirm this command is lawful and necessary for recovery/protection."
        confirmLabel="Approve"
        loading={processing}
        onCancel={() => setModal(null)}
        onConfirm={async (reason) => {
          if (!selectedAction) {
            return;
          }
          await runAction(async () => {
            await apiClient.approveRemoteAction(selectedAction.id, reason);
          });
        }}
      />

      <SensitiveActionModal
        open={modal === 'reject'}
        title="Reject Remote Action"
        description="Provide a reason so requesters understand why this action is denied."
        confirmLabel="Reject"
        danger
        loading={processing}
        onCancel={() => setModal(null)}
        onConfirm={async (reason) => {
          if (!selectedAction) {
            return;
          }
          await runAction(async () => {
            await apiClient.rejectRemoteAction(selectedAction.id, reason);
          });
        }}
      />
    </div>
  );
}
