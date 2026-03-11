'use client';

import { Button } from '@/components/ui/Button';

interface ModalProps {
  open: boolean;
  title: string;
  description?: string;
  children?: React.ReactNode;
  confirmLabel?: string;
  confirmDisabled?: boolean;
  danger?: boolean;
  loading?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function Modal({
  open,
  title,
  description,
  children,
  confirmLabel = 'Confirm',
  confirmDisabled,
  danger,
  loading,
  onCancel,
  onConfirm,
}: ModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgb(0 0 0 / 48%)',
        display: 'grid',
        placeItems: 'center',
        padding: 18,
        zIndex: 99,
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 520,
          borderRadius: 12,
          border: '1px solid var(--border)',
          background: 'var(--surface)',
          boxShadow: 'var(--shadow)',
          padding: 18,
        }}
      >
        <h3 style={{ margin: 0 }}>{title}</h3>
        {description ? <p className="page-subtitle">{description}</p> : null}
        {children ? <div style={{ marginTop: 10 }}>{children}</div> : null}
        <div className="row" style={{ justifyContent: 'flex-end', marginTop: 14 }}>
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} loading={loading} disabled={confirmDisabled}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
