/**
 * BAOS API â€” Barrel export for all API services
 */
export { default as apiClient, extractApiError, getApiBaseUrl } from './client';
export type { ApiError, ApiEnvelope } from './client';

export * from './ports';
export * from './optimizer';
export * from './recommendations';
export * from './feasibility';
export * from './scenarios';
export * from './api';
export * from './portService';
export * from './berthService';
export * from './allocationService';
export * from './recommendationService';
export * from './trainingService';
export * from './analyticsService';
export * from './authService';
