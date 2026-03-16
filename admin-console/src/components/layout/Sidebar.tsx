'use client';

import { TrackMeBrand } from '@/components/layout/TrackMeBrand';
import { authStorage } from '@/lib/auth/storage';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

interface NavItem {
  label: string;
  href: string;
}

const navItems: NavItem[] = [
  { label: 'Device Inventory', href: '/devices' },
  { label: 'Map View', href: '/map' },
  { label: 'Incidents', href: '/incidents' },
  { label: 'Geofences', href: '/geofences' },
  { label: 'Audit Logs', href: '/audit' },
  { label: 'Remote Actions', href: '/remote-actions' },
  { label: 'Settings', href: '/settings' },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside
      style={{
        width: 250,
        borderRight: '1px solid var(--border)',
        background: 'var(--surface)',
        minHeight: '100vh',
        padding: 16,
      }}
    >
      <div style={{ marginBottom: 20 }}>
        <TrackMeBrand compact subtitle="Device Recovery & Protection" />
      </div>

      <nav className="stack">
        {navItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                border: `1px solid ${active ? 'var(--primary)' : 'var(--border)'}`,
                background: active ? 'color-mix(in srgb, var(--primary) 13%, transparent)' : 'transparent',
                borderRadius: 10,
                padding: '10px 12px',
                fontWeight: active ? 700 : 500,
                fontSize: 14,
              }}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <button
        type="button"
        onClick={() => {
          authStorage.clear();
          router.replace('/login');
        }}
        style={{
          marginTop: 24,
          border: '1px solid var(--border)',
          background: 'var(--surface-muted)',
          color: 'var(--text)',
          borderRadius: 10,
          width: '100%',
          padding: '10px 12px',
          textAlign: 'left',
          cursor: 'pointer',
        }}
      >
        Sign Out
      </button>
    </aside>
  );
}
