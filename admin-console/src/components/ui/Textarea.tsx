import { TextareaHTMLAttributes } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
}

export function Textarea({ label, style, ...props }: TextareaProps) {
  return (
    <label className="stack" style={{ gap: 6 }}>
      <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{label}</span>
      <textarea
        {...props}
        style={{
          border: '1px solid var(--border)',
          borderRadius: 10,
          padding: '10px 12px',
          background: 'var(--surface)',
          color: 'var(--text)',
          minHeight: 100,
          ...style,
        }}
      />
    </label>
  );
}
