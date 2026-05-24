/**
 * BAOS — Recommendation API Service
 *
 * Calls POST /api/v1/recommendations/get-recommendation with correct schema.
 * Maps between frontend form fields and backend expected fields.
 */
import apiClient from './client';

// Frontend Form Type---

export interface RecommendationFormData {
  vessel_name: string;
  vessel_type: string;
  cargo_type: string;
  loa_m: number;
  beam_m: number;
  draft_m: number;
  dwt: number;
  cargo_tons: number;
  eta: string; // ISO datetime string
  port_code: string;
}

// Backend Request/Response Types

interface BackendRecommendationRequest {
  vessel_name: string;
  vessel_type: string;
  cargo_type: string;
  loa_m: number;
  beam_m: number;
  draft_m: number;
  dwt: number;
  cargo_tons: number;
  eta: string;
  port_code: string;
}

export interface BerthRecommendation {
  berth_code: string;
  berth_name: string;
  confidence: number;
  technical_score: number;
  commercial_score: number;
  suitability_score: number;
  risk_score: number;
  expected_wait_hours: number;
  expected_service_hours: number;
  pros: string[];
  cons: string[];
  explanation: string;
  compact_reason: string;
  ai_reasoning: string;
  structured_breakdown: ParameterCheck[];
  rank: number;
  timeline_start: number;
  timeline_end: number;
}

export interface ParameterCheck {
  category: string;
  parameter: string;
  status: 'pass' | 'ok' | 'tight' | 'fail' | 'info';
  icon: string;
  detail: string;
  compact: string;
}

export interface RecommendationResponse {
  recommendation_id?: string;
  recommendations: BerthRecommendation[];
  vessel_name: string;
  port_code: string;
  warnings?: string[];
  assumptions_used?: string[];
  source: 'BACKEND' | 'DEMO';
}

// API Function---

/**
 * Get berth recommendations for a vessel.
 *
 * Sends the CORRECT schema to the backend:
 * - vessel_name (not "name")
 * - loa_m (not "loa")
 * - beam_m (not "beam")
 * - draft_m (not "draft")
 *
 * Reads response from data.recommendations (not data.options).
 */
export async function getRecommendation(
  form: RecommendationFormData,
): Promise<RecommendationResponse> {
  const payload: BackendRecommendationRequest = {
    vessel_name: form.vessel_name,
    vessel_type: form.vessel_type,
    cargo_type: form.cargo_type,
    loa_m: form.loa_m,
    beam_m: form.beam_m,
    draft_m: form.draft_m,
    dwt: form.dwt,
    cargo_tons: form.cargo_tons,
    eta: form.eta,
    port_code: form.port_code,
  };

  const res = await apiClient.post('/api/v1/recommendations/get-recommendation', payload);
  const data = res.data;

  // Handle both response formats: { recommendations: [...] } or { options: [...] }
  const recs = data.recommendations || data.options || [];

  return {
    recommendation_id: data.recommendation_id,
    recommendations: recs.map((r: Record<string, unknown>, idx: number) => ({
      ...r,
      rank: (r.rank as number) || idx + 1,
    })) as BerthRecommendation[],
    vessel_name: form.vessel_name,
    port_code: form.port_code,
    warnings: data.warnings || [],
    assumptions_used: data.assumptions_used || [],
    source: 'BACKEND' as const,
  };
}

