import { useEffect, useState } from 'react';
import { getBerths } from '@/services/berthService';
import type { BerthConfig } from '@/services/ports';

export function useBerths(portCode: string) {
  const [data, setData] = useState<BerthConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setLoading(true);
    getBerths(portCode)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err : new Error('Unable to load berths')))
      .finally(() => setLoading(false));
  }, [portCode]);

  return { data, loading, error };
}
