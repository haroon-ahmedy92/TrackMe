'use client';

import { Modal } from '@/components/ui/Modal';
import { Textarea } from '@/components/ui/Textarea';
import { useState } from 'react';

interface SensitiveActionModalProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  danger?: boolean;
  loading?: boolean;
  onCancel: () => void;
  onConfirm: (reason: string) => Promise<void>;
}

export function SensitiveActionModal({
  open,
  title,
  description,
  confirmLabel,
  danger,
  loading,
  onCancel,
  onConfirm,
}: SensitiveActionModalProps) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  return (
    <Modal
      open={open}
      title={title}
      description={description}
      confirmLabel={confirmLabel}
      danger={danger}
      loading={loading}
      confirmDisabled={reason.trim().length < 8}
      onCancel={() => {
        setReason('');
        setError(null);
        onCancel();
      }}
      onConfirm={async () => {
        if (reason.trim().length < 8) {
          setError('Provide a clear reason (minimum 8 characters).');
          return;
        }

        setError(null);
        await onConfirm(reason.trim());
        setReason('');
      }}
    >
      <Textarea
        label="Reason (required for audit trail)"
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder="State the reason and expected impact"
      />
      {error ? (
        <p
          style={{
            margin: '8px 0 0',
            color: 'var(--danger)',
            fontSize: 13,
          }}
        >
          {error}
        </p>
      ) : null}
    </Modal>
  );
}
