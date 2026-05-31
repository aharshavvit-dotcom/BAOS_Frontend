/**
 * StatusBadge â€” Source quality indicator badge.
 */
'use client';

import type { AssumptionSource } from '@/lib/constants/assumptionDefaults';
import { FileText, BarChart3, Brain, Edit3, AlertTriangle, Play, Server } from 'lucide-react';

const BADGE_CONFIG: Record<string, { bg: string; text: string; label: string; icon: React.ReactNode }> = {
  SPEC: { bg: 'rgba(16,185,129,0.12)', text: '#10b981', label: 'Spec-Derived', icon: <FileText size={12} /> },
  HISTORICAL: { bg: 'rgba(14,165,233,0.12)', text: '#0ea5e9', label: 'Historical', icon: <BarChart3 size={12} /> },
  ML_PREDICTED: { bg: 'rgba(139,92,246,0.12)', text: '#8b5cf6', label: 'ML Predicted', icon: <Brain size={12} /> },
  USER_INPUT: { bg: 'rgba(16,185,129,0.12)', text: '#10b981', label: 'User Input', icon: <Edit3 size={12} /> },
  ASSUMPTION: { bg: 'rgba(245,158,11,0.12)', text: '#f59e0b', label: 'Estimated', icon: <AlertTriangle size={12} /> },
  DEMO: { bg: 'rgba(239,68,68,0.12)', text: '#ef4444', label: 'Demo Data', icon: <Play size={12} /> },
  BACKEND: { bg: 'rgba(16,185,129,0.12)', text: '#10b981', label: 'Live', icon: <Server size={12} /> },
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
      display: 'inline-flex', alignItems: 'center', gap: 4,
      whiteSpace: 'nowrap',
    }}>
      {showIcon && <span style={{ display: 'inline-flex', alignItems: 'center' }}>{cfg.icon}</span>}
      {cfg.label}
    </span>
  );
}
