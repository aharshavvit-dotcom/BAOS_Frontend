/**
 * BAOS — Feasibility API Service
 *
 * Calls POST /api/v1/feasibility to get backend-computed feasibility matrix.
 * Replaces the frontend-only feasibility computation.
 */
import apiClient from './client';

// --- Types ---

export interface FeasibilityVessel {
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
}

export interface FeasibilityRequest {
  port_code: string;
  vessels: FeasibilityVessel[];
}

export interface FeasibilityCheck {
  feasible: boolean;
  hard_violations: string[];
  soft_violations: string[];
  score: number;
  summary: string;
}

export interface FeasibilityMatrixResponse {
  port_code: string;
  matrix: Record<string, Record<string, FeasibilityCheck>>;
}

/** Flattened cell for display */
export interface FeasibilityCell {
  vessel_id: string;
  berth_code: string;
  feasible: boolean;
  score: number;
  hard_fails: string[];
  soft_warnings: string[];
  summary: string;
}

// --- API Function ---

/** Get feasibility matrix from backend */
export async function getFeasibilityMatrix(
  request: FeasibilityRequest,
): Promise<FeasibilityCell[]> {
  const res = await apiClient.post<FeasibilityMatrixResponse>(
    '/api/v1/feasibility',
    request,
  );

  // Flatten nested matrix into array of cells
  const cells: FeasibilityCell[] = [];
  const matrix = res.data.matrix;

  for (const vesselId of Object.keys(matrix)) {
    const vesselRow = matrix[vesselId];
    for (const berthCode of Object.keys(vesselRow)) {
      const check = vesselRow[berthCode];
      cells.push({
        vessel_id: vesselId,
        berth_code: berthCode,
        feasible: check.feasible,
        score: check.score,
        hard_fails: check.hard_violations || [],
        soft_warnings: check.soft_violations || [],
        summary: check.summary || '',
      });
    }
  }

  return cells;
}

