import type { DashboardRecommendation } from '@/types';

export const DEMO_MONTHLY_DATA = [
  { metric: 'Vessels',       current: 142, previous: 131 },
  { metric: 'Revenue ($K)',  current: 480, previous: 420 },
  { metric: 'Utilization',   current: 78,  previous: 75 },
  { metric: 'SLA %',         current: 94,  previous: 89 },
];

export const DEMO_UTILIZATION_TREND = [
  { day: 'Mon', util: 72 }, { day: 'Tue', util: 78 },
  { day: 'Wed', util: 75 }, { day: 'Thu', util: 82 },
  { day: 'Fri', util: 80 }, { day: 'Sat', util: 55 },
  { day: 'Sun', util: 48 },
];

export const DEMO_VESSEL_DIST = [
  { name: 'Container', value: 35, color: 'rgba(0,102,204,0.8)' },
  { name: 'Bulk', value: 22, color: 'rgba(0,170,153,0.8)' },
  { name: 'General', value: 18, color: 'rgba(139,92,246,0.8)' },
  { name: 'Tanker', value: 15, color: 'rgba(245,158,11,0.8)' },
  { name: 'RoRo', value: 10, color: 'rgba(236,72,153,0.8)' },
];

export const DEMO_COST_DATA = [
  { category: 'Fuel',      cost: 45 },
  { category: 'Equipment', cost: 38 },
  { category: 'Waiting',   cost: 28 },
  { category: 'SLA',       cost: 12 },
  { category: 'Handling',  cost: 52 },
];

export const DEMO_COST_COLORS = [
  'rgba(239,68,68,0.7)',
  'rgba(245,158,11,0.7)',
  'rgba(59,130,246,0.7)',
  'rgba(139,92,246,0.7)',
  'rgba(0,170,153,0.7)'
];

export const DEMO_SAMPLE_RECS: DashboardRecommendation[] = [
  { id: 'rec-001', vessel_name: 'MV Ocean Crown',    vessel_type: 'Container Ship',   berth_name: 'Berth A1 (Container Terminal)', confidence: 92.5, status: 'pending',  created_at: '2026-03-30T10:30:00Z' },
  { id: 'rec-002', vessel_name: 'SS Pacific Trader', vessel_type: 'Bulk Carrier',     berth_name: 'Berth B3 (Bulk Terminal)',       confidence: 87.3, status: 'accepted', created_at: '2026-03-29T15:45:00Z' },
  { id: 'rec-003', vessel_name: 'MT Horizon Star',   vessel_type: 'Crude Oil Tanker', berth_name: 'Berth C2 (Oil Terminal)',        confidence: 95.1, status: 'pending',  created_at: '2026-03-30T08:00:00Z' },
  { id: 'rec-004', vessel_name: 'MV Jade Express',   vessel_type: 'General Cargo',    berth_name: 'Berth A3 (Multi-purpose)',      confidence: 78.9, status: 'rejected', created_at: '2026-03-28T12:20:00Z' },
];
