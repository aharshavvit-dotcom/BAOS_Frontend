/**
 * BAOS API — Barrel export for all API services
 */
export { default as apiClient, extractApiError, getApiBaseUrl } from './client';
export type { ApiError, ApiEnvelope } from './client';

export * from './ports';
export * from './optimizer';
export * from './recommendations';
export * from './feasibility';
export * from './scenarios';
