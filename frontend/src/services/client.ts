/**
 * BAOS — Centralized API Client
 *
 * Single Axios instance with:
 * - JWT auth interceptor
 * - Consistent error handling
 * - Token refresh
 */
import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { API_BASE_URL } from '@/lib/constants';

// Config---

const API_BASE = API_BASE_URL;

/** Standardized API error shape */
export interface ApiError {
  message: string;
  status: number;
  detail?: string;
}

/** Standardized wrapper response from backend */
export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  warnings?: string[];
  assumptions_used?: string[];
  source_quality?: Record<string, string>;
  timestamp?: string;
}

// Client Instance---

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

// Request interceptor - attach JWT---

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('baos_access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response interceptor - 401 refresh---

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const requestUrl = originalRequest?.url || '';
    const isAuthRequest =
      requestUrl.includes('/api/auth/login') ||
      requestUrl.includes('/api/auth/signup') ||
      requestUrl.includes('/api/auth/refresh');

    if (originalRequest && error.response?.status === 401 && !originalRequest._retry && !isAuthRequest) {
      originalRequest._retry = true;

      try {
        if (typeof window === 'undefined') {
          return Promise.reject(error);
        }
        const refreshToken = localStorage.getItem('baos_refresh_token');
        if (refreshToken) {
          const res = await axios.post(`${API_BASE}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const newToken = res.data.access_token;
          localStorage.setItem('baos_access_token', newToken);
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
          }
          return apiClient(originalRequest);
        }
      } catch {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('baos_access_token');
          localStorage.removeItem('baos_refresh_token');
          localStorage.removeItem('baos_token');
          window.location.href = '/login';
        }
      }
    }

    return Promise.reject(error);
  },
);

// Helpers---

/** Extract a user-friendly error message from an Axios error */
export function extractApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status ?? 0;
    const detail =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message;
    return {
      message: `API Error (${status}): ${detail}`,
      status,
      detail: typeof detail === 'string' ? detail : JSON.stringify(detail),
    };
  }
  return {
    message: error instanceof Error ? error.message : 'Unknown error',
    status: 0,
  };
}

/** Get base URL for display/debugging */
export function getApiBaseUrl(): string {
  return API_BASE;
}

export default apiClient;

