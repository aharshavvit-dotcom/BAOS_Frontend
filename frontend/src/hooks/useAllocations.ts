import { useEffect, useState } from 'react';
import { getAllocations, type AllocationSummary } from '@/services/allocationService';

export function useAllocations() {
  const [data, setData] = useState<AllocationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    getAllocations()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err : new Error('Unable to load allocations')))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
