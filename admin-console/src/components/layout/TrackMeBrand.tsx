type TrackMeBrandProps = {
  compact?: boolean;
  subtitle?: string;
};

export function TrackMeBrand({ compact = false, subtitle }: TrackMeBrandProps) {
  const iconSize = compact ? 40 : 56;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: compact ? 10 : 14,
      }}
    >
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 64 64"
        role="img"
        aria-label="TrackMe logo"
        className="brand-mark"
      >
        <defs>
          <linearGradient id="trackme-pin-gradient" x1="10" x2="42" y1="54" y2="10" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#5a1bff" />
            <stop offset="52%" stopColor="#c02cff" />
            <stop offset="100%" stopColor="#ff5d4d" />
          </linearGradient>
          <linearGradient id="trackme-arrow-gradient" x1="19" x2="57" y1="44" y2="8" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#8f2cff" />
            <stop offset="58%" stopColor="#ff3d75" />
            <stop offset="100%" stopColor="#ff9a1f" />
          </linearGradient>
        </defs>

        <path
          d="M31.6 6C21 6 12.4 14.5 12.4 25.1c0 13.8 15.5 30.5 18 33.1.7.8 1.9.8 2.7 0 2.4-2.6 18-19.3 18-33.1C50.9 14.5 42.3 6 31.6 6Zm0 28.3c-5.1 0-9.2-4.1-9.2-9.2S26.5 16 31.6 16s9.2 4.1 9.2 9.2-4.1 9.1-9.2 9.1Z"
          fill="url(#trackme-pin-gradient)"
          opacity="0.95"
        />
        <path
          d="M22 49.8c-.7 0-1.3-.3-1.7-.9-1.8-2.7-2.8-5.9-2.8-9.1 0-8 5.9-15 13.8-16.2 2.8-.4 5.5.1 8 1.2l-4.2 3.8a10.9 10.9 0 0 0-3.2-.1c-5.7.9-9.6 6.4-8.7 12 .4 2.3 1.4 4.4 2.9 6.2l7.1-6.4c1.2-1 2.8-1.2 4.1-.3 1.4.8 2 2.4 1.7 4l-1.2 6.4a2 2 0 0 1-1.6 1.6l-13.8-2.2-.4.1Z"
          fill="#26194a"
          opacity="0.42"
        />
        <path
          d="M21.7 49.5c-.7 0-1.3-.3-1.7-.9-2.1-3-3.1-6.3-3.1-10 0-8.9 6.4-16.4 15.1-18 3.5-.6 6.8 0 10 1.6l5.4-4.8c.8-.8 2.1-.7 2.9.1.7.8.7 2.1-.1 2.8l-7 6.3a2 2 0 0 1-2.3.2c-2.8-1.6-5.7-2.2-8.6-1.7-6.8 1.2-11.6 7.1-11.6 14.1 0 2.6.7 5 2 7.2L40.7 30c1.8-1.6 4.4-1.9 6.6-.7L45 16.7l12.1 1.9-1.1 1-6.1 5.5-2.7 14.7a2 2 0 0 1-1.7 1.6 2 2 0 0 1-1.9-.9l-1.2-1.8-19.4 17.5c-.4.2-.8.3-1.3.3Z"
          fill="url(#trackme-arrow-gradient)"
        />
      </svg>

      <div style={{ minWidth: 0 }}>
        <div className="brand-wordmark" style={{ fontSize: compact ? 24 : 34 }}>
          <span className="brand-track">Track</span>
          <span className="brand-me">Me</span>
        </div>
        {subtitle ? (
          <p
            className="text-muted"
            style={{
              margin: compact ? '2px 0 0' : '4px 0 0',
              fontSize: compact ? 12 : 13,
            }}
          >
            {subtitle}
          </p>
        ) : null}
      </div>
    </div>
  );
}
