/**
 * ScenarioImpactBanner â€” Shows deltas after a manual override or what-if scenario.
 */
'use client';

import { ArrowUp, ArrowDown, Minus, BarChart3, AlertTriangle, X } from 'lucide-react';

interface ScenarioImpactBannerProps {
  waitingHoursDelta: number;
  costDelta: number;
  objectiveDelta: number;
  confidenceDelta?: number;
  slaRiskDelta?: number;
  conflicts?: string[];
  onDismiss?: () => void;
}

function DeltaChip({ label, value, unit, inverted = false }: {
  label: string; value: number; unit: string; inverted?: boolean;
}) {
  const isPositive = inverted ? value < 0 : value > 0;
  const isNegative = inverted ? value > 0 : value < 0;
  const color = isPositive ? '#10b981' : isNegative ? '#ef4444' : '#94a3b8';
  const icon = value > 0 ? <ArrowUp size={14} className="inline mr-0.5" /> : value < 0 ? <ArrowDown size={14} className="inline mr-0.5" /> : <Minus size={14} className="inline mr-0.5" />;

  return (
    <div style={{ textAlign: 'center', padding: '8px 12px' }}>
      <div style={{ fontSize: 18, fontWeight: 800, color, fontFamily: 'var(--font-display)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {icon} {Math.abs(value).toFixed(1)}{unit}
      </div>
      <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
        {label}
      </div>
    </div>
  );
}

export function ScenarioImpactBanner({
  waitingHoursDelta,
  costDelta,
  objectiveDelta,
  confidenceDelta = 0,
  slaRiskDelta = 0,
  conflicts = [],
  onDismiss,
}: ScenarioImpactBannerProps) {
  const hasImpact = waitingHoursDelta !== 0 || costDelta !== 0 || objectiveDelta !== 0;
  if (!hasImpact) return null;

  const netPositive = objectiveDelta <= 0;

  return (
    <div style={{
      background: netPositive ? 'rgba(16,185,129,0.06)' : 'rgba(245,158,11,0.06)',
      border: `1px solid ${netPositive ? 'rgba(16,185,129,0.25)' : 'rgba(245,158,11,0.25)'}`,
      borderRadius: 10, padding: '16px 20px', marginBottom: 20,
    }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {netPositive ? <BarChart3 size={18} className="text-emerald-500" /> : <AlertTriangle size={18} className="text-amber-500" />}
          <span style={{
            fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15,
            color: 'var(--color-text-primary)',
          }}>
            Scenario Impact Analysis
          </span>
          <span className="badge" style={{
            background: netPositive ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
            color: netPositive ? '#10b981' : '#f59e0b',
            fontSize: 10, fontWeight: 700,
          }}>
            {netPositive ? 'IMPROVED' : 'TRADE-OFF'}
          </span>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--color-text-muted)', display: 'inline-flex', alignItems: 'center'
          }}>
            <X size={16} />
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
        <DeltaChip label="Wait Time" value={waitingHoursDelta} unit="h" inverted />
        <DeltaChip label="Cost" value={costDelta} unit="$" inverted />
        <DeltaChip label="Objective" value={objectiveDelta} unit="" inverted />
        <DeltaChip label="Confidence" value={confidenceDelta} unit="%" />
        <DeltaChip label="SLA Risk" value={slaRiskDelta} unit="%" inverted />
      </div>

      {conflicts.length > 0 && (
        <div style={{
          marginTop: 10, padding: '8px 12px',
          background: 'rgba(239,68,68,0.06)', borderRadius: 6,
          fontSize: 12, color: '#ef4444',
          display: 'flex', alignItems: 'center', gap: 6
        }}>
          <AlertTriangle size={14} /> Conflicts: {conflicts.join('; ')}
        </div>
      )}
    </div>
  );
}
