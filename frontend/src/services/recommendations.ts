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
    recommendations: recs.map((r: Record<string, any>, idx: number) => {
      const wait = typeof r.expected_wait_hours === 'number' ? r.expected_wait_hours : 0.0;
      const svc = typeof r.expected_service_hours === 'number' ? r.expected_service_hours : (typeof r.expected_turnaround_hours === 'number' ? r.expected_turnaround_hours : 24.0);
      const timeline_start = typeof r.timeline_start === 'number' ? r.timeline_start : 0.0;
      const timeline_end = typeof r.timeline_end === 'number' ? r.timeline_end : (timeline_start + wait + svc);

      const reasoning = r.reasoning || {};
      const pros = Array.isArray(reasoning.pros) ? reasoning.pros : (Array.isArray(r.pros) ? r.pros : []);
      const cons = Array.isArray(reasoning.cons) ? reasoning.cons : (Array.isArray(r.cons) ? r.cons : []);
      const headline = reasoning.headline || r.explanation || r.compact_reason || '';

      return {
        berth_code: r.berth_code || '',
        berth_name: r.berth_name || '',
        confidence: typeof r.confidence === 'number' ? r.confidence : 80,
        technical_score: typeof r.technical_score === 'number' ? r.technical_score : (typeof r.suitability_score === 'number' ? r.suitability_score : 80),
        commercial_score: typeof r.commercial_score === 'number' ? r.commercial_score : 0,
        suitability_score: typeof r.suitability_score === 'number' ? r.suitability_score : (typeof r.technical_score === 'number' ? r.technical_score : 80),
        risk_score: typeof r.risk_score === 'number' ? r.risk_score : 0,
        expected_wait_hours: wait,
        expected_service_hours: svc,
        pros: pros,
        cons: cons,
        explanation: r.explanation || headline,
        compact_reason: r.compact_reason || headline,
        ai_reasoning: r.ai_reasoning || headline,
        structured_breakdown: Array.isArray(r.structured_breakdown) ? r.structured_breakdown : [],
        rank: (r.rank as number) || idx + 1,
        timeline_start: timeline_start,
        timeline_end: timeline_end,
      };
    }) as BerthRecommendation[],
    vessel_name: form.vessel_name,
    port_code: form.port_code,
    warnings: data.warnings || [],
    assumptions_used: data.assumptions_used || [],
    source: 'BACKEND' as const,
  };
}

