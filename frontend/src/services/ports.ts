/**
 * BAOS — Port API Service
 *
 * Endpoints:
 *   GET /api/v1/ports
 *   GET /api/v1/ports/{port_code}/status
 *   GET /api/v1/ports/{port_code}/config
 */
import apiClient from './client';

// Types---

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PortInfo {
  port_name: string;
  port_code: string;
  trained: boolean;
  training_status: TrainingStatus;
  status_label: string;
  training_message: string;
  num_berths: number;
  history_rows?: number;
  valid_training_rows?: number;
  models_missing?: string[];
  models_stale?: string[];
  model_info: PortModelInfo | null;
}

export type TrainingStatus =
  | 'data_missing'
  | 'data_loaded_training_pending'
  | 'training_in_progress'
  | 'trained'
  | 'training_failed'
  | 'insufficient_data';

export interface PortModelInfo {
  model_version?: string;
  training_date?: string;
  training_rows?: number;
  features_used?: string[];
  feature_count?: number;
  split_strategy?: string;
  metrics?: Record<string, number>;
  data_date_range?: string;
  known_limitations?: string[];
}

export interface PortStatus {
  port_name: string;
  port_code: string;
  trained: boolean;
  training_status: TrainingStatus;
  status_label: string;
  training_message: string;
  has_enough_data: boolean;
  is_stale: boolean;
  models_required: string[];
  models_active: string[];
  models_missing: string[];
  models_stale: string[];
  model_info: PortModelInfo | null;
  data_quality: DataQuality;
  berth_count: number;
  capability_count: number;
  history_rows: number;
  valid_training_rows: number;
  berth_class_count: number;
}

export interface DataQuality {
  overall_score: number;
  source: 'SPEC' | 'HISTORICAL' | 'ASSUMPTION';
  completeness_pct: number;
  recency_days: number;
}

export interface BerthConfig {
  berth_code: string;
  berth_name: string;
  terminal_code: string;
  terminal_name: string;
  port_code: string;
  port_name: string;
  max_loa_m: number;
  max_draft_m: number;
  depth_m: number;
  max_beam_m: number;
  allowed_vessel_types: string[];
  equipment: string[];
  allow_24x7: boolean;
}

export interface PortConfig {
  port_name: string;
  port_code: string;
  planning_start: string;
  num_berths: number;
  berths: BerthConfig[];
  service_time_stats: ServiceTimeStat[];
  vessel_types: string[];
  cargo_types: string[];
}

export interface ServiceTimeStat {
  berth_code: number | string;
  vessel_type: string | null;
  count: number;
  service_hours_median: number;
  service_hours_mean: number;
}

// API Functions---

/** List all available ports with training status */
export async function getPorts(): Promise<PortInfo[]> {
  const res = await apiClient.get<PaginatedResponse<PortInfo>>('/api/v1/ports');
  return res.data?.items ?? [];
}

/** Get detailed status for a specific port */
export async function getPortStatus(portCode: string): Promise<PortStatus> {
  const res = await apiClient.get<PortStatus>(`/api/v1/ports/${encodeURIComponent(portCode.trim().toUpperCase())}/status`);
  return res.data;
}

/** Get full port configuration including berth inventory */
export async function getPortConfig(portCode: string): Promise<PortConfig> {
  const res = await apiClient.get<PortConfig>(`/api/v1/ports/${encodeURIComponent(portCode.trim().toUpperCase())}/config`);
  return res.data;
}

