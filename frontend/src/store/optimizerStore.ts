/**
 * Optimizer Store — State management for multi-vessel scheduling.
 *
 * Connects to real backend POST /api/v1/optimize.
 * Manages vessels, levers, results, baseline, and overrides.
 */
import { create } from 'zustand';
import {
  runOptimize,
  mapResponseToDisplay,
  createInitialVessels,
  defaultLevers,
  defaultResources,
  type OptimizerVesselInput,
  type OptimizerLeversConfig,
  type ResourceConfig,
  type DisplayOptimizerResult,
  type SolverStatus,
  type OptimizeResponse,
} from '@/services/optimizer';
import { applyOverride, type ScenarioImpact } from '@/services/scenarios';
import { extractApiError } from '@/services/client';

interface OptimizerState {
  // Inputs
  vessels: OptimizerVesselInput[];
  levers: OptimizerLeversConfig;
  resources: ResourceConfig;
  portCode: string;

  // Results
  result: DisplayOptimizerResult | null;
  baseline: DisplayOptimizerResult | null;
  scenarioImpact: ScenarioImpact | null;

  // UI State
  loading: boolean;
  error: string | null;
  solverStatus: SolverStatus | null;

  // Actions — Inputs
  setPortCode: (code: string) => void;
  setVessels: (vessels: OptimizerVesselInput[]) => void;
  addVessel: () => void;
  removeVessel: (index: number) => void;
  updateVessel: (index: number, vessel: OptimizerVesselInput) => void;
  setLevers: (levers: OptimizerLeversConfig) => void;
  setResources: (resources: ResourceConfig) => void;

  // Actions — Execution
  runOptimization: () => Promise<void>;
  applyManualOverride: (vesselId: string, berthCode: string) => Promise<void>;
  clearResult: () => void;
  clearError: () => void;
}

export const useOptimizerStore = create<OptimizerState>((set, get) => ({
  // Default inputs
  vessels: createInitialVessels(3),
  levers: defaultLevers(),
  resources: defaultResources(),
  portCode: 'chennai',

  // No results yet
  result: null,
  baseline: null,
  scenarioImpact: null,
  loading: false,
  error: null,
  solverStatus: null,

  // --- Input Actions ---

  setPortCode: (code) => set({ portCode: code }),

  setVessels: (vessels) => set({ vessels }),

  addVessel: () => {
    const { vessels } = get();
    const newVessel: OptimizerVesselInput = {
      vessel_id: `V${vessels.length + 1}`,
      name: `Vessel_${vessels.length + 1}`,
      vessel_type: 'Bulk Dry',
      cargo_type: 'COAL',
      loa_m: 180,
      beam_m: 28,
      draft_m: 9,
      cargo_tons: 20000,
      dwt: 30000,
      eta_hours: vessels.length * 4,
      service_hours: 24,
      priority: 100,
      preferred_berths: [],
      sla_max_wait_hours: 24,
      demurrage_cost_per_hr: 0,
      needs_tug: true,
      needs_pilot: true,
      customs_cleared: true,
      government_priority: false,
    };
    set({ vessels: [...vessels, newVessel] });
  },

  removeVessel: (index) => {
    const { vessels } = get();
    set({ vessels: vessels.filter((_, i) => i !== index) });
  },

  updateVessel: (index, vessel) => {
    const { vessels } = get();
    const updated = [...vessels];
    updated[index] = vessel;
    set({ vessels: updated });
  },

  setLevers: (levers) => set({ levers }),

  setResources: (resources) => set({ resources }),

  // --- Execution Actions ---

  runOptimization: async () => {
    const { vessels, levers, resources, portCode } = get();

    if (vessels.length === 0) {
      set({ error: 'No vessels to optimize. Add at least one vessel.' });
      return;
    }

    set({ loading: true, error: null, solverStatus: null, scenarioImpact: null });

    try {
      const result = await runOptimize({
        port_code: portCode,
        vessels,
        levers,
        resources,
      });

      set({
        result,
        baseline: result,
        loading: false,
        solverStatus: result.status,
      });
    } catch (err) {
      const apiErr = extractApiError(err);
      set({
        loading: false,
        error: apiErr.message,
        solverStatus: 'ERROR',
      });
    }
  },

  applyManualOverride: async (vesselId: string, berthCode: string) => {
    const { vessels, levers, resources, portCode } = get();

    set({ loading: true, error: null });

    try {
      // Map frontend vessels to backend format
      const backendVessels = vessels.map((v) => ({
        vessel_id: v.vessel_id,
        name: v.name,
        vessel_type: v.vessel_type,
        loa_m: v.loa_m,
        beam_m: v.beam_m,
        draft_m: v.draft_m,
        cargo_type: v.cargo_type,
        cargo_tons: v.cargo_tons,
        eta_minutes: Math.round(v.eta_hours * 60),
        service_time_minutes: Math.round(v.service_hours * 60),
        priority: v.priority,
        preferred_berths: v.preferred_berths,
        sla_max_wait_minutes: Math.round(v.sla_max_wait_hours * 60),
        demurrage_cost_per_hr: v.demurrage_cost_per_hr,
        needs_tug: v.needs_tug,
        needs_pilot: v.needs_pilot,
        customs_cleared: v.customs_cleared,
        government_priority: v.government_priority,
      }));

      const response = await applyOverride({
        port_code: portCode,
        vessels: backendVessels,
        overrides: [{ vessel_id: vesselId, berth_code: berthCode }],
        config: {
          w_waiting: levers.w_waiting,
          w_sla_penalty: levers.w_sla_penalty,
          w_contract_bonus: levers.w_contract_bonus,
          w_deviation: levers.w_deviation,
          w_demurrage: levers.w_demurrage,
          w_throughput: levers.w_throughput,
          ukc_margin_m: levers.ukc_margin_m,
          fcfs_enabled: levers.fcfs_enabled,
          goi_override_enabled: levers.goi_override_enabled,
          max_solve_seconds: levers.max_solve_seconds,
          max_channel_movements: levers.max_channel_movements,
        },
        pilot_capacity: resources.pilot_capacity,
        tug_capacity: resources.tug_capacity,
      });

      // Update result from override response
      set({
        result: response.active_result ? mapResponseToDisplay(response.active_result as unknown as OptimizeResponse, vessels) : null,
        scenarioImpact: response.scenario_impact,
        loading: false,
        solverStatus: response.status,
      });
    } catch (err) {
      const apiErr = extractApiError(err);
      set({
        loading: false,
        error: `Override failed: ${apiErr.message}`,
      });
    }
  },

  clearResult: () => set({ result: null, baseline: null, scenarioImpact: null, solverStatus: null }),

  clearError: () => set({ error: null }),
}));

