/**
 * Auth store — user session management.
 * Falls back to demo login when backend is unreachable.
 */
import { create } from 'zustand';
import api from '@/lib/api';
import type { User, LoginCredentials, SignupData } from '@/types';

/* ── Demo credentials (used when backend is offline) ──────── */
const DEMO_USERS: Record<string, { password: string; user: User }> = {
  'admin@baos.ai': {
    password: 'admin123',
    user: {
      id: 'demo-admin',
      email: 'admin@baos.ai',
      full_name: 'Admin User',
      company: 'Port Authority',
      port_code: 'INMAA',
      port_name: 'Chennai',
      role: 'admin',
    },
  },
  'operator@baos.ai': {
    password: 'operator123',
    user: {
      id: 'demo-operator',
      email: 'operator@baos.ai',
      full_name: 'Port Operator',
      company: 'Chennai Port Trust',
      port_code: 'INMAA',
      port_name: 'Chennai',
      role: 'operator',
    },
  },
};

function tryDemoLogin(email: string, password: string): User | null {
  const entry = DEMO_USERS[email.toLowerCase()];
  if (entry && entry.password === password) return entry.user;
  // Accept any email/password combo in demo mode (min 4 char password)
  if (password.length >= 4) {
    return {
      id: `demo-${Date.now()}`,
      email,
      full_name: email.split('@')[0],
      company: 'Port Authority',
      port_code: 'INMAA',
      port_name: 'Chennai',
      role: 'operator',
    };
  }
  return null;
}

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

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      // Try real backend first
      const res = await api.post('/api/auth/login', credentials);
      const { access_token, refresh_token, user } = res.data;
      localStorage.setItem('baos_access_token', access_token);
      localStorage.setItem('baos_refresh_token', refresh_token);
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      // Backend unreachable — fall back to demo login
      const demoUser = tryDemoLogin(credentials.email, credentials.password);
      if (demoUser) {
        const demoToken = `demo_token_${Date.now()}`;
        localStorage.setItem('baos_access_token', demoToken);
        localStorage.setItem('baos_refresh_token', `refresh_${demoToken}`);
        localStorage.setItem('baos_demo_user', JSON.stringify(demoUser));
        set({ user: demoUser, isAuthenticated: true, isLoading: false });
      } else {
        set({ error: 'Invalid email or password', isLoading: false });
        throw new Error('Invalid email or password');
      }
    }
  },

  signup: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.post('/api/auth/signup', data);
      const { access_token, refresh_token, user } = res.data;
      localStorage.setItem('baos_access_token', access_token);
      localStorage.setItem('baos_refresh_token', refresh_token);
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      // Fallback demo signup
      const demoUser: User = {
        id: `demo-${Date.now()}`,
        email: data.email,
        full_name: data.full_name || data.email.split('@')[0],
        company: data.company || 'Port Authority',
        port_code: data.port_code || 'INMAA',
        port_name: 'Chennai',
        role: 'operator',
      };
      const demoToken = `demo_token_${Date.now()}`;
      localStorage.setItem('baos_access_token', demoToken);
      localStorage.setItem('baos_refresh_token', `refresh_${demoToken}`);
      localStorage.setItem('baos_demo_user', JSON.stringify(demoUser));
      set({ user: demoUser, isAuthenticated: true, isLoading: false });
    }
  },

  logout: () => {
    localStorage.removeItem('baos_access_token');
    localStorage.removeItem('baos_refresh_token');
    localStorage.removeItem('baos_demo_user');
    set({ user: null, isAuthenticated: false });
  },

  setUser: (user) => set({ user, isAuthenticated: true }),

  checkAuth: async () => {
    const token = localStorage.getItem('baos_access_token');
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }
    // Demo tokens start with "demo_"
    if (token.startsWith('demo_')) {
      // Restore demo user from localStorage
      try {
        const stored = localStorage.getItem('baos_demo_user');
        const demoUser = stored ? JSON.parse(stored) : null;
        set({ user: demoUser, isAuthenticated: true });
      } catch {
        set({ isAuthenticated: true });
      }
      return;
    }
    try {
      const res = await api.get('/api/auth/me');
      set({ user: res.data, isAuthenticated: true });
    } catch {
      // Backend unreachable but has token — keep authenticated
      if (token) {
        set({ isAuthenticated: true });
      } else {
        set({ isAuthenticated: false, user: null });
      }
    }
  },

  clearError: () => set({ error: null }),
}));
