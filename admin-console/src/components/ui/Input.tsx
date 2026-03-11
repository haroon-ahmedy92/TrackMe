import { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Input({ label, style, ...props }: InputProps) {
  return (
    <label className="stack" style={{ gap: 6 }}>
      <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{label}</span>
      <input
        {...props}
        style={{
          border: '1px solid var(--border)',
          borderRadius: 10,
          padding: '10px 12px',
          background: 'var(--surface)',
          color: 'var(--text)',
          ...style,
        }}
      />
    </label>
  );
}
