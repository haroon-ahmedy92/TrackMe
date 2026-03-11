'use client';

import { authStorage } from '@/lib/auth/storage';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    const token = authStorage.getToken();
    router.replace(token ? '/devices' : '/login');
  }, [router]);

  return <div className="page text-muted">Redirecting...</div>;
}
