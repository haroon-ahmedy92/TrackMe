'use client';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { apiClient } from '@/lib/api/client';
import { authStorage } from '@/lib/auth/storage';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('admin@org.tz');
  const [password, setPassword] = useState('password123');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const result = await apiClient.login({ email, password });
      authStorage.setAuth(result.accessToken, result.profile);
      router.replace('/devices');
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : 'Unable to sign in');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        padding: 20,
      }}
    >
      <Card style={{ width: '100%', maxWidth: 420 }}>
        <h1 className="page-title">Sign in</h1>
        <p className="page-subtitle">
          Admin access for organization-managed and explicitly enrolled devices only.
        </p>

        <form onSubmit={onSubmit} className="stack" style={{ marginTop: 18 }}>
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {error ? (
            <p
              style={{
                margin: 0,
                padding: '10px 12px',
                borderRadius: 10,
                border: '1px solid color-mix(in srgb, var(--danger) 40%, transparent)',
                background: 'color-mix(in srgb, var(--danger) 15%, transparent)',
              }}
            >
              {error}
            </p>
          ) : null}

          <Button type="submit" loading={submitting}>
            Sign in
          </Button>
        </form>

        <p className="text-muted" style={{ marginTop: 14, fontSize: 12 }}>
          Local development uses mock auth by default (`NEXT_PUBLIC_USE_MOCKS=true`).
        </p>
      </Card>
    </div>
  );
}
