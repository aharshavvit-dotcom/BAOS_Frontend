/**
 * Analytics Page â€” Port Operations Analytics Dashboard
 * Features: Berth occupancy status, vessel throughput trends,
 * terminal performance, draft utilization, cargo distribution
 */
'use client';

import { useState, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, AreaChart, Area, LineChart, Line,
} from 'recharts';
import SourceBadge from '@/components/ui/SourceBadge';
import {
  TERMINALS,
  BERTH_STATUS,
  WEEKLY_THROUGHPUT,
  MONTHLY_UTILIZATION,
  ANALYTICS_COLORS as COLORS,
} from '@/lib/demo/analyticsDemoData';
import {
  TrendingUp, Ship, Wrench, CheckCircle2, BarChart3,
  Anchor, Building, Clock, Package
} from 'lucide-react';

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<'today' | 'week' | 'month'>('today');

  const stats = useMemo(() => {
    const occupied = BERTH_STATUS.filter(b => b.status === 'occupied').length;
    const free = BERTH_STATUS.filter(b => b.status === 'free').length;
    const maintenance = BERTH_STATUS.filter(b => b.status === 'maintenance').length;
    const total = BERTH_STATUS.length;
    return { occupied, free, maintenance, total, utilizationPct: Math.round((occupied / total) * 100) };
  }, []);

  const vesselTypeDistrib = useMemo(() => {
    const counts: Record<string, number> = {};
    BERTH_STATUS.filter(b => b.vesselType).forEach(b => {
      counts[b.vesselType] = (counts[b.vesselType] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, []);

  const terminalUtilization = useMemo(() => {
    return TERMINALS.map(t => {
      const terminalBerths = BERTH_STATUS.filter(b => b.terminal === t.name.split(' ')[0]);
      const occupied = terminalBerths.filter(b => b.status === 'occupied').length;
      return {
        name: t.name.replace(' Terminal', ''),
        total: terminalBerths.length || t.berths.length,
        occupied,
        utilization: terminalBerths.length ? Math.round((occupied / terminalBerths.length) * 100) : 0,
      };
    });
  }, []);

  const departingSoon = BERTH_STATUS
    .filter(b => b.status === 'occupied' && b.eta_depart)
    .sort((a, b) => parseInt(a.eta_depart) - parseInt(b.eta_depart))
    .slice(0, 5);

  function statusColor(s: string) {
    return s === 'occupied' ? '#0ea5e9' : s === 'free' ? '#10b981' : '#f59e0b';
  }
  function statusBg(s: string) {
    return s === 'occupied' ? 'rgba(14,165,233,0.1)' : s === 'free' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)';
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <BarChart3 className="text-emerald-500 animate-pulse" size={24} />
            <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 22, color: 'var(--color-text-primary)' }}>
              Port Analytics
            </h2>
            <span className="badge badge-success">Live</span>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13, marginTop: 4 }}>
            Real-time operational intelligence for Chennai Port — 23 berths across 5 terminals
          </p>
        </div>
        <div className="flex gap-2">
          {(['today', 'week', 'month'] as const).map(t => (
            <button key={t} onClick={() => setTimeRange(t)}
              style={{
                padding: '6px 16px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                background: timeRange === t ? 'var(--color-primary)' : 'transparent',
                color: timeRange === t ? 'white' : 'var(--color-text-secondary)',
                border: `1px solid ${timeRange === t ? 'var(--color-primary)' : 'var(--color-border)'}`,
                textTransform: 'capitalize',
              }}>{t}</button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        {[
          { icon: <CheckCircle2 size={22} className="text-emerald-500" />, value: stats.free.toString(), label: 'Berths Free', color: '#10b981' },
          { icon: <Ship size={22} className="text-sky-500" />, value: stats.occupied.toString(), label: 'Berths Occupied', color: '#0ea5e9' },
          { icon: <Wrench size={22} className="text-amber-500" />, value: stats.maintenance.toString(), label: 'Maintenance', color: '#f59e0b' },
          { icon: <TrendingUp size={22} className="text-purple-500" />, value: `${stats.utilizationPct}%`, label: 'Utilization Rate', color: stats.utilizationPct > 75 ? '#ef4444' : '#10b981' },
          { icon: <Anchor size={22} className="text-blue-500" />, value: stats.occupied.toString(), label: 'Vessels in Port', color: '#8b5cf6' },
        ].map((kpi, i) => (
          <div key={i} className="card-flat text-center" style={{ padding: 16 }}>
            <div className="flex justify-center mb-2">{kpi.icon}</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: kpi.color, fontFamily: 'var(--font-display)' }}>{kpi.value}</div>
            <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{kpi.label}</div>
          </div>
        ))}
      </div>

      {/* Berth Status Grid */}
      <div className="flex items-center gap-3 mb-4">
        <Building size={20} className="text-blue-500" />
        <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--color-text-primary)' }}>
          Live Berth Status
        </h3>
        <div className="flex gap-3 ml-auto text-xs" style={{ color: 'var(--color-text-muted)' }}>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" /> Free ({stats.free})</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-sky-500" /> Occupied ({stats.occupied})</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-500" /> Maintenance ({stats.maintenance})</span>
        </div>
      </div>

      <div className="card mb-8" style={{ padding: 20, overflowX: 'auto' }}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {BERTH_STATUS.map(b => (
            <div key={b.berth} className="card-flat" style={{
              padding: '12px 16px', borderLeft: `3px solid ${statusColor(b.status)}`,
              background: statusBg(b.status),
            }}>
              <div className="flex items-center justify-between mb-1">
                <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--color-text-primary)' }}>{b.berth}</span>
                <span style={{
                  padding: '2px 8px', borderRadius: 20, fontSize: 10, fontWeight: 700,
                  background: statusColor(b.status), color: 'white', textTransform: 'uppercase',
                }}>{b.status}</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                {b.terminal} Terminal
              </div>
              {b.status === 'occupied' && (
                <>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)', marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Ship size={14} className="text-sky-400" /> {b.vessel} <span style={{ fontWeight: 400, fontSize: 11 }}>({b.vesselType})</span>
                  </div>
                  <div style={{ marginTop: 6 }}>
                    <div className="flex items-center justify-between" style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 3 }}>
                      <span>Since: {b.since}</span>
                      <span>Departs in: {b.eta_depart}</span>
                    </div>
                    <div style={{ height: 6, borderRadius: 3, background: 'rgba(0,0,0,0.08)', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', borderRadius: 3, transition: 'width 0.5s',
                        width: `${b.progress}%`,
                        background: b.progress > 80 ? '#10b981' : b.progress > 50 ? '#0ea5e9' : '#f59e0b',
                      }} />
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 2, textAlign: 'right' }}>{b.progress}% complete</div>
                  </div>
                </>
              )}
              {b.status === 'free' && (
                <div style={{ fontSize: 11, color: '#10b981', marginTop: 6, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <CheckCircle2 size={12} /> Available — free since {b.since}
                </div>
              )}
              {b.status === 'maintenance' && (
                <div style={{ fontSize: 11, color: '#f59e0b', marginTop: 6, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Wrench size={12} /> Scheduled maintenance — since {b.since}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Terminal Utilization */}
        <div className="card flex flex-col justify-between" style={{ padding: 20 }}>
          <div className="flex items-center justify-between mb-4">
            <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Building size={16} className="text-blue-500" /> Terminal Utilization
            </h4>
            <SourceBadge source="DEMO" />
          </div>
          <div className="h-[260px] w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={terminalUtilization} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis type="number" domain={[0, 100]} stroke="#94a3b8" fontSize={12} />
                <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={11} width={80} />
                <Tooltip contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 8 }}
                  formatter={(v) => [`${v}%`, 'Utilization']} />
                <Bar dataKey="utilization" radius={[0, 6, 6, 0]}>
                  {terminalUtilization.map((_, i) => (
                    <Cell key={i} fill={COLORS[i]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Vessel Type Distribution */}
        <div className="card flex flex-col justify-between" style={{ padding: 20 }}>
          <div className="flex items-center justify-between mb-4">
            <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Ship size={16} className="text-sky-500" /> Current Vessel Mix
            </h4>
            <SourceBadge source="HISTORICAL" />
          </div>
          <div className="h-[260px] w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={vesselTypeDistrib} cx="50%" cy="50%" outerRadius={90} innerRadius={50} paddingAngle={3} dataKey="value"
                  label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}>
                  {vesselTypeDistrib.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Weekly Throughput */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="card flex flex-col justify-between" style={{ padding: 20 }}>
          <div className="flex items-center justify-between mb-4">
            <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Package size={16} className="text-emerald-500" /> Weekly Vessel Throughput
            </h4>
            <SourceBadge source="HISTORICAL" />
          </div>
          <div className="h-[240px] w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={WEEKLY_THROUGHPUT}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis dataKey="day" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 8 }} />
                <Bar dataKey="vessels" fill="#0ea5e9" name="Vessels" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card flex flex-col justify-between" style={{ padding: 20 }}>
          <div className="flex items-center justify-between mb-4">
            <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Clock size={16} className="text-amber-500" /> Average Wait Time Trend
            </h4>
            <SourceBadge source="DEMO" />
          </div>
          <div className="h-[240px] w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={WEEKLY_THROUGHPUT}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis dataKey="day" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} label={{ value: 'Hours', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 8 }} />
                <defs>
                  <linearGradient id="waitGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="avgWait" name="Avg Wait (h)" stroke="#f59e0b" fill="url(#waitGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Monthly Utilization Trend */}
      <div className="card mb-8" style={{ padding: 20 }}>
        <div className="flex items-center justify-between mb-4">
          <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
            <TrendingUp size={16} className="text-purple-500" /> Monthly Berth Utilization Trend
          </h4>
          <SourceBadge source="DEMO" />
        </div>
        <div className="h-[260px] w-full min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={MONTHLY_UTILIZATION}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
              <XAxis dataKey="month" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} domain={[50, 100]} />
              <Tooltip contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 8 }} />
              <Legend />
              <Line type="monotone" dataKey="utilization" name="Utilization %" stroke="#8b5cf6" strokeWidth={3} dot={{ r: 5 }}
                activeDot={{ r: 8, fill: '#8b5cf6' }} />
              {/* Target line */}
              <Line type="monotone" data={MONTHLY_UTILIZATION.map(m => ({ ...m, target: 75 }))} dataKey="target"
                name="Target (75%)" stroke="#10b981" strokeDasharray="8 4" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Departing Soon Table */}
      <div className="flex items-center gap-3 mb-4">
        <Clock size={20} className="text-amber-500 animate-pulse" />
        <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--color-text-primary)' }}>
          Vessels Departing Soon
        </h3>
      </div>
      <div className="card mb-8" style={{ padding: 0, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'rgba(0,0,0,0.02)' }}>
              {['Berth', 'Vessel', 'Type', 'Progress', 'Departs In', 'Status'].map(h => (
                <th key={h} style={{
                  padding: '10px 14px', textAlign: 'left', color: 'var(--color-text-muted)',
                  fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5,
                  borderBottom: '1px solid var(--color-border)',
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {departingSoon.map(b => (
              <tr key={b.berth} style={{ borderBottom: '1px solid var(--color-border)' }}>
                <td style={{ padding: '10px 14px', fontWeight: 700, color: 'var(--color-text-primary)' }}>{b.berth}</td>
                <td style={{ padding: '10px 14px' }}>{b.vessel}</td>
                <td style={{ padding: '10px 14px' }}>
                  <span style={{ padding: '2px 8px', borderRadius: 20, fontSize: 11, background: 'rgba(14,165,233,0.1)', color: '#0ea5e9', fontWeight: 600 }}>
                    {b.vesselType}
                  </span>
                </td>
                <td style={{ padding: '10px 14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'rgba(0,0,0,0.08)', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', borderRadius: 3, width: `${b.progress}%`,
                        background: b.progress > 80 ? '#10b981' : '#0ea5e9',
                      }} />
                    </div>
                    <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-secondary)' }}>{b.progress}%</span>
                  </div>
                </td>
                <td style={{ padding: '10px 14px', fontWeight: 700, color: parseInt(b.eta_depart) <= 6 ? '#10b981' : 'var(--color-text-secondary)' }}>
                  {b.eta_depart}
                </td>
                <td style={{ padding: '10px 14px' }}>
                  {parseInt(b.eta_depart) <= 6
                    ? <span style={{ color: '#10b981', fontWeight: 700, fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4 }}>🟢 Departing Soon</span>
                    : <span style={{ color: '#0ea5e9', fontWeight: 600, fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4 }}>🔵 In Service</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
