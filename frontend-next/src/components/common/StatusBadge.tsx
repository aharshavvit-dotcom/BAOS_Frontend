/**
 * StatusBadge — Source quality indicator badge.
 */
'use client';

import type { AssumptionSource } from '@/lib/constants/assumptionDefaults';

const BADGE_CONFIG: Record<string, { bg: string; text: string; label: string; icon: string }> = {
  SPEC: { bg: 'rgba(16,185,129,0.12)', text: '#10b981', label: 'Spec-Derived', icon: '📋' },
  HISTORICAL: { bg: 'rgba(14,165,233,0.12)', text: '#0ea5e9', label: 'Historical', icon: '📊' },
  ML_PREDICTED: { bg: 'rgba(139,92,246,0.12)', text: '#8b5cf6', label: 'ML Predicted', icon: '🧠' },
  USER_INPUT: { bg: 'rgba(16,185,129,0.12)', text: '#10b981', label: 'User Input', icon: '✍️' },
  ASSUMPTION: { bg: 'rgba(245,158,11,0.12)', text: '#f59e0b', label: 'Estimated', icon: '⚠️' },
  DEMO: { bg: 'rgba(239,68,68,0.12)', text: '#ef4444', label: 'Demo Data', icon: '🎮' },
  BACKEND: { bg: 'rgba(16,185,129,0.12)', text: '#10b981', label: 'Live', icon: '🟢' },
};

interface StatusBadgeProps {
  source: AssumptionSource | 'BACKEND';
  size?: 'sm' | 'md';
  showIcon?: boolean;
}

export function StatusBadge({ source, size = 'sm', showIcon = true }: StatusBadgeProps) {
  const cfg = BADGE_CONFIG[source] || BADGE_CONFIG.ASSUMPTION;
  const fontSize = size === 'sm' ? 9 : 11;
  const padding = size === 'sm' ? '1px 6px' : '2px 10px';

  return (
    <span style={{
      background: cfg.bg, color: cfg.text,
      padding, borderRadius: 8,
      fontSize, fontWeight: 700,
      textTransform: 'uppercase', letterSpacing: 0.5,
      display: 'inline-flex', alignItems: 'center', gap: 3,
      whiteSpace: 'nowrap',
    }}>
      {showIcon && <span style={{ fontSize: fontSize + 2 }}>{cfg.icon}</span>}
      {cfg.label}
    </span>
  );
}
