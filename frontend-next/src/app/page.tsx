/**
 * BAOS AI — Landing Page
 * Exact replica of landing.html with Recharts instead of Chart.js
 */
'use client';

import { Fragment, useEffect, useRef, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Area, AreaChart,
} from 'recharts';

/* ═══════════════════════════════════════════════════════════
   ANIMATED COUNTER COMPONENT
   ═══════════════════════════════════════════════════════════ */
function AnimatedCounter({
  target, prefix = '', suffix = '', decimals = 0, duration = 2000,
}: {
  target: number; prefix?: string; suffix?: string; decimals?: number; duration?: number;
}) {
  const [value, setValue] = useState(0);
  const [started, setStarted] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setStarted(true); },
      { threshold: 0.15 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!started) return;
    const startTime = performance.now();
    let raf: number;
    function update(now: number) {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(parseFloat((target * eased).toFixed(decimals)));
      if (progress < 1) raf = requestAnimationFrame(update);
      else setValue(parseFloat(target.toFixed(decimals)));
    }
    raf = requestAnimationFrame(update);
    return () => cancelAnimationFrame(raf);
  }, [started, target, duration, decimals]);

  return <span ref={ref}>{prefix}{value.toFixed(decimals)}{suffix}</span>;
}

/* ═══════════════════════════════════════════════════════════
   REVEAL ON SCROLL COMPONENT
   ═══════════════════════════════════════════════════════════ */
function Reveal({ children, className = '', delay = 0 }: {
  children: React.ReactNode; className?: string; delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(30px)',
        transition: `opacity 0.8s ease ${delay}ms, transform 0.8s ease ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   CHART DATA
   ═══════════════════════════════════════════════════════════ */
const utilizationData = [
  { name: 'B1', utilization: 78, target: 75 },
  { name: 'B2', utilization: 62, target: 75 },
  { name: 'B3', utilization: 85, target: 75 },
  { name: 'B4', utilization: 45, target: 75 },
  { name: 'B5', utilization: 71, target: 75 },
];

const turnaroundData = [
  { day: 'Mon', avg: 28.5, target: 24 },
  { day: 'Tue', avg: 26.2, target: 24 },
  { day: 'Wed', avg: 27.8, target: 24 },
  { day: 'Thu', avg: 24.1, target: 24 },
  { day: 'Fri', avg: 25.6, target: 24 },
  { day: 'Sat', avg: 29.3, target: 24 },
  { day: 'Sun', avg: 26.4, target: 24 },
];

const revenueData = [
  { month: 'Jan', revenue: 320, cost: 180 },
  { month: 'Feb', revenue: 380, cost: 195 },
  { month: 'Mar', revenue: 410, cost: 210 },
  { month: 'Apr', revenue: 395, cost: 200 },
  { month: 'May', revenue: 450, cost: 220 },
  { month: 'Jun', revenue: 480, cost: 230 },
];

const distributionData = [
  { name: 'Container', value: 40, color: 'rgba(0, 102, 204, 0.8)' },
  { name: 'Bulk Carrier', value: 25, color: 'rgba(0, 170, 153, 0.8)' },
  { name: 'General Cargo', value: 20, color: 'rgba(139, 92, 246, 0.8)' },
  { name: 'Tanker', value: 15, color: 'rgba(245, 158, 11, 0.8)' },
];

const heatmapData = [
  { berth: 'B1', data: [72, 85, 68, 91, 78, 45, 38] },
  { berth: 'B2', data: [55, 62, 78, 70, 88, 52, 41] },
  { berth: 'B3', data: [88, 92, 75, 83, 95, 60, 55] },
  { berth: 'B4', data: [42, 58, 65, 72, 68, 35, 28] },
  { berth: 'B5', data: [68, 75, 82, 88, 72, 48, 42] },
];
const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function getHeatmapColor(val: number) {
  if (val >= 90) return { bg: 'rgba(239,68,68,0.5)', color: '#EF4444' };
  if (val >= 75) return { bg: 'rgba(239,68,68,0.3)', color: '#EF4444' };
  if (val >= 60) return { bg: 'rgba(245,158,11,0.5)', color: '#F59E0B' };
  if (val >= 40) return { bg: 'rgba(245,158,11,0.3)', color: '#F59E0B' };
  return { bg: 'rgba(16,185,129,0.3)', color: '#10B981' };
}

const COLORS_UTIL = ['rgba(0,102,204,0.7)', 'rgba(0,170,153,0.7)', 'rgba(239,68,68,0.7)', 'rgba(139,92,246,0.7)', 'rgba(245,158,11,0.7)'];

/* ═══════════════════════════════════════════════════════════
   FEATURES
   ═══════════════════════════════════════════════════════════ */
const features = [
  { icon: '🤖', title: 'AI-Powered Optimization', desc: 'Machine learning algorithms analyze historical patterns to recommend optimal berth assignments.' },
  { icon: '📊', title: 'Real-time Analytics', desc: 'Live dashboards with KPIs, charts, and heatmaps for port-wide operational visibility.' },
  { icon: '⚡', title: 'Constraint Solver', desc: 'CP-SAT constraint programming handles 15+ constraints including vessel dimensions, tide, and SLA.' },
  { icon: '💰', title: 'Commercial Intelligence', desc: 'Revenue optimization with dynamic pricing, partnership tiers, and cost-benefit analysis.' },
  { icon: '🔄', title: 'Continuous Learning', desc: 'Feedback loops track outcomes and retrain models weekly for ever-improving accuracy.' },
  { icon: '🛡️', title: 'Enterprise Security', desc: 'JWT authentication, role-based access, and audit logging for compliance.' },
];

/* ═══════════════════════════════════════════════════════════
   LANDING PAGE COMPONENT
   ═══════════════════════════════════════════════════════════ */
export default function LandingPage() {
  const [navScrolled, setNavScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setNavScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen" style={{ background: 'var(--color-dark)' }}>
      {/* ── Navbar ──────────────────────────────────────────── */}
      <nav
        id="navbar"
        className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
        style={{
          background: navScrolled ? 'rgba(255,255,255,0.98)' : 'rgba(255,255,255,0.95)',
          boxShadow: navScrolled ? '0 4px 20px rgba(0,0,0,0.05)' : 'none',
          padding: '14px 0',
        }}
      >
        <div className="max-w-[1200px] mx-auto px-6 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 no-underline">
            <span className="text-2xl">🚢</span>
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 20, color: 'var(--color-text-primary)' }}>
              BAOS <span style={{ color: 'var(--color-primary)' }}>AI</span>
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Features</a>
            <a href="#metrics" className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Metrics</a>
            <a href="#analytics" className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Analytics</a>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="btn btn-ghost btn-sm">Sign In</Link>
            <Link href="/signup" className="btn btn-primary btn-sm">Get Started</Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────────── */}
      <section className="pt-[140px] pb-[80px] px-6 text-center gradient-hero">
        <div className="max-w-[900px] mx-auto animate-fade-in-up">
          <div className="inline-block px-4 py-2 rounded-full text-xs font-semibold mb-6"
               style={{ background: 'rgba(0,102,204,0.15)', color: 'var(--color-primary)', border: '1px solid rgba(0,102,204,0.3)' }}>
            🚀 Maritime Decision Intelligence Platform
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold mb-6 leading-tight"
              style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text-primary)' }}>
            Optimize Your Port with{' '}
            <span style={{ background: 'linear-gradient(135deg, #0066CC, #00AA99)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              AI Intelligence
            </span>
          </h1>
          <p className="text-lg mb-10 max-w-[640px] mx-auto" style={{ color: 'var(--color-text-muted)', lineHeight: 1.7 }}>
            AI-powered berth allocation that reduces turnaround time, maximizes revenue,
            and ensures SLA compliance with real-time optimization.
          </p>
          <div className="flex justify-center gap-4 mb-12">
            <Link href="/signup" className="btn btn-primary btn-lg">Get Started Free →</Link>
            <a href="#features" className="btn btn-outline btn-lg">Learn More</a>
          </div>
          {/* Hero stats */}
          <div className="flex justify-center gap-12 flex-wrap">
            {[
              { value: 94, suffix: '%', label: 'SLA Compliance' },
              { value: 26.5, suffix: 'h', label: 'Avg Turnaround', decimals: 1 },
              { value: 480, prefix: '$', suffix: 'K', label: 'Monthly Revenue' },
            ].map((s, i) => (
              <div key={i} className="text-center">
                <div className="text-3xl font-extrabold" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-primary)' }}>
                  <AnimatedCounter target={s.value} prefix={s.prefix || ''} suffix={s.suffix} decimals={s.decimals || 0} />
                </div>
                <div className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ───────────────────────────────────────── */}
      <section id="features" className="py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <Reveal className="text-center mb-14">
            <h2 className="text-3xl font-bold mb-3" style={{ fontFamily: 'var(--font-display)' }}>Powered by Advanced AI</h2>
            <p style={{ color: 'var(--color-text-muted)' }}>Enterprise-grade tools for modern port operations</p>
          </Reveal>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <Reveal key={i} delay={i * 100}>
                <div className="card h-full">
                  <div className="text-3xl mb-4">{f.icon}</div>
                  <h3 className="text-lg font-bold mb-2" style={{ fontFamily: 'var(--font-display)' }}>{f.title}</h3>
                  <p className="text-sm" style={{ color: 'var(--color-text-muted)', lineHeight: 1.6 }}>{f.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── KPI Metrics ────────────────────────────────────── */}
      <section id="metrics" className="py-20 px-6" style={{ background: 'var(--color-dark-card)' }}>
        <div className="max-w-[1200px] mx-auto">
          <Reveal className="text-center mb-14">
            <h2 className="text-3xl font-bold mb-3" style={{ fontFamily: 'var(--font-display)' }}>Key Performance Metrics</h2>
            <p style={{ color: 'var(--color-text-muted)' }}>Real-time insights driving operational excellence</p>
          </Reveal>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { icon: '🚢', value: 142, suffix: '', label: 'Active Vessels', sub: '+8.4% vs last month' },
              { icon: '⏱️', value: 26.5, suffix: 'h', label: 'Avg Turnaround', sub: '-12% improvement', decimals: 1 },
              { icon: '📈', value: 78, suffix: '%', label: 'Berth Utilization', sub: 'Optimal range: 70-85%' },
              { icon: '💰', value: 480, prefix: '$', suffix: 'K', label: 'Monthly Revenue', sub: '+14.3% growth' },
            ].map((kpi, i) => (
              <Reveal key={i} delay={i * 150}>
                <div className="card text-center">
                  <div className="text-3xl mb-3">{kpi.icon}</div>
                  <div className="text-2xl font-extrabold mb-1" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-primary)' }}>
                    <AnimatedCounter target={kpi.value} prefix={kpi.prefix || ''} suffix={kpi.suffix} decimals={kpi.decimals || 0} />
                  </div>
                  <div className="text-sm font-semibold mb-1" style={{ color: 'var(--color-text-primary)' }}>{kpi.label}</div>
                  <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{kpi.sub}</div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Charts ─────────────────────────────────────────── */}
      <section id="analytics" className="py-20 px-6">
        <div className="max-w-[1200px] mx-auto">
          <Reveal className="text-center mb-14">
            <h2 className="text-3xl font-bold mb-3" style={{ fontFamily: 'var(--font-display)' }}>Operational Analytics</h2>
            <p style={{ color: 'var(--color-text-muted)' }}>Data-driven insights for smarter port management</p>
          </Reveal>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Chart A: Utilization Bar */}
            <Reveal>
              <div className="card-flat" style={{ height: 340 }}>
                <h3 className="text-sm font-bold mb-4" style={{ fontFamily: 'var(--font-display)' }}>Berth Utilization</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={utilizationData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.2)" />
                    <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                    <Tooltip contentStyle={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 8, color: '#0F172A' }} />
                    <Legend wrapperStyle={{ fontSize: 12, color: '#64748b' }} />
                    <Bar dataKey="utilization" name="Current Utilization %" radius={[6, 6, 0, 0]}>
                      {utilizationData.map((_, i) => <Cell key={i} fill={COLORS_UTIL[i]} />)}
                    </Bar>
                    <Line type="linear" dataKey="target" name="Optimal Target" stroke="#10b981" strokeDasharray="6 4" strokeWidth={2} dot={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Reveal>

            {/* Chart B: Turnaround Line */}
            <Reveal delay={100}>
              <div className="card-flat" style={{ height: 340 }}>
                <h3 className="text-sm font-bold mb-4" style={{ fontFamily: 'var(--font-display)' }}>Vessel Turnaround Trend</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={turnaroundData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.2)" />
                    <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={[20, 35]} tickFormatter={(v) => `${v}h`} />
                    <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #475569', borderRadius: 8, color: '#F1F5F9' }} />
                    <Area type="monotone" dataKey="avg" name="Avg Turnaround (hours)" stroke="#0066CC" fill="rgba(0,102,204,0.08)" strokeWidth={2.5} dot={{ fill: '#0066CC', stroke: '#fff', strokeWidth: 2, r: 4 }} />
                    <Line type="linear" dataKey="target" name="Target (24h)" stroke="#10b981" strokeDasharray="6 4" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Reveal>

            {/* Chart C: Revenue Bar */}
            <Reveal delay={200}>
              <div className="card-flat" style={{ height: 340 }}>
                <h3 className="text-sm font-bold mb-4" style={{ fontFamily: 'var(--font-display)' }}>Revenue Impact</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={revenueData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.2)" />
                    <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(v) => `$${v}K`} />
                    <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #475569', borderRadius: 8, color: '#F1F5F9' }} />
                    <Legend wrapperStyle={{ fontSize: 12, color: '#64748b' }} />
                    <Bar dataKey="revenue" name="Revenue ($K)" fill="rgba(0,102,204,0.7)" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="cost" name="Cost ($K)" fill="rgba(239,68,68,0.5)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Reveal>

            {/* Chart D: Distribution Doughnut */}
            <Reveal delay={300}>
              <div className="card-flat" style={{ height: 340 }}>
                <h3 className="text-sm font-bold mb-4" style={{ fontFamily: 'var(--font-display)' }}>Vessel Type Distribution</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={distributionData} cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                         paddingAngle={2} dataKey="value" nameKey="name">
                      {distributionData.map((d, i) => <Cell key={i} fill={d.color} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: '#1E293B', border: '1px solid #475569', borderRadius: 8, color: '#F1F5F9' }} />
                    <Legend wrapperStyle={{ fontSize: 12, color: '#64748b' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* ── Heatmap ────────────────────────────────────────── */}
      <section className="py-20 px-6" style={{ background: 'var(--color-dark-card)' }}>
        <div className="max-w-[1200px] mx-auto">
          <Reveal className="text-center mb-14">
            <h2 className="text-3xl font-bold mb-3" style={{ fontFamily: 'var(--font-display)' }}>Utilization Heatmap</h2>
            <p style={{ color: 'var(--color-text-muted)' }}>Weekly berth occupancy at a glance</p>
          </Reveal>
          <Reveal>
            <div className="card-flat max-w-[800px] mx-auto">
              <div className="heatmap-grid">
                <div className="heatmap-header"></div>
                {days.map(d => <div key={d} className="heatmap-header">{d}</div>)}
                {heatmapData.map(row => (
                  <Fragment key={row.berth}>
                    <div className="heatmap-label">{row.berth}</div>
                    {row.data.map((val, di) => {
                      const c = getHeatmapColor(val);
                      return (
                        <div key={`${row.berth}-${di}`}
                             className="heatmap-cell"
                             style={{ background: c.bg, color: c.color }}
                             title={`${row.berth} · ${days[di]}: ${val}%`}>
                          {val}%
                        </div>
                      );
                    })}
                  </Fragment>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────── */}
      <section className="py-20 px-6 text-center">
        <Reveal>
          <div className="max-w-[600px] mx-auto">
            <h2 className="text-3xl font-bold mb-4" style={{ fontFamily: 'var(--font-display)' }}>
              Ready to Optimize Your Port?
            </h2>
            <p className="mb-8" style={{ color: 'var(--color-text-muted)' }}>
              Start using AI-powered berth allocation today. No setup required.
            </p>
            <div className="flex justify-center gap-4">
              <Link href="/signup" className="btn btn-primary btn-lg">Start Free Trial →</Link>
              <Link href="/login" className="btn btn-secondary btn-lg">Sign In</Link>
            </div>
          </div>
        </Reveal>
      </section>

      {/* ── Footer ─────────────────────────────────────────── */}
      <footer className="py-8 px-6 text-center" style={{ borderTop: '1px solid var(--color-dark-border)' }}>
        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
          © 2026 BAOS AI — Maritime Decision Intelligence Platform. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
