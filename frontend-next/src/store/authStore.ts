/**
 * Auth store - user session management backed by the FastAPI auth API.
 */
import { create } from 'zustand';
import api, { extractApiError } from '@/lib/api/client';
import type { User, LoginCredentials, SignupData } from '@/types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (credentials: LoginCredentials) => Promise<void>;
  signup: (data: SignupData) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

function clearStoredAuth() {
  localStorage.removeItem('baos_access_token');
  localStorage.removeItem('baos_refresh_token');
}

function normalizeEmail(email: string) {
  return email.trim().toLowerCase();
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.post('/api/auth/login', {
        email: normalizeEmail(credentials.email),
        password: credentials.password,
      });
      const { access_token, refresh_token, user } = res.data;
      localStorage.setItem('baos_access_token', access_token);
      localStorage.setItem('baos_refresh_token', refresh_token);
      set({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (err) {
      clearStoredAuth();
      const apiError = extractApiError(err);
      const message = apiError.status === 401
        ? 'Invalid email or password'
        : apiError.detail || apiError.message || 'Unable to sign in';
      set({ error: message, isAuthenticated: false, user: null, isLoading: false });
      throw new Error(message);
    }
  },

  signup: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.post('/api/auth/signup', {
        ...data,
        email: normalizeEmail(data.email),
        port_code: (data.port_code || 'INMAA').trim().toUpperCase(),
      });
      const { access_token, refresh_token, user } = res.data;
      localStorage.setItem('baos_access_token', access_token);
      localStorage.setItem('baos_refresh_token', refresh_token);
      set({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (err) {
      clearStoredAuth();
      const apiError = extractApiError(err);
      const message = apiError.detail || apiError.message || 'Unable to create account';
      set({ error: message, isAuthenticated: false, user: null, isLoading: false });
      throw new Error(message);
    }
  },

  logout: () => {
    clearStoredAuth();
    set({ user: null, isAuthenticated: false, error: null });
  },

  setUser: (user) => set({ user, isAuthenticated: true }),

  checkAuth: async () => {
    const token = localStorage.getItem('baos_access_token');
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }

    try {
      const res = await api.get('/api/auth/me');
      set({ user: res.data, isAuthenticated: true, error: null });
    } catch {
      clearStoredAuth();
      set({ isAuthenticated: false, user: null });
    }
  },

  clearError: () => set({ error: null }),
}));
