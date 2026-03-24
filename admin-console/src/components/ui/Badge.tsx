import type { CSSProperties } from 'react';

type BadgeVariant = 'neutral' | 'success' | 'warning' | 'danger' | 'approximate' | 'moderate' | 'precise' | 'stale' | 'offline';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  style?: CSSProperties;
}

const colorMap: Record<BadgeVariant, string> = {
  neutral: 'var(--text-muted)',
  success: 'var(--success)',
  warning: 'var(--warning)',
  danger: 'var(--danger)',
  approximate: 'var(--approximate)',
  moderate: 'var(--moderate)',
  precise: 'var(--precise)',
  stale: '#c2410c',
  offline: '#64748b',
};

export function Badge({ children, variant = 'neutral', style }: BadgeProps) {
  const color = colorMap[variant];

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 10px',
        borderRadius: 999,
        border: `1px solid color-mix(in srgb, ${color} 45%, transparent)`,
        background: `color-mix(in srgb, ${color} 14%, transparent)`,
        fontWeight: 600,
        fontSize: 12,
        color,
        ...style,
      }}
    >
      {children}
    </span>
  );
}
