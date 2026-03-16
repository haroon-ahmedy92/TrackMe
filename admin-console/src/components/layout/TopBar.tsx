'use client';

import { TrackMeBrand } from '@/components/layout/TrackMeBrand';
import { authStorage } from '@/lib/auth/storage';

export function TopBar() {
  const profile = authStorage.getProfile();

  return (
    <header
      style={{
        height: 64,
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0 20px',
      }}
    >
      <div>
        <TrackMeBrand compact subtitle="Visible, consent-based protection workflows only" />
      </div>
      <div style={{ textAlign: 'right' }}>
        <p style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>{profile?.fullName ?? 'Guest'}</p>
        <p className="text-muted" style={{ margin: '2px 0 0', fontSize: 12 }}>
          {profile?.role ?? 'unknown'}
        </p>
      </div>
    </header>
  );
}
