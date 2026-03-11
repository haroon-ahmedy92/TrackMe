'use client';

import { LoadingCard } from '@/components/common/LoadingCard';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { Input } from '@/components/ui/Input';
import { apiClient } from '@/lib/api/client';
import { formatDateTime } from '@/lib/format';
import { useAsyncData } from '@/lib/hooks/useAsyncData';
import { useMemo, useState } from 'react';

export default function AuditPage() {
  const { data, loading, error, refresh } = useAsyncData(() => apiClient.getAuditLogs(), []);
  const [filter, setFilter] = useState('');

  const logs = useMemo(() => {
    const all = data ?? [];
    if (!filter.trim()) {
      return all;
    }
    const q = filter.toLowerCase();
    return all.filter(
      (item) =>
        item.action.toLowerCase().includes(q) ||
        item.actor.toLowerCase().includes(q) ||
        item.targetId.toLowerCase().includes(q),
    );
  }, [data, filter]);

  if (loading) {
    return (
      <div className="page">
        <LoadingCard />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <Card>
          <p style={{ margin: 0, color: 'var(--danger)' }}>{error}</p>
          <Button style={{ marginTop: 10 }} onClick={() => void refresh()}>
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="page container stack">
      <div>
        <h1 className="page-title">Audit Log Viewer</h1>
        <p className="page-subtitle">Immutable record of sensitive actions, reasons, actors, and timestamps.</p>
      </div>

      <Card>
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <Input
            label="Filter"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Search actor, action, or target"
          />
          <Badge variant="neutral">{logs.length} records</Badge>
        </div>

        <div style={{ marginTop: 12 }}>
          <DataTable
            rows={logs}
            rowKey={(item) => item.id}
            columns={[
              {
                key: 'time',
                header: 'Timestamp',
                cell: (item) => formatDateTime(item.createdAt),
              },
              {
                key: 'actor',
                header: 'Actor',
                cell: (item) => <span className="code">{item.actor}</span>,
              },
              {
                key: 'action',
                header: 'Action',
                cell: (item) => <Badge variant="warning">{item.action}</Badge>,
              },
              {
                key: 'target',
                header: 'Target',
                cell: (item) => (
                  <div className="stack" style={{ gap: 4 }}>
                    <span>{item.targetType}</span>
                    <span className="code" style={{ fontSize: 12 }}>
                      {item.targetId}
                    </span>
                  </div>
                ),
              },
              {
                key: 'reason',
                header: 'Reason',
                cell: (item) => item.reason ?? '-',
              },
            ]}
          />
        </div>
      </Card>
    </div>
  );
}
