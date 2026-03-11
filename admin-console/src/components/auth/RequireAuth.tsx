'use client';

import { authStorage } from '@/lib/auth/storage';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = authStorage.getToken();
    if (!token && pathname !== '/login') {
      router.replace('/login');
      return;
    }
    if (token && pathname === '/login') {
      router.replace('/devices');
      return;
    }
    setReady(true);
  }, [pathname, router]);

  if (!ready) {
    return <div className="page text-muted">Checking session...</div>;
  }

  return <>{children}</>;
}
