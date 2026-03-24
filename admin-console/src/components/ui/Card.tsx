import { CSSProperties } from 'react';

interface CardProps {
  children: React.ReactNode;
  style?: CSSProperties;
  className?: string;
}

export function Card({ children, style, className }: CardProps) {
  return (
    <section
      className={className}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        boxShadow: 'var(--shadow)',
        padding: 16,
        ...style,
      }}
    >
      {children}
    </section>
  );
}
