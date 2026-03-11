export function Skeleton({ height = 16, width = '100%' }: { height?: number; width?: string | number }) {
  return (
    <div
      style={{
        height,
        width,
        borderRadius: 8,
        background:
          'linear-gradient(90deg, color-mix(in srgb, var(--surface-muted) 65%, transparent), color-mix(in srgb, var(--surface) 90%, transparent), color-mix(in srgb, var(--surface-muted) 65%, transparent))',
        backgroundSize: '220px 100%',
        animation: 'loadingShimmer 1.4s infinite',
      }}
    />
  );
}
