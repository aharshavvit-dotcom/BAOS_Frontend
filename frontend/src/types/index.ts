/**
 * BAOS AI — TypeScript type definitions.
 */

// --- Auth ---

export interface User {
  id: string;
  email: string;
  full_name: string;
  company: string;
  port_code: string | null;
  port_name: string | null;
  role: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface SignupData {
  email: string;
  password: string;
  full_name: string;
  company: string;
  port_code: string;
}

// --- Dashboard ---

export interface KPIValue {
  label: string;
  value: number | string;
  change_pct?: number;
  trend?: 'up' | 'down' | 'flat';
  icon?: string;
}

export interface KPIData {
  vessels_count: number;
  revenue: number;
  cost: number;
  utilization_pct: number;
  sla_compliance_pct: number;
  avg_turnaround_hours: number;
  kpi_cards: KPIValue[];
}

export interface ChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string | string[];
  borderColor?: string;
  borderWidth?: number;
  fill?: boolean;
  tension?: number;
  borderRadius?: number;
  borderSkipped?: boolean;
  borderDash?: number[];
  pointRadius?: number;
  pointBackgroundColor?: string;
  pointBorderColor?: string;
  pointBorderWidth?: number;
  type?: string;
  hoverOffset?: number;
}

export interface ChartData {
  labels: string[];
  datasets: ChartDataset[];
}

export interface ChartsData {
  monthly_comparison: ChartData;
  utilization_trend: ChartData;
  vessel_distribution: ChartData;
  cost_breakdown: ChartData;
}

// --- Recommendations ---

export interface BerthRecommendation {
  berth_code: string;
  berth_name: string;
  confidence: number;
  technical_score: number;
  commercial_score: number;
  reasoning: Record<string, unknown>;
  expected_turnaround_hours?: number;
}

export interface RecommendationResponse {
  recommendation_id: string;
  recommendations: BerthRecommendation[];
  vessel_name: string;
  port_code: string;
}

export interface DashboardRecommendation {
  id: string;
  vessel_name: string;
  vessel_type: string;
  berth_name: string;
  confidence: number;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: string;
}

export interface RecommendationRequest {
  vessel_name: string;
  vessel_type: string;
  loa_m: number;
  beam_m: number;
  draft_m: number;
  dwt: number;
  cargo_type: string;
  cargo_tons: number;
  eta?: string;
  port_code: string;
}

// --- Vessel & Port ---

export interface Vessel {
  id: string;
  name: string;
  vessel_type: string;
  loa_m: number;
  beam_m: number;
  draft_m: number;
  dwt: number;
  cargo_type: string;
  cargo_tons: number;
  imo_number: string;
  company: string;
}

export interface Port {
  id: string;
  name: string;
  code: string;
  country: string;
}

export interface Berth {
  id: string;
  port_id: string;
  code: string;
  name: string;
  max_loa_m: number;
  max_beam_m: number;
  max_draft_m: number;
  depth_m: number;
  is_available: boolean;
}

// --- UI ---

export interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
}

export type FilterStatus = 'all' | 'pending' | 'accepted' | 'rejected';

