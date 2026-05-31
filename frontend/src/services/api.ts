import { API_BASE_URL } from '@/lib/constants';

async function attemptTokenRefresh(): Promise<boolean> {
  if (typeof window === 'undefined') return false;

  const refreshToken = localStorage.getItem('baos_refresh_token');
  const accessToken = localStorage.getItem('baos_access_token');
  if (!refreshToken && !accessToken) return false;

  try {
    const headers: Record<string, string> = {};
    const init: RequestInit = { method: 'POST', headers };

    if (refreshToken) {
      headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify({ refresh_token: refreshToken });
    } else if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    const res = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, init);
    if (!res.ok) return false;

    const data = await res.json();
    localStorage.setItem('baos_access_token', data.access_token);
    return true;
  } catch {
    return false;
  }
}

function clearAuthAndRedirect() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('baos_access_token');
  localStorage.removeItem('baos_refresh_token');
  localStorage.removeItem('baos_token');
  window.location.href = '/login';
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
  retryOnUnauthorized = true,
): Promise<T> {
  const headers = new Headers(options?.headers);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('baos_access_token');
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401 && retryOnUnauthorized) {
    const refreshed = await attemptTokenRefresh();
    if (refreshed) {
      return apiFetch<T>(path, options, false);
    }
    clearAuthAndRedirect();
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}
