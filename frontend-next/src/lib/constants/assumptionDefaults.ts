/**
 * Assumption-based placeholders for cost/decision factors.
 *
 * These defaults are used when real operational data is unavailable.
 * Each placeholder includes metadata so the UI can display source quality
 * and the optimizer can apply confidence adjustments.
 *
 * @see Section 2.3 of the upgrade spec
 */

export type AssumptionSource =
  | 'SPEC'
  | 'HISTORICAL'
  | 'ML_PREDICTED'
  | 'USER_INPUT'
  | 'ASSUMPTION'
  | 'DEMO';

export interface AssumptionDefault {
  key: string;
  value: number;
  unit: string;
  source: AssumptionSource;
  confidenceMultiplier: number;
  description: string;
  usedInDecision: boolean;
  category: 'cost' | 'penalty' | 'reward' | 'resource' | 'safety' | 'commercial';
}

export const ASSUMPTION_DEFAULTS: AssumptionDefault[] = [
  {
    key: 'DEMURRAGE_RATE_USD_PER_HOUR',
    value: 500,
    unit: 'USD/hour',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.8,
    description:
      'Default demurrage estimate used when vessel-specific rate is unavailable. Typical range: $200–$2,000/hr depending on vessel size.',
    usedInDecision: true,
    category: 'cost',
  },
  {
    key: 'FUEL_WAIT_RATE_USD_PER_HOUR',
    value: 150,
    unit: 'USD/hour',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.7,
    description:
      'Estimated fuel burn cost while vessel is anchored waiting for berth. Based on typical anchorage fuel consumption.',
    usedInDecision: true,
    category: 'cost',
  },
  {
    key: 'SLA_PENALTY_USD_PER_HOUR',
    value: 1000,
    unit: 'USD/hour',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.6,
    description:
      'Penalty per hour of SLA wait-time violation. Requires real contract data for production use.',
    usedInDecision: true,
    category: 'penalty',
  },
  {
    key: 'REVENUE_PER_TON_USD',
    value: 2.5,
    unit: 'USD/ton',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.5,
    description:
      'Estimated port revenue per cargo ton. Varies widely by cargo type and terminal.',
    usedInDecision: true,
    category: 'commercial',
  },
  {
    key: 'UNASSIGNED_PENALTY_USD',
    value: 100000,
    unit: 'USD',
    source: 'ASSUMPTION',
    confidenceMultiplier: 1.0,
    description:
      'Heavy penalty for leaving a vessel unassigned. Set very high to prefer assignment over rejection.',
    usedInDecision: true,
    category: 'penalty',
  },
  {
    key: 'SCHEDULE_CHANGE_PENALTY_USD',
    value: 5000,
    unit: 'USD',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.7,
    description:
      'Penalty for changing a vessel\'s berth assignment from the previous schedule. Represents operational disruption cost.',
    usedInDecision: true,
    category: 'penalty',
  },
  {
    key: 'RISK_PENALTY_MULTIPLIER',
    value: 1000,
    unit: 'multiplier',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.6,
    description:
      'Multiplier applied to low-confidence assignments in the objective function.',
    usedInDecision: true,
    category: 'penalty',
  },
  {
    key: 'BERTH_IDLE_PENALTY_USD_PER_HOUR',
    value: 200,
    unit: 'USD/hour',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.5,
    description:
      'Cost of berth sitting idle. Encourages balanced utilization across berths.',
    usedInDecision: false,
    category: 'cost',
  },
  {
    key: 'THROUGHPUT_VALUE_USD_PER_TON_HOUR',
    value: 0.5,
    unit: 'USD/ton·hour',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.4,
    description:
      'Value of throughput efficiency. Higher throughput berths get a bonus in the objective.',
    usedInDecision: false,
    category: 'reward',
  },
  {
    key: 'PILOT_CAPACITY',
    value: 2,
    unit: 'pilots',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.8,
    description:
      'Number of pilots available for simultaneous vessel movements. Requires real pilot schedule data.',
    usedInDecision: true,
    category: 'resource',
  },
  {
    key: 'TUG_CAPACITY',
    value: 3,
    unit: 'tugs',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.8,
    description:
      'Number of tugs available for simultaneous vessel movements. Requires real tug schedule data.',
    usedInDecision: true,
    category: 'resource',
  },
  {
    key: 'CHANNEL_CAPACITY',
    value: 1,
    unit: 'movements',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.9,
    description:
      'Maximum simultaneous channel movements. Constrains how many vessels can enter/exit at once.',
    usedInDecision: true,
    category: 'resource',
  },
  {
    key: 'UKC_SAFETY_MARGIN_M',
    value: 0.5,
    unit: 'meters',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.9,
    description:
      'Under-keel clearance safety margin added to vessel draft for berthing checks.',
    usedInDecision: true,
    category: 'safety',
  },
  {
    key: 'WEATHER_DISRUPTION_HOURS_PER_WEEK',
    value: 0,
    unit: 'hours/week',
    source: 'ASSUMPTION',
    confidenceMultiplier: 0.3,
    description:
      'Estimated weather disruption per planning horizon. Requires real meteorological data for production use.',
    usedInDecision: false,
    category: 'safety',
  },
];

/** Lookup helper: get assumption by key */
export function getAssumption(key: string): AssumptionDefault | undefined {
  return ASSUMPTION_DEFAULTS.find((a) => a.key === key);
}

/** Get all assumptions used in the decision objective */
export function getDecisionAssumptions(): AssumptionDefault[] {
  return ASSUMPTION_DEFAULTS.filter((a) => a.usedInDecision);
}

/** Get assumptions grouped by category */
export function getAssumptionsByCategory(): Record<string, AssumptionDefault[]> {
  const grouped: Record<string, AssumptionDefault[]> = {};
  for (const a of ASSUMPTION_DEFAULTS) {
    if (!grouped[a.category]) grouped[a.category] = [];
    grouped[a.category].push(a);
  }
  return grouped;
}

/** Risk level thresholds */
export const RISK_LEVELS = {
  LOW: { min: 85, label: 'Low Risk', color: '#10b981' },
  MEDIUM: { min: 65, max: 84, label: 'Medium Risk', color: '#f59e0b' },
  HIGH: { max: 64, label: 'High Risk', color: '#ef4444' },
} as const;

export function getRiskLevel(confidencePct: number) {
  if (confidencePct >= 85) return RISK_LEVELS.LOW;
  if (confidencePct >= 65) return RISK_LEVELS.MEDIUM;
  return RISK_LEVELS.HIGH;
}
