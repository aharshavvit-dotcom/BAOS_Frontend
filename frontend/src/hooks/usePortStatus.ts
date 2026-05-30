import { useEffect, useState } from 'react';
import { getPortStatus, type PortStatus } from '@/services/portService';

export function usePortStatus(portCode: string) {
  const [data, setData] = useState<PortStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setLoading(true);
    getPortStatus(portCode)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err : new Error('Unable to load port status')))
      .finally(() => setLoading(false));
  }, [portCode]);

  return { data, loading, error };
}
