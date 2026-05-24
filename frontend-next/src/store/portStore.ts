/**
 * Port Store — Dynamic port configuration and berth inventory.
 *
 * Replaces ALL hardcoded berth arrays (INMAA-B01..B07, BERTH_SPECS, etc.)
 * with real data from GET /api/v1/ports/{port_code}/config.
 */
import { create } from 'zustand';
import {
  getPorts, getPortConfig, getPortStatus,
  type PortInfo, type PortConfig, type PortStatus, type BerthConfig,
} from '@/lib/api/ports';

// ── Dynamic color palette for berths ──────────────────────────────────────

const BERTH_PALETTE = [
  '#10b981', '#0ea5e9', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899',
  '#6366f1', '#14b8a6', '#f97316', '#06b6d4', '#a855f7', '#e11d48',
  '#22c55e', '#3b82f6', '#d946ef', '#eab308', '#f43f5e', '#84cc16',
  '#0891b2', '#7c3aed', '#db2777', '#65a30d', '#0d9488', '#c026d3',
];

function buildBerthColorMap(berths: BerthConfig[]): Record<string, string> {
  const map: Record<string, string> = {};
  berths.forEach((b, i) => {
    map[b.berth_code] = BERTH_PALETTE[i % BERTH_PALETTE.length];
  });
  return map;
}

// ── Store Type ────────────────────────────────────────────────────────────

interface PortState {
  // Data
  ports: PortInfo[];
  selectedPortCode: string;
  portConfig: PortConfig | null;
  portStatus: PortStatus | null;
  berthColorMap: Record<string, string>;

  // UI state
  loading: boolean;
  error: string | null;

  // Actions
  fetchPorts: () => Promise<void>;
  selectPort: (portCode: string) => Promise<void>;
  refreshPortStatus: () => Promise<void>;

  // Computed helpers
  getBerths: () => BerthConfig[];
  getBerthByCode: (code: string) => BerthConfig | undefined;
  getBerthColor: (code: string) => string;
  getBerthDisplayName: (code: string) => string;
  getVesselTypes: () => string[];
}

export const usePortStore = create<PortState>((set, get) => ({
  ports: [],
  selectedPortCode: 'chennai',
  portConfig: null,
  portStatus: null,
  berthColorMap: {},
  loading: false,
  error: null,

  fetchPorts: async () => {
    set({ loading: true, error: null });
    try {
      const ports = await getPorts();
      set({ ports, loading: false });

      // Auto-select first port if none selected
      if (ports.length > 0 && !get().portConfig) {
        await get().selectPort(ports[0].port_name);
      }
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to load ports',
      });
    }
  },

  selectPort: async (portCode: string) => {
    set({ loading: true, error: null, selectedPortCode: portCode });
    try {
      const [config, status] = await Promise.all([
        getPortConfig(portCode),
        getPortStatus(portCode),
      ]);
      set({
        portConfig: config,
        portStatus: status,
        berthColorMap: buildBerthColorMap(config.berths),
        loading: false,
      });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : `Failed to load port ${portCode}`,
      });
    }
  },

  refreshPortStatus: async () => {
    const { selectedPortCode } = get();
    try {
      const status = await getPortStatus(selectedPortCode);
      set({ portStatus: status });
    } catch {
      // Silently fail — status is non-critical
    }
  },

  getBerths: () => get().portConfig?.berths ?? [],

  getBerthByCode: (code: string) =>
    get().portConfig?.berths.find((b) => b.berth_code === code),

  getBerthColor: (code: string) => get().berthColorMap[code] || '#94a3b8',

  getBerthDisplayName: (code: string) => {
    const berth = get().getBerthByCode(code);
    return berth ? berth.berth_name : code;
  },

  getVesselTypes: () => get().portConfig?.vessel_types ?? [],
}));
