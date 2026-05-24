/**
 * Alerts Page — Port Operations Alert Management
 * Features: Real-time alerts for SLA breaches, berth congestion,
 * maintenance schedules, weather warnings, and vessel delays
 */
'use client';

import { useState, useMemo } from 'react';

/* --- Alert Types --- */
interface Alert {
  id: string;
  type: 'critical' | 'warning' | 'info' | 'success';
  category: 'sla' | 'congestion' | 'weather' | 'maintenance' | 'vessel' | 'safety' | 'system';
  title: string;
  message: string;
  berth?: string;
  vessel?: string;
  timestamp: string;
  acknowledged: boolean;
  actionRequired: boolean;
}

const CATEGORY_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
  sla: { icon: '📋', label: 'SLA Breach', color: '#ef4444' },
  congestion: { icon: '🚧', label: 'Congestion', color: '#f59e0b' },
  weather: { icon: '🌊', label: 'Weather', color: '#0ea5e9' },
  maintenance: { icon: '🔧', label: 'Maintenance', color: '#8b5cf6' },
  vessel: { icon: '🚢', label: 'Vessel', color: '#ec4899' },
  safety: { icon: '⚠️', label: 'Safety', color: '#ef4444' },
  system: { icon: '💻', label: 'System', color: '#6366f1' },
};

const TYPE_CONFIG: Record<string, { icon: string; bg: string; border: string; text: string }> = {
  critical: { icon: '🔴', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.3)', text: '#ef4444' },
  warning: { icon: '🟡', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.3)', text: '#f59e0b' },
  info: { icon: '🔵', bg: 'rgba(14,165,233,0.08)', border: 'rgba(14,165,233,0.3)', text: '#0ea5e9' },
  success: { icon: '🟢', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.3)', text: '#10b981' },
};

const MOCK_ALERTS: Alert[] = [
  {
    id: 'A001', type: 'critical', category: 'sla',
    title: 'SLA Breach — MV Horizon Star exceeding max wait time',
    message: 'Vessel MV Horizon Star at Berth JD4 has exceeded the SLA maximum wait time of 24 hours. Current wait: 28.4 hours. Contractual penalty of $1,000/hr now accruing. Immediate action required to expedite cargo operations or negotiate SLA waiver.',
    berth: 'Berth JD4', vessel: 'MV Horizon Star', timestamp: '2 min ago', acknowledged: false, actionRequired: true,
  },
  {
    id: 'A002', type: 'critical', category: 'safety',
    title: 'Oil Spill Containment Alert — BD1 Terminal',
    message: 'Minor oil sheen detected near Berth BD1 during MT Jade Voyager cargo transfer operations. Containment booms deployed. Environmental response team on-site. Operations temporarily paused pending safety clearance.',
    berth: 'Berth BD1', vessel: 'MT Jade Voyager', timestamp: '15 min ago', acknowledged: false, actionRequired: true,
  },
  {
    id: 'A003', type: 'warning', category: 'congestion',
    title: 'Berth Congestion — CCTL Container Terminal at 75% capacity',
    message: 'CTB1 and CTB2 are occupied, CTB3 and CTB4 are free but a queue of 3 container vessels expected within next 12 hours. Consider diverting overflow to CITPL terminal (SCB3 available). Average wait time trending up to 5.2 hours.',
    berth: 'CCTL Terminal', timestamp: '32 min ago', acknowledged: false, actionRequired: true,
  },
  {
    id: 'A004', type: 'warning', category: 'weather',
    title: 'High Wind Advisory — Sustained winds 25-30 knots forecast',
    message: 'National Weather Service forecasts sustained winds of 25-30 knots for the next 12 hours (16:00–04:00). Berths with LOA >250m vessels should prepare for potential mooring adjustments. Pilot operations may be suspended if gusts exceed 35 knots.',
    timestamp: '45 min ago', acknowledged: false, actionRequired: false,
  },
  {
    id: 'A005', type: 'warning', category: 'vessel',
    title: 'Vessel Delay — MV Nordic Express ETA revised +6 hours',
    message: 'MV Nordic Express (Container, 289m) has revised ETA from 08:00 to 14:00 due to engine speed reduction. This may cascade to berth SCB2 scheduling. Recommend reviewing assignment queue for SCB2 and notifying downstream terminals.',
    vessel: 'MV Nordic Express', berth: 'Berth SCB2', timestamp: '1h ago', acknowledged: true, actionRequired: false,
  },
  {
    id: 'A006', type: 'info', category: 'maintenance',
    title: 'Scheduled Maintenance — Berth JD6 crane servicing',
    message: 'Berth JD6 gantry crane annual servicing in progress. Expected completion: 48 hours. Berth is non-operational. Bulk dry vessels previously assigned to JD6 should be redirected to JD5 or Ambedkar Terminal berths.',
    berth: 'Berth JD6', timestamp: '1d ago', acknowledged: true, actionRequired: false,
  },
  {
    id: 'A007', type: 'info', category: 'vessel',
    title: 'New Arrival — MT Chem Pioneer approaching anchorage',
    message: 'MT Chem Pioneer (Chemical Tanker, 175m LOA, 12.4m draft) approaching Chennai anchorage. ETA to pilot boarding: 2 hours. Pre-assigned to Berth BD2 (Oil Terminal). Hazmat clearance pending customs documentation.',
    vessel: 'MT Chem Pioneer', berth: 'Berth BD2', timestamp: '2h ago', acknowledged: true, actionRequired: false,
  },
  {
    id: 'A008', type: 'success', category: 'system',
    title: 'Optimizer Run Completed — All vessels assigned',
    message: 'CP-SAT optimizer completed successfully in 1.24 seconds. All 12 vessels assigned to berths with OPTIMAL status. Average confidence score: 87%. No SLA violations predicted in the current schedule.',
    timestamp: '3h ago', acknowledged: true, actionRequired: false,
  },
  {
    id: 'A009', type: 'success', category: 'sla',
    title: 'SLA Compliance — Monthly target achieved',
    message: 'Port-wide SLA compliance for April 2026 has reached 96.2%, exceeding the 95% target. Top performing terminal: CCTL (99.1% compliance). Lowest: Jawahar Terminal (91.8%) — driven by bulk dry vessel delays during week 2.',
    timestamp: '6h ago', acknowledged: true, actionRequired: false,
  },
  {
    id: 'A010', type: 'warning', category: 'congestion',
    title: 'Anchorage Queue — 4 vessels awaiting berth assignment',
    message: '4 vessels currently at anchorage: 2 Bulk Dry, 1 Container, 1 Chemical Tanker. Average waiting time: 6.8 hours. Recommend prioritizing Bulk Dry vessels for Ambedkar Terminal (3 berths free).',
    timestamp: '4h ago', acknowledged: false, actionRequired: true,
  },
];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>(MOCK_ALERTS);
  const [filter, setFilter] = useState<'all' | 'critical' | 'warning' | 'info' | 'success'>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [showAcknowledged, setShowAcknowledged] = useState(true);

  const filtered = useMemo(() => {
    return alerts.filter(a => {
      if (filter !== 'all' && a.type !== filter) return false;
      if (categoryFilter !== 'all' && a.category !== categoryFilter) return false;
      if (!showAcknowledged && a.acknowledged) return false;
      return true;
    });
  }, [alerts, filter, categoryFilter, showAcknowledged]);

  const counts = useMemo(() => ({
    all: alerts.length,
    critical: alerts.filter(a => a.type === 'critical').length,
    warning: alerts.filter(a => a.type === 'warning').length,
    info: alerts.filter(a => a.type === 'info').length,
    success: alerts.filter(a => a.type === 'success').length,
    unacknowledged: alerts.filter(a => !a.acknowledged).length,
    actionRequired: alerts.filter(a => a.actionRequired && !a.acknowledged).length,
  }), [alerts]);

  function acknowledgeAlert(id: string) {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a));
  }

  function acknowledgeAll() {
    setAlerts(prev => prev.map(a => ({ ...a, acknowledged: true })));
  }

  function dismissAlert(id: string) {
    setAlerts(prev => prev.filter(a => a.id !== id));
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-2xl">🔔</span>
            <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 22, color: 'var(--color-text-primary)' }}>
              Port Alerts
            </h2>
            {counts.unacknowledged > 0 && (
              <span style={{
                padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 700,
                background: 'rgba(239,68,68,0.12)', color: '#ef4444',
              }}>
                {counts.unacknowledged} new
              </span>
            )}
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13, marginTop: 4 }}>
            Real-time operational alerts, SLA monitoring, and weather advisories
          </p>
        </div>
        <div className="flex gap-2">
          {counts.unacknowledged > 0 && (
            <button className="btn btn-secondary" onClick={acknowledgeAll} style={{ fontSize: 12 }}>
              ✅ Acknowledge All ({counts.unacknowledged})
            </button>
          )}
        </div>
      </div>

      {/* --- Alert Summary Cards --- */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        {[
          { icon: '🔴', value: counts.critical, label: 'Critical', color: '#ef4444' },
          { icon: '🟡', value: counts.warning, label: 'Warnings', color: '#f59e0b' },
          { icon: '🔵', value: counts.info, label: 'Info', color: '#0ea5e9' },
          { icon: '🟢', value: counts.success, label: 'Resolved', color: '#10b981' },
          { icon: '⚡', value: counts.actionRequired, label: 'Action Needed', color: counts.actionRequired > 0 ? '#ef4444' : '#10b981' },
        ].map((kpi, i) => (
          <div key={i} className="card-flat text-center" style={{ padding: 14, cursor: 'pointer' }}
            onClick={() => setFilter(i < 4 ? (['critical', 'warning', 'info', 'success'] as const)[i] : 'all')}>
            <div style={{ fontSize: 18 }}>{kpi.icon}</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: kpi.color, fontFamily: 'var(--font-display)' }}>{kpi.value}</div>
            <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{kpi.label}</div>
          </div>
        ))}
      </div>

      {/* --- Filters --- */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        {/* Type filter */}
        <div className="flex gap-1">
          {(['all', 'critical', 'warning', 'info', 'success'] as const).map(t => (
            <button key={t} onClick={() => setFilter(t)}
              style={{
                padding: '5px 14px', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                background: filter === t ? (t === 'all' ? 'var(--color-primary)' : TYPE_CONFIG[t]?.bg || 'var(--color-primary)') : 'transparent',
                color: filter === t ? (t === 'all' ? 'white' : TYPE_CONFIG[t]?.text || 'white') : 'var(--color-text-muted)',
                border: `1px solid ${filter === t ? (t === 'all' ? 'var(--color-primary)' : TYPE_CONFIG[t]?.border || 'var(--color-primary)') : 'var(--color-border)'}`,
                textTransform: 'capitalize',
              }}>
              {t === 'all' ? `All (${counts.all})` : `${TYPE_CONFIG[t]?.icon} ${t} (${counts[t]})`}
            </button>
          ))}
        </div>

        {/* Category filter */}
        <select className="form-input" value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}
          style={{ maxWidth: 200, fontSize: 12, padding: '5px 10px' }}>
          <option value="all">All Categories</option>
          {Object.entries(CATEGORY_CONFIG).map(([k, v]) => (
            <option key={k} value={k}>{v.icon} {v.label}</option>
          ))}
        </select>

        <label className="flex items-center gap-2" style={{ fontSize: 12, color: 'var(--color-text-muted)', marginLeft: 'auto' }}>
          <input type="checkbox" checked={showAcknowledged} onChange={e => setShowAcknowledged(e.target.checked)} />
          Show acknowledged
        </label>
      </div>

      {/* --- Alert List --- */}
      <div className="space-y-3 mb-8">
        {filtered.length === 0 && (
          <div className="card text-center" style={{ padding: 40 }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🎉</div>
            <p style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>No alerts matching your filters.</p>
          </div>
        )}

        {filtered.map(alert => {
          const tc = TYPE_CONFIG[alert.type];
          const cc = CATEGORY_CONFIG[alert.category];
          return (
            <div key={alert.id} className="card animate-fade-in-up" style={{
              padding: 0, overflow: 'hidden',
              borderLeft: `4px solid ${tc.text}`,
              opacity: alert.acknowledged ? 0.7 : 1,
              background: alert.acknowledged ? 'transparent' : tc.bg,
            }}>
              <div style={{ padding: '16px 20px' }}>
                {/* Header */}
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span style={{ fontSize: 14 }}>{tc.icon}</span>
                      <span style={{
                        padding: '1px 8px', borderRadius: 20, fontSize: 10, fontWeight: 700,
                        background: `${cc.color}15`, color: cc.color, textTransform: 'uppercase',
                      }}>
                        {cc.icon} {cc.label}
                      </span>
                      {alert.actionRequired && !alert.acknowledged && (
                        <span style={{
                          padding: '1px 8px', borderRadius: 20, fontSize: 10, fontWeight: 700,
                          background: 'rgba(239,68,68,0.1)', color: '#ef4444', animation: 'pulse 2s infinite',
                        }}>
                          ⚡ ACTION REQUIRED
                        </span>
                      )}
                      {alert.vessel && (
                        <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>🚢 {alert.vessel}</span>
                      )}
                      {alert.berth && (
                        <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>🏗️ {alert.berth}</span>
                      )}
                    </div>
                    <h4 style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)', lineHeight: 1.4 }}>
                      {alert.title}
                    </h4>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span style={{ fontSize: 11, color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>{alert.timestamp}</span>
                  </div>
                </div>

                {/* Body */}
                <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: 12 }}>
                  {alert.message}
                </p>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {!alert.acknowledged && (
                    <button onClick={() => acknowledgeAlert(alert.id)}
                      style={{
                        padding: '4px 14px', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                        background: 'var(--color-primary)', color: 'white', border: 'none',
                      }}>
                      ✅ Acknowledge
                    </button>
                  )}
                  <button onClick={() => dismissAlert(alert.id)}
                    style={{
                      padding: '4px 14px', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                      background: 'transparent', color: 'var(--color-text-muted)',
                      border: '1px solid var(--color-border)',
                    }}>
                    ✕ Dismiss
                  </button>
                  {alert.acknowledged && (
                    <span style={{ fontSize: 11, color: '#10b981', fontWeight: 600, marginLeft: 'auto' }}>
                      ✓ Acknowledged
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

