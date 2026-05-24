/**
 * Dashboard store — KPIs and chart data.
 * Uses local fallback data when backend API is unavailable.
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

/* ── Fallback data (used when backend is unavailable) ────────── */
const FALLBACK_KPIS: KPIData = {
  vessels_count: 142,
  revenue: 480000,
  cost: 175000,
  utilization_pct: 78,
  sla_compliance_pct: 94,
  avg_turnaround_hours: 18.5,
  kpi_cards: [],
};

export const useDashboardStore = create<DashboardState>((set) => ({
  kpis: null,
  charts: null,
  recommendations: [],
  loading: false,
  lastUpdated: null,

  fetchKPIs: async (_portCode = 'INMAA') => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const res = await fetch(`${apiUrl}/api/dashboard/kpis?port_code=${_portCode}`, {
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const data = await res.json();
        set({ kpis: data, lastUpdated: new Date().toISOString() });
        return;
      }
    } catch {
      // Backend unavailable — use fallback silently
    }
    set({ kpis: FALLBACK_KPIS, lastUpdated: new Date().toISOString() });
  },

  fetchCharts: async (_portCode = 'INMAA', _timeRange = '30d') => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const res = await fetch(`${apiUrl}/api/dashboard/charts?port_code=${_portCode}&time_range=${_timeRange}`, {
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const data = await res.json();
        set({ charts: data });
        return;
      }
    } catch {
      // Backend unavailable — use fallback silently
    }
  },

  fetchRecommendations: async (_portCode = 'INMAA', _status = 'all') => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const res = await fetch(`${apiUrl}/api/dashboard/recommendations?port_code=${_portCode}&status=${_status}`, {
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        const data = await res.json();
        set({ recommendations: data.recommendations || [] });
        return;
      }
    } catch {
      // Backend unavailable — use fallback silently
    }
  },

  updateKPIs: (kpis) => set({ kpis, lastUpdated: new Date().toISOString() }),

  addRecommendation: (rec) =>
    set((state) => ({
      recommendations: [rec, ...state.recommendations],
    })),
}));
