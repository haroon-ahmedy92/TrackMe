import { CSSProperties } from 'react';

interface CardProps {
  children: React.ReactNode;
  style?: CSSProperties;
}

export function Card({ children, style }: CardProps) {
  return (
    <section
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
