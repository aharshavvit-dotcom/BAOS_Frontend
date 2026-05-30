import { apiFetch } from './api';

export interface AllocationSummary {
  id: string;
  status: string;
  [key: string]: unknown;
}

export function getAllocations(): Promise<AllocationSummary[]> {
  return apiFetch<AllocationSummary[]>('/api/v1/allocations');
}
