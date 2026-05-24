/* ── Optimizer Types & Helpers ─────────────────────────── */

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
  start_hours: number;
  end_hours: number;
  waiting_hours: number;
  service_hours: number;
  sla_exceeded: boolean;
  confidence: number;
  explanation: string;
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
  score: number;
  waiting_hours: number;
  cost_delta: number;
  confidence: number;
  reasons: string[];
}

export interface OptimizerResult {
  status: string;
  solve_time_sec: number;
  assignments: ScheduleAssignment[];
  costs: CostBreakdown[];
  kpis: { avg_wait: number; utilization: number; sla_compliance: number; total_revenue: number; total_cost: number; cargo_tons: number };
  feasibility_matrix: FeasibilityCell[];
  ranked_alternatives: Record<string, RankedAlternative[]>;
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

export const VESSEL_TYPES = ['Bulk Dry', 'Chemical', 'Container', 'General Cargo', 'Oil', 'Other Dry Cargo', 'Ro-Ro Cargo', 'Bulk Carrier', 'Crude Oil Tanker', 'Chemical Tanker', 'RoRo', 'LPG Tanker', 'LNG Tanker', 'Multipurpose', 'Passenger'];
export const CARGO_TYPES = ['COAL', 'IRON ORE', 'CONTAINER', 'CRUDE OIL', 'CHEMICALS', 'GENERAL', 'VEHICLES', 'PETROLEUM', 'DIESEL', 'FUEL OIL', 'CEMENT', 'FERTILIZER', 'GRAIN', 'BAUXITE', 'SUGAR', 'LIMESTONE', 'STEEL', 'TIMBER', 'LPG', 'LNG', 'BREAK BULK', 'PROJECT CARGO'];
export const ALL_BERTHS = ['INMAA-B01', 'INMAA-B02', 'INMAA-B03', 'INMAA-B04', 'INMAA-B05', 'INMAA-B06', 'INMAA-B07'];

export const BERTH_COLORS: Record<string, string> = {
  'INMAA-B01': '#10b981', 'INMAA-B02': '#0ea5e9', 'INMAA-B03': '#8b5cf6',
  'INMAA-B04': '#f59e0b', 'INMAA-B05': '#ef4444', 'INMAA-B06': '#ec4899', 'INMAA-B07': '#6366f1',
};

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

/* ── Feasibility simulation ───────────────────────────── */
const BERTH_SPECS: Record<string, { max_loa: number; max_draft: number; max_beam: number; depth: number; types: string[]; equipment: string[]; cargo_handling: string[]; throughput_tph: number; has_rail: boolean; hazmat_certified: boolean; name: string }> = {
  'INMAA-B01': { max_loa: 250, max_draft: 14, max_beam: 40, depth: 14.5, types: ['Bulk Carrier', 'General Cargo'], equipment: ['Gantry Crane (45t)', 'Conveyor Belt'], cargo_handling: ['COAL', 'IRON ORE', 'GENERAL'], throughput_tph: 1200, has_rail: true, hazmat_certified: false, name: 'Bulk Terminal A1' },
  'INMAA-B02': { max_loa: 300, max_draft: 16, max_beam: 50, depth: 16.2, types: ['Container Ship', 'RoRo'], equipment: ['STS Crane (65t) x3', 'RTG Crane x4'], cargo_handling: ['CONTAINER', 'VEHICLES'], throughput_tph: 2400, has_rail: true, hazmat_certified: false, name: 'Container Terminal A2' },
  'INMAA-B03': { max_loa: 280, max_draft: 15, max_beam: 45, depth: 15.0, types: ['Bulk Carrier', 'Container Ship', 'General Cargo'], equipment: ['Mobile Harbour Crane (100t)', 'STS Crane (50t)'], cargo_handling: ['COAL', 'CONTAINER', 'GENERAL', 'IRON ORE'], throughput_tph: 1800, has_rail: false, hazmat_certified: false, name: 'Multi-purpose B3' },
  'INMAA-B04': { max_loa: 220, max_draft: 12, max_beam: 35, depth: 12.5, types: ['Chemical Tanker', 'Crude Oil Tanker'], equipment: ['Loading Arms x4', 'Vapour Recovery Unit'], cargo_handling: ['CRUDE OIL', 'CHEMICALS'], throughput_tph: 800, has_rail: false, hazmat_certified: true, name: 'Liquid Terminal B4' },
  'INMAA-B05': { max_loa: 350, max_draft: 18, max_beam: 60, depth: 18.5, types: ['Crude Oil Tanker', 'Bulk Carrier'], equipment: ['Loading Arms x6', 'Grab Crane (35t) x2'], cargo_handling: ['CRUDE OIL', 'COAL', 'IRON ORE'], throughput_tph: 3000, has_rail: true, hazmat_certified: true, name: 'Deep Water Terminal C5' },
  'INMAA-B06': { max_loa: 200, max_draft: 11, max_beam: 32, depth: 11.5, types: ['General Cargo', 'RoRo'], equipment: ['Mobile Crane (40t)', 'Ramp (RoRo)'], cargo_handling: ['GENERAL', 'VEHICLES'], throughput_tph: 600, has_rail: false, hazmat_certified: false, name: 'General Purpose D6' },
  'INMAA-B07': { max_loa: 260, max_draft: 13, max_beam: 38, depth: 13.5, types: ['Container Ship', 'Chemical Tanker'], equipment: ['STS Crane (55t) x2', 'Chemical Loading Arms'], cargo_handling: ['CONTAINER', 'CHEMICALS'], throughput_tph: 1600, has_rail: true, hazmat_certified: true, name: 'Hybrid Terminal D7' },
};

export { BERTH_SPECS };

export function computeFeasibility(vessels: VesselInput[]): FeasibilityCell[] {
  const cells: FeasibilityCell[] = [];
  for (const v of vessels) {
    for (const bc of ALL_BERTHS) {
      const spec = BERTH_SPECS[bc];
      const reasons: string[] = [];
      let score = 1.0;

      // LOA check with operational context
      if (v.loa_m > spec.max_loa) {
        reasons.push(`⛔ LOA VIOLATION: Vessel length ${v.loa_m}m exceeds berth max ${spec.max_loa}m by ${v.loa_m - spec.max_loa}m — mooring infrastructure cannot accommodate this vessel safely`);
        score -= 0.4;
      } else {
        const margin = spec.max_loa - v.loa_m;
        if (margin < 20) reasons.push(`⚠️ LOA tight fit: Only ${margin}m clearance — tugboat maneuvering may be restricted during berthing/unberthing`);
        else reasons.push(`✅ LOA safe: ${v.loa_m}m vessel fits in ${spec.max_loa}m berth with ${margin}m maneuvering clearance`);
      }

      // Draft check with UKC analysis
      const ukc = spec.depth - v.draft_m;
      if (v.draft_m > spec.max_draft) {
        reasons.push(`⛔ DRAFT VIOLATION: Required draft ${v.draft_m}m exceeds berth depth limit ${spec.max_draft}m — grounding risk at low tide`);
        score -= 0.4;
      } else if (ukc < 1.5) {
        reasons.push(`⚠️ Under-Keel Clearance only ${ukc.toFixed(1)}m (min recommended: 1.5m) — tide-dependent berthing window required, may cause delays`);
        score -= 0.1;
      } else {
        reasons.push(`✅ Draft safe: ${ukc.toFixed(1)}m under-keel clearance at ${spec.depth}m channel depth — all-tide access permitted`);
      }

      // Beam check
      if (v.beam_m > spec.max_beam) {
        reasons.push(`⛔ BEAM VIOLATION: Vessel beam ${v.beam_m}m exceeds berth width capacity ${spec.max_beam}m — crane reach insufficient`);
        score -= 0.3;
      } else {
        reasons.push(`✅ Beam OK: ${v.beam_m}m within ${spec.max_beam}m limit — full crane coverage available`);
      }

      // Vessel type compatibility with equipment context
      if (spec.types.includes(v.vessel_type)) {
        reasons.push(`✅ Vessel type match: ${spec.name} is equipped for ${v.vessel_type} ops with ${spec.equipment[0]}`);
      } else {
        reasons.push(`⚠️ Type mismatch: ${spec.name} optimized for ${spec.types.join(' / ')} — ${v.vessel_type} would require improvised handling, expect +30% service time`);
        score -= 0.2;
      }

      // Cargo handling compatibility
      if (spec.cargo_handling.includes(v.cargo_type)) {
        reasons.push(`✅ Cargo handling: ${v.cargo_type} cargo supported — ${spec.throughput_tph} TPH throughput capacity`);
      } else {
        reasons.push(`⚠️ Cargo type: ${v.cargo_type} not standard at ${spec.name} (handles: ${spec.cargo_handling.join(', ')}) — may need mobile equipment, +2-4h setup`);
        score -= 0.1;
      }

      // Throughput assessment
      if (v.cargo_tons > 0) {
        const estHours = v.cargo_tons / spec.throughput_tph;
        if (estHours < 12) reasons.push(`✅ Fast turnaround: ~${estHours.toFixed(1)}h cargo ops at ${spec.throughput_tph} TPH`);
        else if (estHours < 24) reasons.push(`ℹ️ Standard turnaround: ~${estHours.toFixed(1)}h for ${v.cargo_tons.toLocaleString()}t at ${spec.throughput_tph} TPH`);
        else reasons.push(`⚠️ Extended berth occupation: ~${estHours.toFixed(1)}h needed — consider splitting cargo across shifts`);
      }

      cells.push({ vessel_id: v.vessel_id, berth_code: bc, feasible: score > 0.3, score: Math.max(0, score), reasons });
    }
  }
  return cells;
}

export function generateExplanation(v: VesselInput, bc: string, waitH: number, confidence: number, isOverride: boolean): string {
  const spec = BERTH_SPECS[bc];
  if (!spec) return `Assigned to ${bc} with ${(confidence * 100).toFixed(0)}% confidence.`;

  const ukc = spec.depth - v.draft_m;
  const loaMargin = spec.max_loa - v.loa_m;
  const typeMatch = spec.types.includes(v.vessel_type);
  const cargoMatch = spec.cargo_handling.includes(v.cargo_type);
  const estOpsH = v.cargo_tons > 0 ? v.cargo_tons / spec.throughput_tph : v.service_hours;

  let text = '';

  if (isOverride) {
    text += `🔄 MANUAL OVERRIDE: ${v.name} manually re-assigned to ${bc} (${spec.name}). `;
  }

  // Primary assignment rationale
  text += `The CP-SAT solver assigned ${v.name} (${v.vessel_type}, ${v.loa_m}m LOA, ${v.draft_m}m draft) to ${bc} — ${spec.name}. `;

  // Physical fit analysis
  text += `Physical clearance: LOA margin ${loaMargin}m, UKC ${ukc.toFixed(1)}m (${ukc >= 1.5 ? 'all-tide access' : 'tide-restricted'}). `;

  // Equipment & handling
  if (typeMatch && cargoMatch) {
    text += `This berth has dedicated ${spec.equipment[0]} infrastructure optimized for ${v.vessel_type} handling ${v.cargo_type} cargo at ${spec.throughput_tph} TPH, yielding an estimated ${estOpsH.toFixed(1)}h cargo operations cycle. `;
  } else if (typeMatch) {
    text += `Vessel type is compatible, but ${v.cargo_type} cargo requires adaptive handling (berth standard: ${spec.cargo_handling.join(', ')}). Est. service time may increase by 15-20%. `;
  } else {
    text += `This is a cross-type assignment — ${spec.name} is primarily configured for ${spec.types.join('/')} operations. The solver chose this berth because it minimizes overall fleet waiting cost despite equipment mismatch. `;
  }

  // Wait time & cost analysis
  if (waitH < 0.5) {
    text += `Near-zero waiting time (${waitH.toFixed(1)}h) — vessel proceeds directly to berth upon arrival. `;
  } else if (waitH < 2) {
    text += `Acceptable waiting time of ${waitH.toFixed(1)}h. `;
  } else {
    text += `Elevated waiting time of ${waitH.toFixed(1)}h — driven by berth occupancy from prior vessel. Consider re-scheduling ETA window for reduced anchorage time. `;
  }

  // Confidence reasoning
  if (confidence > 0.9) {
    text += `Confidence ${(confidence * 100).toFixed(0)}%: Strong physical fit, type-matched equipment, and SLA-compliant schedule.`;
  } else if (confidence > 0.7) {
    text += `Confidence ${(confidence * 100).toFixed(0)}%: Good assignment with minor trade-offs in equipment matching or wait time.`;
  } else {
    text += `Confidence ${(confidence * 100).toFixed(0)}%: Marginal assignment — review alternatives for potential improvement.`;
  }

  return text;
}

export function getSampleResult(vessels: VesselInput[], overrides?: Map<string, string>): OptimizerResult {
  const berths = ['INMAA-B01', 'INMAA-B03', 'INMAA-B06', 'INMAA-B02', 'INMAA-B05'];
  const feasibility_matrix = computeFeasibility(vessels);

  const assignments: ScheduleAssignment[] = vessels.map((v, i) => {
    const bc = overrides?.get(v.vessel_id) || berths[i % berths.length];
    const waitH = i * 0.5 + (overrides?.has(v.vessel_id) ? 0.3 : 0);
    const cell = feasibility_matrix.find(c => c.vessel_id === v.vessel_id && c.berth_code === bc);
    const confidence = cell ? Math.min(0.98, cell.score * 0.6 + 0.35) : 0.75;
    return {
      vessel_id: v.vessel_id, vessel_name: v.name, berth_code: bc,
      start_hours: v.eta_hours + waitH, end_hours: v.eta_hours + v.service_hours + waitH,
      waiting_hours: waitH, service_hours: v.service_hours, sla_exceeded: false,
      confidence, explanation: generateExplanation(v, bc, waitH, confidence, !!overrides?.has(v.vessel_id)),
    };
  });

  const costs: CostBreakdown[] = vessels.map((v, i) => {
    const bc = overrides?.get(v.vessel_id) || berths[i % berths.length];
    const spec = BERTH_SPECS[bc];
    const waitCost = (i * 0.5) * 1000 + 200;
    const fuelCost = 1200 + i * 300;
    const equipCost = spec ? (spec.types.includes(v.vessel_type) ? 800 : 1200) : 800;
    return {
      vessel_id: v.vessel_id, vessel_name: v.name, berth_code: bc,
      waiting_cost: waitCost, fuel_burn_cost: fuelCost,
      equipment_rental: equipCost, sla_penalty: 0, net_cost: waitCost + fuelCost + equipCost,
    };
  });

  const ranked_alternatives: Record<string, RankedAlternative[]> = {};
  for (const v of vessels) {
    const vCells = feasibility_matrix.filter(c => c.vessel_id === v.vessel_id && c.feasible);
    ranked_alternatives[v.vessel_id] = vCells
      .sort((a, b) => b.score - a.score)
      .slice(0, 5)
      .map((c, idx) => ({
        berth_code: c.berth_code, score: c.score,
        waiting_hours: idx * 0.8 + 0.5, cost_delta: idx * 400 - 200,
        confidence: Math.min(0.98, c.score * 0.6 + 0.35), reasons: c.reasons,
      }));
  }

  return {
    status: 'OPTIMAL', solve_time_sec: 1.24, assignments, costs,
    kpis: { avg_wait: 1.5, utilization: 72, sla_compliance: 100, total_revenue: 85000, total_cost: costs.reduce((s, c) => s + c.net_cost, 0), cargo_tons: vessels.reduce((s, v) => s + v.cargo_tons, 0) },
    feasibility_matrix, ranked_alternatives,
  };
}
