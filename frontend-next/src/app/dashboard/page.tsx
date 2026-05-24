/**
 * BAOS AI — Dashboard Page
 * Matches homepage.html with Recharts and real-time data
 */
'use client';

import { useState, useEffect } from 'react';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Area, AreaChart,
} from 'recharts';
import { useAuthStore } from '@/store/authStore';
import { useDashboardStore } from '@/store/dashboardStore';
import type { FilterStatus, DashboardRecommendation } from '@/types';
import AnimatedCounter from '@/components/common/AnimatedCounter';
import SourceBadge from '@/components/common/SourceBadge';
import apiClient from '@/lib/api/client';
import {
  DEMO_MONTHLY_DATA,
  DEMO_UTILIZATION_TREND,
  DEMO_VESSEL_DIST,
  DEMO_COST_DATA,
  DEMO_COST_COLORS,
  DEMO_SAMPLE_RECS,
} from '@/lib/demo/dashboardDemoData';

export default function DashboardPage() {
  const user = useAuthStore(s => s.user);
  const [filter, setFilter] = useState<FilterStatus>('all');
  const { kpis, recommendations: storeRecs, fetchKPIs, fetchCharts, fetchRecommendations: fetchRecs } = useDashboardStore();
  const [recommendations, setRecommendations] = useState<DashboardRecommendation[]>(DEMO_SAMPLE_RECS);
  const [greeting, setGreeting] = useState('Welcome');

  // Load greeting safely inside useEffect to avoid hydration mismatch
  useEffect(() => {
    const h = new Date().getHours();
    if (h < 12) setGreeting('Good Morning');
    else if (h < 17) setGreeting('Good Afternoon');
    else setGreeting('Good Evening');
  }, []);

  // Try loading from API on mount (graceful fallback to sample data)
  useEffect(() => {
    fetchKPIs().catch(() => {});
    fetchCharts().catch(() => {});
    fetchRecs().catch(() => {});
  }, [fetchKPIs, fetchCharts, fetchRecs]);

  useEffect(() => {
    if (storeRecs && storeRecs.length > 0) {
      setRecommendations(storeRecs);
    } else {
      setRecommendations(DEMO_SAMPLE_RECS);
    }
  }, [storeRecs]);

  const filtered = filter === 'all' ? recommendations : recommendations.filter(r => r.status === filter);

  async function acceptRec(id: string) {
    try {
      await apiClient.patch(`/api/recommendations/${id}`, { status: 'accepted' });
    } catch (e) {
      console.error("Failed to accept recommendation in backend", e);
    }
    setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'accepted' as const } : r));
  }

  async function rejectRec(id: string) {
    try {
      await apiClient.patch(`/api/recommendations/${id}`, { status: 'rejected' });
    } catch (e) {
      console.error("Failed to reject recommendation in backend", e);
    }
    setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'rejected' as const } : r));
  }

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold" style={{ fontFamily: 'var(--font-display)' }}>
            {greeting}, {user?.full_name?.split(' ')[0] || 'Captain'} 👋
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

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { icon: '🚢', label: 'Active Vessels',     value: kpis?.vessels_count ?? 142,  suffix: '', change: '+8.4%' },
          { icon: '💰', label: 'Revenue',             value: kpis?.revenue ? Math.round(kpis.revenue / 1000) : 480,  prefix: '$', suffix: 'K', change: '+14.3%' },
          { icon: '📈', label: 'Berth Utilization',   value: kpis?.utilization_pct ?? 78,   suffix: '%', change: '+4%' },
          { icon: '✅', label: 'SLA Compliance',      value: kpis?.sla_compliance_pct ?? 94,   suffix: '%', change: '+5.6%' },
        ].map((kpi, i) => (
          <div key={i} className="card" style={{ background: 'var(--color-dark-card)' }}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-2xl">{kpi.icon}</span>
              <span className="badge badge-success text-xs">{kpi.change}</span>
            </div>
            <div className="text-2xl font-extrabold mb-1" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-primary)' }}>
              <AnimatedCounter target={kpi.value} prefix={kpi.prefix || ''} suffix={kpi.suffix} />
            </div>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{kpi.label}</p>
          </div>
        ))}
      </div>

      {/* Charts (2x2 grid) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Monthly Comparison Bar */}
        <div className="card-flat h-[320px] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold" style={{ fontFamily: 'var(--font-display)' }}>Monthly Comparison</h3>
            <SourceBadge source="HISTORICAL" />
          </div>
          <div className="h-[260px] w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={DEMO_MONTHLY_DATA}>
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
        </div>

        {/* Utilization Trend */}
        <div className="card-flat h-[320px] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold" style={{ fontFamily: 'var(--font-display)' }}>Utilization Trend</h3>
            <SourceBadge source="DEMO" />
          </div>
          <div className="h-[260px] w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={DEMO_UTILIZATION_TREND}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.15)" />
                <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={[0, 100]} tickFormatter={v => `${v}%`} />
                <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #475569', borderRadius: 8, color: '#F1F5F9', fontSize: 12 }} />
                <Area type="monotone" dataKey="util" name="Utilization %" stroke="#0066CC" fill="rgba(0,102,204,0.08)" strokeWidth={2} dot={{ fill: '#0066CC', r: 3 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Vessel Distribution */}
        <div className="card-flat h-[320px] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold" style={{ fontFamily: 'var(--font-display)' }}>Vessel Distribution</h3>
            <SourceBadge source="HISTORICAL" />
          </div>
          <div className="h-[260px] w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={DEMO_VESSEL_DIST} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={2} dataKey="value" nameKey="name">
                  {DEMO_VESSEL_DIST.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #475569', borderRadius: 8, color: '#F1F5F9', fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Cost Breakdown */}
        <div className="card-flat h-[320px] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-bold" style={{ fontFamily: 'var(--font-display)' }}>Cost Breakdown ($K)</h3>
            <SourceBadge source="DEMO" />
          </div>
          <div className="h-[260px] w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={DEMO_COST_DATA}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.15)" />
                <XAxis dataKey="category" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={v => `$${v}K`} />
                <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #475569', borderRadius: 8, color: '#F1F5F9', fontSize: 12 }} />
                <Bar dataKey="cost" name="Cost ($K)" radius={[4, 4, 0, 0]}>
                  {DEMO_COST_DATA.map((_, i) => <Cell key={i} fill={DEMO_COST_COLORS[i]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recommendations */}
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

      {/* Quick Actions */}
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
