/**
 * Dashboard store: KPIs and chart data from the backend API.
 */
import { create } from 'zustand';
import { apiFetch } from '@/services/api';
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
      const data = await apiFetch<KPIData>(`/api/dashboard/kpis?port_code=${normalizePortCode(portCode)}`);
      set({ kpis: data, lastUpdated: new Date().toISOString(), loading: false });
    } catch {
      set({ kpis: null, loading: false });
    }
  },

  fetchCharts: async (portCode = 'INMAA', timeRange = '30d') => {
    try {
      const data = await apiFetch<ChartsData>(
        `/api/dashboard/charts?port_code=${normalizePortCode(portCode)}&time_range=${encodeURIComponent(timeRange)}`,
      );
      set({ charts: data });
    } catch {
      set({ charts: null });
    }
  },

  fetchRecommendations: async (portCode = 'INMAA', status = 'all') => {
    try {
      const data = await apiFetch<{ recommendations: DashboardRecommendation[] }>(
        `/api/dashboard/recommendations?port_code=${normalizePortCode(portCode)}&status=${encodeURIComponent(status)}`,
      );
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
