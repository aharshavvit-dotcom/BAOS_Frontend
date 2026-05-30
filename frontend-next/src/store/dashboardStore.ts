/**
 * Dashboard store: KPIs and chart data from the backend API.
 */
import { create } from 'zustand';
import type { KPIData, ChartsData, DashboardRecommendation } from '@/types';

interface DashboardState {
  kpis: KPIData | null;
  charts: ChartsData | null;
  recommendations: DashboardRecommendation[];
  loading: boolean;
  lastUpdated: string | null;

  fetchKPIs: (portCode?: string) => Promise<void>;
  fetchCharts: (portCode?: string, timeRange?: string) => Promise<void>;
  fetchRecommendations: (portCode?: string, status?: string) => Promise<void>;
  updateKPIs: (kpis: KPIData) => void;
  addRecommendation: (rec: DashboardRecommendation) => void;
}

function normalizePortCode(portCode = 'INMAA') {
  return encodeURIComponent(portCode.trim().toUpperCase());
}

export const useDashboardStore = create<DashboardState>((set) => ({
  kpis: null,
  charts: null,
  recommendations: [],
  loading: false,
  lastUpdated: null,

  fetchKPIs: async (portCode = 'INMAA') => {
    set({ loading: true });
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const res = await fetch(`${apiUrl}/api/dashboard/kpis?port_code=${normalizePortCode(portCode)}`);
      if (!res.ok) throw new Error('Failed to load KPIs');
      const data = await res.json();
      set({ kpis: data, lastUpdated: new Date().toISOString(), loading: false });
    } catch {
      set({ kpis: null, loading: false });
    }
  },

  fetchCharts: async (portCode = 'INMAA', timeRange = '30d') => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const res = await fetch(
        `${apiUrl}/api/dashboard/charts?port_code=${normalizePortCode(portCode)}&time_range=${encodeURIComponent(timeRange)}`,
      );
      if (!res.ok) throw new Error('Failed to load charts');
      const data = await res.json();
      set({ charts: data });
    } catch {
      set({ charts: null });
    }
  },

  fetchRecommendations: async (portCode = 'INMAA', status = 'all') => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const res = await fetch(
        `${apiUrl}/api/dashboard/recommendations?port_code=${normalizePortCode(portCode)}&status=${encodeURIComponent(status)}`,
      );
      if (!res.ok) throw new Error('Failed to load recommendations');
      const data = await res.json();
      set({ recommendations: data.recommendations || [] });
    } catch {
      set({ recommendations: [] });
    }
  },

  updateKPIs: (kpis) => set({ kpis, lastUpdated: new Date().toISOString() }),

  addRecommendation: (rec) =>
    set((state) => ({
      recommendations: [rec, ...state.recommendations],
    })),
}));
