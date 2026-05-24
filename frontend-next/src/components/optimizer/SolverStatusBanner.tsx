/**
 * SolverStatusBanner — Shows optimizer solve status with contextual styling.
 */
'use client';

import type { SolverStatus } from '@/lib/api/optimizer';

interface SolverStatusBannerProps {
  status: SolverStatus;
  message: string;
  solveTimeSec?: number;
  assignedCount?: number;
  totalCount?: number;
  unassignedVessels?: string[];
}

const STATUS_CONFIG: Record<SolverStatus, { bg: string; border: string; icon: string; textColor: string }> = {
  OPTIMAL: {
    bg: 'rgba(16,185,129,0.08)',
    border: 'rgba(16,185,129,0.3)',
    icon: '✅',
    textColor: '#10b981',
  },
  FEASIBLE: {
    bg: 'rgba(14,165,233,0.08)',
    border: 'rgba(14,165,233,0.3)',
    icon: '✔️',
    textColor: '#0ea5e9',
  },
  INFEASIBLE: {
    bg: 'rgba(239,68,68,0.08)',
    border: 'rgba(239,68,68,0.3)',
    icon: '❌',
    textColor: '#ef4444',
  },
  TIMEOUT: {
    bg: 'rgba(245,158,11,0.08)',
    border: 'rgba(245,158,11,0.3)',
    icon: '⏱️',
    textColor: '#f59e0b',
  },
  ERROR: {
    bg: 'rgba(239,68,68,0.08)',
    border: 'rgba(239,68,68,0.3)',
    icon: '⚠️',
    textColor: '#ef4444',
  },
};

export function SolverStatusBanner({
  status,
  message,
  solveTimeSec,
  assignedCount,
  totalCount,
  unassignedVessels,
}: SolverStatusBannerProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.ERROR;

  return (
    <div style={{
      background: config.bg,
      border: `1px solid ${config.border}`,
      borderRadius: 10,
      padding: '14px 20px',
      marginBottom: 20,
    }}>
      <div className="flex items-center gap-3">
        <span style={{ fontSize: 20 }}>{config.icon}</span>
        <div className="flex-1">
          <div style={{ fontSize: 14, fontWeight: 700, color: config.textColor, marginBottom: 2 }}>
            {status}
            {solveTimeSec !== undefined && (
              <span style={{ fontWeight: 400, fontSize: 12, marginLeft: 8, color: 'var(--color-text-muted)' }}>
                Solved in {solveTimeSec.toFixed(2)}s
              </span>
            )}
          </div>
          <div style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>
            {message}
          </div>
        </div>
        {assignedCount !== undefined && totalCount !== undefined && (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: config.textColor, fontFamily: 'var(--font-display)' }}>
              {assignedCount}/{totalCount}
            </div>
            <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Assigned
            </div>
          </div>
        )}
      </div>
      {unassignedVessels && unassignedVessels.length > 0 && (
        <div style={{
          marginTop: 10, padding: '8px 12px',
          background: 'rgba(239,68,68,0.06)', borderRadius: 6,
          fontSize: 12, color: '#ef4444',
        }}>
          ⚠️ Unassigned: {unassignedVessels.join(', ')}
        </div>
      )}
    </div>
  );
}
