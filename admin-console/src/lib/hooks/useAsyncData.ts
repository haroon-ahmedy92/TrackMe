'use client';

import { useCallback, useEffect, useState } from 'react';

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export const useAsyncData = <T,>(loader: () => Promise<T>, deps: unknown[] = []): AsyncState<T> => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await loader();
      setData(result);
    } catch (errorValue) {
      const message = errorValue instanceof Error ? errorValue.message : 'Unexpected error';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { data, loading, error, refresh };
};
