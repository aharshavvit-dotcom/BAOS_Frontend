import { apiFetch } from './api';

export function getKpis<T = unknown>(portCode = 'INMAA'): Promise<T> {
  return apiFetch<T>(`/api/dashboard/kpis?port_code=${encodeURIComponent(portCode)}`);
}

export function getCharts<T = unknown>(portCode = 'INMAA'): Promise<T> {
  return apiFetch<T>(`/api/dashboard/charts?port_code=${encodeURIComponent(portCode)}`);
}
