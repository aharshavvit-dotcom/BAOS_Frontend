/* ── Optimizer Types & Helpers ─────────────────────────── */

/**
 * NOTE: This file has been refactored. Hardcoded berth arrays (ALL_BERTHS,
 * BERTH_SPECS, BERTH_COLORS) have been REMOVED. All berth data now comes
 * from the port store (dynamic data from GET /api/v1/ports/{port}/config).
 *
 * The local getSampleResult() mock is retained ONLY for demo mode fallback.
 */

// ── Types ─────────────────────────────────────────────────────────────────

export interface VesselInput {
  vessel_id: string;
  name: string;
  vessel_type: string;
  cargo_type: string;
  loa_m: number;
  beam_m: number;
  draft_m: number;
  cargo_tons: number;
  eta_hours: number;
  service_hours: number;
}

export interface ScheduleAssignment {
  vessel_id: string;
  vessel_name: string;
  berth_code: string;
  berth_name: string;
  start_hours: number;
  end_hours: number;
  waiting_hours: number;
  service_hours: number;
  sla_exceeded: boolean;
  confidence: number;
  explanation: string;
  source: string;
}

export interface CostBreakdown {
  vessel_id: string;
  vessel_name: string;
  berth_code: string;
  waiting_cost: number;
  fuel_burn_cost: number;
  equipment_rental: number;
  sla_penalty: number;
  net_cost: number;
}

export interface FeasibilityCell {
  vessel_id: string;
  berth_code: string;
  feasible: boolean;
  score: number;
  reasons: string[];
}

export interface RankedAlternative {
  berth_code: string;
  berth_name: string;
  score: number;
  waiting_hours: number;
  cost_delta: number;
  confidence: number;
  reasons: string[];
}

export interface OptimizerResult {
  status: string;
  status_message: string;
  solve_time_sec: number;
  objective_value: number;
  assignments: ScheduleAssignment[];
  costs: CostBreakdown[];
  kpis: {
    avg_wait: number;
    utilization: number;
    sla_compliance: number;
    total_revenue: number;
    total_cost: number;
    cargo_tons: number;
  };
  feasibility_matrix: FeasibilityCell[];
  ranked_alternatives: Record<string, RankedAlternative[]>;
  unassigned_vessels: string[];
  warnings: string[];
  source: 'BACKEND' | 'DEMO';
}

export interface LeversConfig {
  w_waiting: number;
  w_sla_penalty: number;
  w_contract_bonus: number;
  w_deviation: number;
  w_demurrage: number;
  w_throughput: number;
  ukc_margin_m: number;
  fcfs_enabled: boolean;
  goi_override_enabled: boolean;
  max_solve_seconds: number;
  max_channel_movements: number;
}

export interface ShipTypeLevers {
  ship_type: string;
  selected_berths: string[];
  config: LeversConfig;
}

// ── Constants ─────────────────────────────────────────────────────────────

export const VESSEL_TYPES = [
  'Bulk Dry', 'Chemical', 'Container', 'General Cargo', 'Oil',
  'Other Dry Cargo', 'Ro-Ro Cargo', 'Bulk Carrier', 'Crude Oil Tanker',
  'Chemical Tanker', 'RoRo', 'LPG Tanker', 'LNG Tanker', 'Multipurpose', 'Passenger',
];

export const CARGO_TYPES = [
  'COAL', 'IRON ORE', 'CONTAINER', 'CRUDE OIL', 'CHEMICALS', 'GENERAL',
  'VEHICLES', 'PETROLEUM', 'DIESEL', 'FUEL OIL', 'CEMENT', 'FERTILIZER',
  'GRAIN', 'BAUXITE', 'SUGAR', 'LIMESTONE', 'STEEL', 'TIMBER', 'LPG', 'LNG',
  'BREAK BULK', 'PROJECT CARGO',
];

/**
 * @deprecated — Use usePortStore().getBerths() instead.
 * These are kept ONLY for demo mode fallback.
 */
export const ALL_BERTHS_DEMO = [
  'JD1', 'JD2', 'JD3', 'JD4', 'JD5', 'JD6',
  'SCB1', 'SCB2', 'SCB3',
  'CTB1', 'CTB2', 'CTB3', 'CTB4',
  'BD1', 'BD2', 'BD3',
  '1 South', '2 South', '1 West', '2 West', '3 West', '4 West', 'C',
];

// ── Defaults & Factories ──────────────────────────────────────────────────

export function defaultLevers(): LeversConfig {
  return {
    w_waiting: 1.0, w_sla_penalty: 2.0, w_contract_bonus: 0.5,
    w_deviation: 0.5, w_demurrage: 0.0, w_throughput: 0.5,
    ukc_margin_m: 0.5, fcfs_enabled: false, goi_override_enabled: false,
    max_solve_seconds: 30, max_channel_movements: 2,
  };
}

export function makeVessel(i: number): VesselInput {
  return {
    vessel_id: `V${i + 1}`, name: `Vessel_${i + 1}`, vessel_type: 'Bulk Dry', cargo_type: 'COAL',
    loa_m: 180, beam_m: 28, draft_m: 9, cargo_tons: 20000, eta_hours: i * 4, service_hours: 24,
  };
}

export function createInitialVessels(n: number): VesselInput[] {
  return Array.from({ length: n }, (_, i) => makeVessel(i));
}

// ── Demo-Only Mock Result ─────────────────────────────────────────────────

/**
 * @deprecated — Only used when NEXT_PUBLIC_DEMO_MODE=true and backend is unavailable.
 * In production, all schedules come from POST /api/v1/optimize.
 */
export function getSampleResult(vessels: VesselInput[]): OptimizerResult {
  const berths = ALL_BERTHS_DEMO.slice(0, 7);

  const assignments: ScheduleAssignment[] = vessels.map((v, i) => {
    const bc = berths[i % berths.length];
    const waitH = i * 0.5;
    const confidence = 0.75 + Math.random() * 0.2;
    return {
      vessel_id: v.vessel_id, vessel_name: v.name, berth_code: bc,
      berth_name: bc,
      start_hours: v.eta_hours + waitH, end_hours: v.eta_hours + v.service_hours + waitH,
      waiting_hours: waitH, service_hours: v.service_hours, sla_exceeded: false,
      confidence, explanation: `[DEMO] ${v.name} assigned to ${bc}.`,
      source: 'DEMO',
    };
  });

  const costs: CostBreakdown[] = vessels.map((v, i) => {
    const bc = berths[i % berths.length];
    const waitCost = (i * 0.5) * 500;
    const fuelCost = 1200 + i * 300;
    return {
      vessel_id: v.vessel_id, vessel_name: v.name, berth_code: bc,
      waiting_cost: waitCost, fuel_burn_cost: fuelCost,
      equipment_rental: 800, sla_penalty: 0, net_cost: waitCost + fuelCost + 800,
    };
  });

  return {
    status: 'OPTIMAL',
    status_message: '[DEMO] Simulated optimal schedule. Connect backend for real results.',
    solve_time_sec: 0,
    objective_value: 0,
    assignments, costs,
    kpis: {
      avg_wait: 1.5, utilization: 72, sla_compliance: 100,
      total_revenue: 85000,
      total_cost: costs.reduce((s, c) => s + c.net_cost, 0),
      cargo_tons: vessels.reduce((s, v) => s + v.cargo_tons, 0),
    },
    feasibility_matrix: [],
    ranked_alternatives: {},
    unassigned_vessels: [],
    warnings: ['⚠️ This is demo data. Results are not from the CP-SAT solver.'],
    source: 'DEMO',
  };
}
