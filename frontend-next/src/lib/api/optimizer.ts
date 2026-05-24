/**
 * BAOS — Optimizer API Service
 *
 * Calls the real CP-SAT backend at POST /api/v1/optimize.
 * Handles unit conversion (hours→minutes) and schema mapping.
 */
import apiClient from './client';
import type { AssumptionSource } from '../constants/assumptionDefaults';

// --- Frontend Types (display-friendly, hours-based) ---

export interface OptimizerVesselInput {
  vessel_id: string;
  name: string;
  vessel_type: string;
  cargo_type: string;
  loa_m: number;
  beam_m: number;
  draft_m: number;
  cargo_tons: number;
  dwt: number;
  eta_hours: number;
  service_hours: number;
  priority: number;
  preferred_berths: string[];
  sla_max_wait_hours: number;
  demurrage_cost_per_hr: number;
  needs_tug: boolean;
  needs_pilot: boolean;
  customs_cleared: boolean;
  government_priority: boolean;
}

export interface OptimizerLeversConfig {
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

export interface ResourceConfig {
  pilot_capacity: number;
  tug_capacity: number;
  channel_capacity: number;
}

export interface OptimizerRequest {
  port_code: string;
  vessels: OptimizerVesselInput[];
  levers: OptimizerLeversConfig;
  resources: ResourceConfig;
}

// --- Backend Types (what the API actually expects/returns) ---

interface BackendVessel {
  vessel_id: string;
  name: string;
  vessel_type: string;
  cargo_type: string;
  loa_m: number;
  beam_m: number;
  draft_m: number;
  cargo_tons: number;
  eta_minutes: number;
  service_time_minutes: number;
  priority: number;
  preferred_berths: string[];
  sla_max_wait_minutes: number;
  demurrage_cost_per_hr: number;
  needs_tug: boolean;
  needs_pilot: boolean;
  customs_cleared: boolean;
  government_priority: boolean;
}

interface BackendOptimizeRequest {
  port_code: string;
  vessels: BackendVessel[];
  config: Record<string, unknown>;
  pilot_capacity: number;
  tug_capacity: number;
}

// --- Response Types ---

export interface AssignmentResult {
  vessel_id: string;
  vessel_name: string;
  berth_code: string;
  berth_name: string;
  start_minutes: number;
  end_minutes: number;
  waiting_minutes: number;
  service_minutes: number;
  sla_exceeded: boolean;
  is_preferred_berth: boolean;
}

export interface CostSummary {
  total_waiting_cost: number;
  total_fuel_cost: number;
  total_equipment_cost: number;
  total_sla_penalties: number;
  total_revenue: number;
  total_cost: number;
  net_cost: number;
}

export interface ExplanationResult {
  vessel_id: string;
  berth_code: string;
  headline: string;
  reasons: string[];
  trade_offs: string[];
  cost_note: string;
}

export interface MlPrediction {
  service_time_p25_hours?: number;
  service_time_p50_hours: number;
  service_time_p75_hours?: number;
  source: 'ML_P50' | 'HISTORICAL_MEDIAN' | 'USER_INPUT' | 'ASSUMPTION';
  used_in_optimizer: boolean;
  confidence: number;
  fallback_used: boolean;
}

export type SolverStatus = 'OPTIMAL' | 'FEASIBLE' | 'INFEASIBLE' | 'TIMEOUT' | 'ERROR';

export interface OptimizeResponse {
  status: SolverStatus;
  solve_time_sec: number;
  objective_value: number;
  assignments: AssignmentResult[];
  unassigned_vessels: string[];
  kpis: Record<string, number>;
  cost_summary: CostSummary | null;
  explanations: ExplanationResult[] | null;
  ml_predictions?: Record<string, MlPrediction>;
  assumptions_used?: string[];
  warnings?: string[];
}

// --- Display-friendly mapped result ---

export interface DisplayAssignment {
  vessel_id: string;
  vessel_name: string;
  berth_code: string;
  berth_name: string;
  start_hours: number;
  end_hours: number;
  waiting_hours: number;
  service_hours: number;
  sla_exceeded: boolean;
  is_preferred_berth: boolean;
  confidence: number;
  explanation: string;
  source: AssumptionSource;
}

export interface DisplayCostBreakdown {
  vessel_id: string;
  vessel_name: string;
  berth_code: string;
  waiting_cost: number;
  fuel_burn_cost: number;
  equipment_rental: number;
  sla_penalty: number;
  net_cost: number;
}

export interface DisplayOptimizerResult {
  status: SolverStatus;
  status_message: string;
  solve_time_sec: number;
  objective_value: number;
  assignments: DisplayAssignment[];
  costs: DisplayCostBreakdown[];
  kpis: {
    avg_wait: number;
    utilization: number;
    sla_compliance: number;
    total_revenue: number;
    total_cost: number;
    cargo_tons: number;
  };
  unassigned_vessels: string[];
  ml_predictions: Record<string, MlPrediction>;
  explanations: ExplanationResult[];
  assumptions_used: string[];
  warnings: string[];
  source: 'BACKEND' | 'DEMO';
}

// --- Mapper: Frontend → Backend ---

function mapVesselToBackend(v: OptimizerVesselInput): BackendVessel {
  return {
    vessel_id: v.vessel_id,
    name: v.name,
    vessel_type: v.vessel_type,
    cargo_type: v.cargo_type,
    loa_m: v.loa_m,
    beam_m: v.beam_m,
    draft_m: v.draft_m,
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
  };
}

function mapRequestToBackend(req: OptimizerRequest): BackendOptimizeRequest {
  return {
    port_code: req.port_code,
    vessels: req.vessels.map(mapVesselToBackend),
    config: {
      w_waiting: req.levers.w_waiting,
      w_sla_penalty: req.levers.w_sla_penalty,
      w_contract_bonus: req.levers.w_contract_bonus,
      w_deviation: req.levers.w_deviation,
      w_demurrage: req.levers.w_demurrage,
      w_throughput: req.levers.w_throughput,
      ukc_margin_m: req.levers.ukc_margin_m,
      fcfs_enabled: req.levers.fcfs_enabled,
      goi_override_enabled: req.levers.goi_override_enabled,
      max_solve_seconds: req.levers.max_solve_seconds,
      max_channel_movements: req.levers.max_channel_movements,
    },
    pilot_capacity: req.resources.pilot_capacity,
    tug_capacity: req.resources.tug_capacity,
  };
}

// --- Mapper: Backend → Display ---

function getSolverStatusMessage(status: SolverStatus, assignedCount: number, totalCount: number): string {
  switch (status) {
    case 'OPTIMAL':
      return `Optimal schedule found. ${assignedCount}/${totalCount} vessels assigned.`;
    case 'FEASIBLE':
      return `Feasible solution found (optimality not proven). ${assignedCount}/${totalCount} vessels assigned.`;
    case 'INFEASIBLE':
      return `No feasible schedule found. Review vessel constraints and berth availability.`;
    case 'TIMEOUT':
      return assignedCount > 0
        ? `Solver timed out. Best feasible solution: ${assignedCount}/${totalCount} vessels assigned.`
        : `Solver timed out without finding a feasible solution.`;
    case 'ERROR':
      return `Solver encountered an error. Please retry or contact support.`;
    default:
      return `Status: ${status}`;
  }
}

export function mapResponseToDisplay(
  response: OptimizeResponse,
  vessels: OptimizerVesselInput[],
): DisplayOptimizerResult {
  const explanationMap = new Map<string, ExplanationResult>();
  if (response.explanations) {
    for (const exp of response.explanations) {
      explanationMap.set(exp.vessel_id, exp);
    }
  }

  const assignments: DisplayAssignment[] = response.assignments.map((a) => {
    const exp = explanationMap.get(a.vessel_id);
    return {
      vessel_id: a.vessel_id,
      vessel_name: a.vessel_name,
      berth_code: a.berth_code,
      berth_name: a.berth_name,
      start_hours: a.start_minutes / 60,
      end_hours: a.end_minutes / 60,
      waiting_hours: a.waiting_minutes / 60,
      service_hours: a.service_minutes / 60,
      sla_exceeded: a.sla_exceeded,
      is_preferred_berth: a.is_preferred_berth,
      confidence: 0.85, // Will be enriched from confidence engine
      explanation: exp ? exp.headline + ' ' + exp.reasons.join(' ') : '',
      source: 'BACKEND' as AssumptionSource,
    };
  });

  // Build cost breakdown per vessel from cost_summary
  const costs: DisplayCostBreakdown[] = assignments.map((a) => {
    const waitCost = a.waiting_hours * 500; // Default demurrage assumption
    const fuelCost = a.waiting_hours * 150;  // Fuel wait assumption
    return {
      vessel_id: a.vessel_id,
      vessel_name: a.vessel_name,
      berth_code: a.berth_code,
      waiting_cost: Math.round(waitCost),
      fuel_burn_cost: Math.round(fuelCost),
      equipment_rental: 800,
      sla_penalty: a.sla_exceeded ? 1000 : 0,
      net_cost: Math.round(waitCost + fuelCost + 800 + (a.sla_exceeded ? 1000 : 0)),
    };
  });

  const totalCargo = vessels.reduce((s, v) => s + v.cargo_tons, 0);
  const kpis = response.kpis || {};

  return {
    status: response.status as SolverStatus,
    status_message: getSolverStatusMessage(
      response.status as SolverStatus,
      response.assignments.length,
      vessels.length,
    ),
    solve_time_sec: response.solve_time_sec,
    objective_value: response.objective_value,
    assignments,
    costs,
    kpis: {
      avg_wait: kpis.avg_wait_hours ?? (assignments.reduce((s, a) => s + a.waiting_hours, 0) / Math.max(assignments.length, 1)),
      utilization: kpis.utilization_pct ?? 0,
      sla_compliance: kpis.sla_compliance_pct ?? (assignments.filter((a) => !a.sla_exceeded).length / Math.max(assignments.length, 1)) * 100,
      total_revenue: response.cost_summary?.total_revenue ?? 0,
      total_cost: response.cost_summary?.total_cost ?? costs.reduce((s, c) => s + c.net_cost, 0),
      cargo_tons: totalCargo,
    },
    unassigned_vessels: response.unassigned_vessels,
    ml_predictions: response.ml_predictions || {},
    explanations: response.explanations || [],
    assumptions_used: response.assumptions_used || [],
    warnings: response.warnings || [],
    source: 'BACKEND',
  };
}

// --- API Functions ---

/** Run multi-vessel CP-SAT optimization via real backend */
export async function runOptimize(
  request: OptimizerRequest,
): Promise<DisplayOptimizerResult> {
  const backendReq = mapRequestToBackend(request);
  const res = await apiClient.post<OptimizeResponse>('/api/v1/optimize', backendReq);
  return mapResponseToDisplay(res.data, request.vessels);
}

/** Get the last computed schedule for a port */
export async function getSchedule(portCode: string): Promise<OptimizeResponse> {
  const res = await apiClient.get<OptimizeResponse>(`/api/v1/schedule/${portCode}`);
  return res.data;
}

// --- Default Vessel Factory ---

export function makeDefaultVessel(index: number): OptimizerVesselInput {
  return {
    vessel_id: `V${index + 1}`,
    name: `Vessel_${index + 1}`,
    vessel_type: 'Bulk Dry',
    cargo_type: 'COAL',
    loa_m: 180,
    beam_m: 28,
    draft_m: 9,
    cargo_tons: 20000,
    dwt: 30000,
    eta_hours: index * 4,
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
}

export function createInitialVessels(count: number): OptimizerVesselInput[] {
  return Array.from({ length: count }, (_, i) => makeDefaultVessel(i));
}

/** Default levers config */
export function defaultLevers(): OptimizerLeversConfig {
  return {
    w_waiting: 1.0,
    w_sla_penalty: 2.0,
    w_contract_bonus: 0.5,
    w_deviation: 0.5,
    w_demurrage: 0.0,
    w_throughput: 0.5,
    ukc_margin_m: 0.5,
    fcfs_enabled: false,
    goi_override_enabled: false,
    max_solve_seconds: 30,
    max_channel_movements: 2,
  };
}

/** Default resource config */
export function defaultResources(): ResourceConfig {
  return {
    pilot_capacity: 2,
    tug_capacity: 3,
    channel_capacity: 1,
  };
}

