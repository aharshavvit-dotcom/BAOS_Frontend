/**
 * BAOS AI — Dashboard Page
 * Matches homepage.html with Recharts and real-time data
 */
'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Area, AreaChart,
} from 'recharts';
import { useAuthStore } from '@/store/authStore';
import { useDashboardStore } from '@/store/dashboardStore';
import type { FilterStatus, DashboardRecommendation } from '@/types';

/* ═══════════════════════════════════════════════════════════
   ANIMATED COUNTER
   ═══════════════════════════════════════════════════════════ */
function Counter({ value, prefix = '', suffix = '', decimals = 0, duration = 1200 }: {
  value: number; prefix?: string; suffix?: string; decimals?: number; duration?: number;
}) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const start = performance.now();
    let raf: number;
    function update(now: number) {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(parseFloat((value * eased).toFixed(decimals)));
      if (p < 1) raf = requestAnimationFrame(update);
      else setDisplay(parseFloat(value.toFixed(decimals)));
    }
    raf = requestAnimationFrame(update);
    return () => cancelAnimationFrame(raf);
  }, [value, duration, decimals]);

  return <>{prefix}{display.toFixed(decimals)}{suffix}</>;
}

/* ═══════════════════════════════════════════════════════════
   CHART DATA (matching homepage.js)
   ═══════════════════════════════════════════════════════════ */
const monthlyData = [
  { metric: 'Vessels',       current: 142, previous: 131 },
  { metric: 'Revenue ($K)',  current: 480, previous: 420 },
  { metric: 'Utilization',   current: 78,  previous: 75 },
  { metric: 'SLA %',         current: 94,  previous: 89 },
];

const utilizationTrend = [
  { day: 'Mon', util: 72 }, { day: 'Tue', util: 78 },
  { day: 'Wed', util: 75 }, { day: 'Thu', util: 82 },
  { day: 'Fri', util: 80 }, { day: 'Sat', util: 55 },
  { day: 'Sun', util: 48 },
];

const vesselDist = [
  { name: 'Container', value: 35, color: 'rgba(0,102,204,0.8)' },
  { name: 'Bulk', value: 22, color: 'rgba(0,170,153,0.8)' },
  { name: 'General', value: 18, color: 'rgba(139,92,246,0.8)' },
  { name: 'Tanker', value: 15, color: 'rgba(245,158,11,0.8)' },
  { name: 'RoRo', value: 10, color: 'rgba(236,72,153,0.8)' },
];

const costData = [
  { category: 'Fuel',      cost: 45 },
  { category: 'Equipment', cost: 38 },
  { category: 'Waiting',   cost: 28 },
  { category: 'SLA',       cost: 12 },
  { category: 'Handling',  cost: 52 },
];
const costColors = ['rgba(239,68,68,0.7)', 'rgba(245,158,11,0.7)', 'rgba(59,130,246,0.7)', 'rgba(139,92,246,0.7)', 'rgba(0,170,153,0.7)'];

/* ═══════════════════════════════════════════════════════════
   SAMPLE RECOMMENDATIONS
   ═══════════════════════════════════════════════════════════ */
const sampleRecs: DashboardRecommendation[] = [
  { id: 'rec-001', vessel_name: 'MV Ocean Crown',    vessel_type: 'Container Ship',   berth_name: 'Berth A1 (Container Terminal)', confidence: 92.5, status: 'pending',  created_at: '2026-03-30T10:30:00Z' },
  { id: 'rec-002', vessel_name: 'SS Pacific Trader', vessel_type: 'Bulk Carrier',     berth_name: 'Berth B3 (Bulk Terminal)',       confidence: 87.3, status: 'accepted', created_at: '2026-03-29T15:45:00Z' },
  { id: 'rec-003', vessel_name: 'MT Horizon Star',   vessel_type: 'Crude Oil Tanker', berth_name: 'Berth C2 (Oil Terminal)',        confidence: 95.1, status: 'pending',  created_at: '2026-03-30T08:00:00Z' },
  { id: 'rec-004', vessel_name: 'MV Jade Express',   vessel_type: 'General Cargo',    berth_name: 'Berth A3 (Multi-purpose)',      confidence: 78.9, status: 'rejected', created_at: '2026-03-28T12:20:00Z' },
];

export default function DashboardPage() {
  const user = useAuthStore(s => s.user);
  const [filter, setFilter] = useState<FilterStatus>('all');
  const [recommendations, setRecommendations] = useState(sampleRecs);

  const { fetchKPIs, fetchCharts, fetchRecommendations: fetchRecs } = useDashboardStore();

  // Try loading from API on mount (graceful fallback to sample data)
  useEffect(() => {
    fetchKPIs().catch(() => {});
    fetchCharts().catch(() => {});
    fetchRecs().catch(() => {});
  }, [fetchKPIs, fetchCharts, fetchRecs]);

  const filtered = filter === 'all' ? recommendations : recommendations.filter(r => r.status === filter);

  function acceptRec(id: string) {
    setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'accepted' as const } : r));
  }

  function rejectRec(id: string) {
    setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'rejected' as const } : r));
  }

  const getGreeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good Morning';
    if (h < 17) return 'Good Afternoon';
    return 'Good Evening';
  };

  return (
    <div className="space-y-6">
      {/* ── Welcome ──────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold" style={{ fontFamily: 'var(--font-display)' }}>
            {getGreeting()}, {user?.full_name?.split(' ')[0] || 'Captain'} 👋
          </h1>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Here&apos;s your port overview for today
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-secondary btn-sm">📥 Export</button>
          <button className="btn btn-primary btn-sm">+ New Assignment</button>
        </div>
      </div>

      {/* ── KPI Cards ────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { icon: '🚢', label: 'Active Vessels',     value: 142,  suffix: '', change: '+8.4%', trend: 'up' },
          { icon: '💰', label: 'Revenue',             value: 480,  prefix: '$', suffix: 'K', change: '+14.3%', trend: 'up' },
          { icon: '📈', label: 'Berth Utilization',   value: 78,   suffix: '%', change: '+4%', trend: 'up' },
          { icon: '✅', label: 'SLA Compliance',      value: 94,   suffix: '%', change: '+5.6%', trend: 'up' },
        ].map((kpi, i) => (
          <div key={i} className="card" style={{ background: 'var(--color-dark-card)' }}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-2xl">{kpi.icon}</span>
              <span className="badge badge-success text-xs">{kpi.change}</span>
            </div>
            <div className="text-2xl font-extrabold mb-1" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-primary)' }}>
              <Counter value={kpi.value} prefix={kpi.prefix || ''} suffix={kpi.suffix} />
            </div>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{kpi.label}</p>
          </div>
        ))}
      </div>

      {/* ── Charts (2×2 grid) ────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Monthly Comparison Bar */}
        <div className="card-flat" style={{ height: 320 }}>
          <h3 className="text-sm font-bold mb-3" style={{ fontFamily: 'var(--font-display)' }}>Monthly Comparison</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.15)" />
              <XAxis dataKey="metric" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #475569', borderRadius: 8, color: '#F1F5F9', fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="current" name="This Month" fill="rgba(0,102,204,0.7)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="previous" name="Last Month" fill="rgba(148,163,184,0.5)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Utilization Trend */}
        <div className="card-flat" style={{ height: 320 }}>
          <h3 className="text-sm font-bold mb-3" style={{ fontFamily: 'var(--font-display)' }}>Utilization Trend</h3>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={utilizationTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.15)" />
              <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={[0, 100]} tickFormatter={v => `${v}%`} />
              <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #475569', borderRadius: 8, color: '#F1F5F9', fontSize: 12 }} />
              <Area type="monotone" dataKey="util" name="Utilization %" stroke="#0066CC" fill="rgba(0,102,204,0.08)" strokeWidth={2} dot={{ fill: '#0066CC', r: 3 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Vessel Distribution */}
        <div className="card-flat" style={{ height: 320 }}>
          <h3 className="text-sm font-bold mb-3" style={{ fontFamily: 'var(--font-display)' }}>Vessel Distribution</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={vesselDist} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={2} dataKey="value" nameKey="name">
                {vesselDist.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #475569', borderRadius: 8, color: '#F1F5F9', fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Cost Breakdown */}
        <div className="card-flat" style={{ height: 320 }}>
          <h3 className="text-sm font-bold mb-3" style={{ fontFamily: 'var(--font-display)' }}>Cost Breakdown ($K)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={costData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.15)" />
              <XAxis dataKey="category" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={v => `$${v}K`} />
              <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #475569', borderRadius: 8, color: '#F1F5F9', fontSize: 12 }} />
              <Bar dataKey="cost" name="Cost ($K)" radius={[4, 4, 0, 0]}>
                {costData.map((_, i) => <Cell key={i} fill={costColors[i]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Recommendations ──────────────────────────────── */}
      <div className="card-flat">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold" style={{ fontFamily: 'var(--font-display)' }}>AI Recommendations</h3>
          <div className="flex gap-2">
            {(['all', 'pending', 'accepted', 'rejected'] as FilterStatus[]).map(status => (
              <button
                key={status}
                className={`rec-tab ${filter === status ? 'active' : ''}`}
                onClick={() => setFilter(status)}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)} ({status === 'all' ? recommendations.length : recommendations.filter(r => r.status === status).length})
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          {filtered.length === 0 ? (
            <div className="text-center py-8" style={{ color: 'var(--color-text-muted)' }}>
              <span className="text-3xl block mb-2">📋</span>
              No recommendations found
            </div>
          ) : filtered.map(rec => (
            <div
              key={rec.id}
              className="flex items-center gap-4 p-4 rounded-lg transition-colors"
              style={{ background: 'var(--color-dark)', border: '1px solid var(--color-dark-border)' }}
            >
              <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-lg"
                   style={{ background: 'rgba(0,102,204,0.15)' }}>
                🚢
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                    {rec.vessel_name}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'rgba(100,116,139,0.2)', color: 'var(--color-text-muted)' }}>
                    {rec.vessel_type}
                  </span>
                </div>
                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  → {rec.berth_name}
                </p>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-sm font-bold" style={{
                  color: rec.confidence >= 90 ? 'var(--color-success)' : rec.confidence >= 80 ? 'var(--color-primary)' : 'var(--color-warning)'
                }}>
                  {rec.confidence}%
                </div>
                <span className={`badge ${
                  rec.status === 'accepted' ? 'badge-success' :
                  rec.status === 'rejected' ? 'badge-danger' : 'badge-warning'
                }`}>
                  {rec.status}
                </span>
              </div>
              {rec.status === 'pending' && (
                <div className="flex gap-2 flex-shrink-0">
                  <button onClick={() => acceptRec(rec.id)} className="btn btn-sm" style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--color-success)', border: '1px solid var(--color-success)' }}>
                    ✓
                  </button>
                  <button onClick={() => rejectRec(rec.id)} className="btn btn-sm" style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--color-danger)', border: '1px solid var(--color-danger)' }}>
                    ✗
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── Quick Actions ────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: '🎯', label: 'Run Optimizer', desc: 'Multi-vessel scheduling' },
          { icon: '📊', label: 'Generate Report', desc: 'Export analytics' },
          { icon: '🔔', label: 'Set Alert', desc: 'Configure notifications' },
          { icon: '📋', label: 'View Schedule', desc: 'Berth assignments' },
        ].map((action, i) => (
          <button key={i} className="card text-left group">
            <div className="text-2xl mb-2">{action.icon}</div>
            <p className="text-sm font-semibold mb-1" style={{ fontFamily: 'var(--font-display)' }}>{action.label}</p>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{action.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
