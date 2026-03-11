import { ApiError } from '@/lib/api/errors';
import { authStorage } from '@/lib/auth/storage';

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

const request = async <T>(input: string, init?: RequestInit): Promise<T> => {
  const token = authStorage.getToken();

  const response = await fetch(`${baseUrl}${input}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(payload?.detail ?? 'API request failed', response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
};

export const httpClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'DELETE',
      body: body ? JSON.stringify(body) : undefined,
    }),
};
