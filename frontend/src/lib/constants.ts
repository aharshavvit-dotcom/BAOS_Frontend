export const PORT_CODES = {
  CHENNAI: 'INMAA',
} as const;

export const STATUS_COLORS: Record<string, string> = {
  Assigned: 'bg-green-100 text-green-800',
  Pending: 'bg-yellow-100 text-yellow-800',
  'In Progress': 'bg-blue-100 text-blue-800',
  Completed: 'bg-gray-100 text-gray-700',
  Cancelled: 'bg-red-100 text-red-800',
  Delayed: 'bg-orange-100 text-orange-800',
} as const;

export const VESSEL_TYPES = [
  'Container',
  'Bulk Carrier',
  'Tanker',
  'General Cargo',
  'Ro-Ro',
  'Passenger',
  'Offshore Supply',
] as const;

export const ROUTE_PATHS = {
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  BERTHS: '/berths',
  ALLOCATIONS: '/allocations',
  RECOMMENDATIONS: '/recommendations',
  ANALYTICS: '/analytics',
  TRAINING: '/training',
  SETTINGS: '/settings',
} as const;

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL || API_BASE_URL;
