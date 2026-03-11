import { SelectHTMLAttributes } from 'react';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: Array<{ label: string; value: string }>;
}

export function Select({ label, options, style, ...props }: SelectProps) {
  return (
    <label className="stack" style={{ gap: 6 }}>
      <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{label}</span>
      <select
        {...props}
        style={{
          border: '1px solid var(--border)',
          borderRadius: 10,
          padding: '10px 12px',
          background: 'var(--surface)',
          color: 'var(--text)',
          ...style,
        }}
      >
        {options.map((option) => (
          <option value={option.value} key={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
