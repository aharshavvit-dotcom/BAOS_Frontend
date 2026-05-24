/**
 * BAOS — Scenario API Service
 *
 * Calls backend for manual override / what-if scenarios.
 * Replaces the frontend-only local mutation pattern.
 */
import apiClient from './client';
import type { SolverStatus } from './optimizer';

// --- Types ---

export interface ScenarioOverride {
  vessel_id: string;
  berth_code: string;
  reason?: string;
}

export interface ApplyOverrideRequest {
  port_code: string;
  vessels: Array<{
    vessel_id: string;
    name: string;
    vessel_type: string;
    loa_m: number;
    beam_m: number;
    draft_m: number;
    cargo_type: string;
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
  }>;
  overrides: ScenarioOverride[];
  config?: Record<string, unknown>;
  pilot_capacity?: number;
  tug_capacity?: number;
}

export interface ScenarioImpact {
  objective_delta: number;
  waiting_hours_delta: number;
  cost_delta: number;
  confidence_delta: number;
  sla_risk_delta: number;
  conflicts_detected: string[];
}

export interface ApplyOverrideResponse {
  success: boolean;
  status: SolverStatus;
  active_result: Record<string, unknown>;
  scenario_impact: ScenarioImpact;
  ranked_alternatives: Record<string, unknown>;
  messages: string[];
}

export interface RankedAlternative {
  rank: number;
  berth_code: string;
  berth_name: string;
  objective_value: number;
  waiting_hours: number;
  cost: number;
  confidence_pct: number;
  feasibility_score: number;
  reason: string;
  is_current: boolean;
}

export interface RankedAlternativesResponse {
  vessel_id: string;
  alternatives: RankedAlternative[];
}

// --- API Functions ---

/**
 * Apply a manual override and trigger backend re-optimization.
 *
 * Flow:
 *   User changes berth
 *     → POST /api/v1/scenarios/apply-override
 *     → Backend validates constraints
 *     → Backend re-runs optimizer with locked override
 *     → Backend returns new schedule + deltas
 *     → Frontend updates active result
 */
export async function applyOverride(
  request: ApplyOverrideRequest,
): Promise<ApplyOverrideResponse> {
  const res = await apiClient.post<ApplyOverrideResponse>(
    '/api/v1/scenarios/apply-override',
    request,
  );
  return res.data;
}

/** Get solver-ranked alternatives for a vessel */
export async function getRankedAlternatives(
  portCode: string,
  vesselId: string,
  vessels: ApplyOverrideRequest['vessels'],
): Promise<RankedAlternative[]> {
  const res = await apiClient.post<RankedAlternativesResponse>(
    '/api/v1/optimizer/ranked-alternatives',
    {
      port_code: portCode,
      vessel_id: vesselId,
      vessels,
    },
  );
  return res.data.alternatives;
}

/** Run what-if scenario comparison */
export async function runWhatIf(
  portCode: string,
  vessels: ApplyOverrideRequest['vessels'],
  scenarioName: string,
  changeDescription: string,
  modifiedConfig: Record<string, unknown>,
) {
  const res = await apiClient.post('/api/v1/what-if', {
    port_code: portCode,
    vessels,
    scenario_name: scenarioName,
    change_description: changeDescription,
    modified_config: modifiedConfig,
  });
  return res.data;
}

