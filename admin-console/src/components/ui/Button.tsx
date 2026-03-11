import { ButtonHTMLAttributes } from 'react';

type ButtonVariant = 'primary' | 'ghost' | 'danger';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
}

export function Button({ variant = 'primary', loading = false, children, style, ...props }: ButtonProps) {
  const backgroundByVariant: Record<ButtonVariant, string> = {
    primary: 'var(--primary)',
    ghost: 'var(--surface-muted)',
    danger: 'var(--danger)',
  };

  const colorByVariant: Record<ButtonVariant, string> = {
    primary: 'var(--primary-contrast)',
    ghost: 'var(--text)',
    danger: '#fff',
  };

  return (
    <button
      {...props}
      disabled={loading || props.disabled}
      style={{
        border: `1px solid ${variant === 'ghost' ? 'var(--border)' : 'transparent'}`,
        background: backgroundByVariant[variant],
        color: colorByVariant[variant],
        borderRadius: 10,
        padding: '10px 14px',
        cursor: loading ? 'default' : 'pointer',
        fontWeight: 600,
        opacity: loading ? 0.8 : 1,
        ...style,
      }}
    >
      {loading ? 'Working...' : children}
    </button>
  );
}
