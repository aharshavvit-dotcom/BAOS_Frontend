/**
 * Get Recommendation Page â€” AI-powered berth recommendations
 * Features: Rich agentic explanations, interactive berth timeline,
 * confidence comparison, detailed constraint analysis
 *
 * REFACTORED: Uses real backend API call with correct schema instead of local fallback.
 * Uses dynamic port store to resolve friendly berth names and colors.
 */
'use client';

import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { usePortStore } from '@/store/portStore';
import { getRecommendation, type BerthRecommendation, type ParameterCheck } from '@/services/recommendations';
import { extractApiError } from '@/services/client';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { PortSelector } from '@/components/features/PortSelector';
import SourceBadge from '@/components/ui/SourceBadge';
import { VESSEL_TYPES } from '@/lib/constants';

/* Types */
interface VesselForm {
  vessel_name: string;
  vessel_type: string;
  cargo_type: string;
  eta_date: string;
  eta_time: string;
  cargo_tons: number;
  loa: number;
  beam: number;
  draft: number;
  dwt: number;
}

const CARGO_TYPES = ['COAL', 'IRON ORE', 'CONTAINER', 'CRUDE OIL', 'CHEMICALS', 'GENERAL', 'VEHICLES', 'PETROLEUM', 'DIESEL', 'FUEL OIL', 'CEMENT', 'FERTILIZER', 'GRAIN', 'BAUXITE', 'SUGAR', 'LIMESTONE', 'STEEL', 'TIMBER', 'LPG', 'LNG', 'BREAK BULK', 'PROJECT CARGO'];
const RANK_COLORS = ['#10b981', '#0ea5e9', '#8b5cf6'];

export default function RecommendPage() {
  const { selectedPortCode, getBerthColor, getBerthDisplayName, fetchPorts } = usePortStore();

  const [form, setForm] = useState<VesselForm>({
    vessel_name: '',
    vessel_type: 'Bulk Dry',
    cargo_type: 'COAL',
    eta_date: '',
    eta_time: '08:00',
    cargo_tons: 25000,
    loa: 180,
    beam: 28,
    draft: 10,
    dwt: 30000,
  });
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<BerthRecommendation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hoveredBar, setHoveredBar] = useState<BerthRecommendation | null>(null);
  const [breakdownOpen, setBreakdownOpen] = useState(false);
  const [barPos, setBarPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    fetchPorts();
    setForm(prev => ({
      ...prev,
      eta_date: new Date(Date.now() + 86400000).toISOString().split('T')[0]
    }));
  }, [fetchPorts]);

  function updateField<K extends keyof VesselForm>(key: K, val: VesselForm[K]) {
    setForm(prev => ({ ...prev, [key]: val }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await getRecommendation({
        vessel_name: form.vessel_name,
        vessel_type: form.vessel_type,
        cargo_type: form.cargo_type,
        loa_m: form.loa,
        beam_m: form.beam,
        draft_m: form.draft,
        dwt: form.dwt,
        cargo_tons: form.cargo_tons,
        eta: `${form.eta_date}T${form.eta_time}:00`,
        port_code: selectedPortCode,
      });

      setResults(response.recommendations);
      setError(null);
    } catch (err) {
      const apiErr = extractApiError(err);
      setError(apiErr.message);
      setResults(null);
    } finally {
      setLoading(false);
    }
  }

  function confColor(c: number) {
    return c > 60 ? '#10b981' : c > 30 ? '#f59e0b' : '#ef4444';
  }

  const best = results?.[0];

  return (
    <div>
      {/* Section Header */}
      <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="text-2xl">ðŸš¢</span>
            <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 22, color: 'var(--color-text-primary)' }}>
              Enter Vessel Details
            </h2>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>
            Fill in vessel information to receive AI-powered berth recommendations with detailed explanations
          </p>
        </div>
        <PortSelector />
      </div>

      {/* Vessel Input Form */}
      <form onSubmit={handleSubmit}>
        <div className="card" style={{ padding: 24, marginBottom: 24 }}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Column 1 */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Vessel Name</label>
                <input className="form-input" placeholder="e.g. MV OCEAN STAR" value={form.vessel_name} onChange={e => updateField('vessel_name', e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Vessel Type</label>
                <select className="form-input" value={form.vessel_type} onChange={e => updateField('vessel_type', e.target.value)}>
                  {VESSEL_TYPES.map(vt => <option key={vt} value={vt}>{vt}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Cargo Type</label>
                <select className="form-input" value={form.cargo_type} onChange={e => updateField('cargo_type', e.target.value)}>
                  {CARGO_TYPES.map(ct => <option key={ct} value={ct}>{ct}</option>)}
                </select>
              </div>
            </div>

            {/* Column 2 */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>ETA Date</label>
                <input className="form-input" type="date" value={form.eta_date} onChange={e => updateField('eta_date', e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>ETA Time</label>
                <input className="form-input" type="time" value={form.eta_time} onChange={e => updateField('eta_time', e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Cargo (tons)</label>
                <input className="form-input" type="number" min={0} step={1000} value={form.cargo_tons} onChange={e => updateField('cargo_tons', +e.target.value)} />
              </div>
            </div>

            {/* Column 3 */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>LOA (m)</label>
                <input className="form-input" type="number" min={10} step={5} value={form.loa} onChange={e => updateField('loa', +e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Beam (m)</label>
                <input className="form-input" type="number" min={1} step={1} value={form.beam} onChange={e => updateField('beam', +e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Draft (m)</label>
                  <input className="form-input" type="number" min={1} step={0.5} value={form.draft} onChange={e => updateField('draft', +e.target.value)} />
                </div>
                <div>
                  <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>DWT (tons)</label>
                  <input className="form-input" type="number" min={0} step={1000} value={form.dwt} onChange={e => updateField('dwt', +e.target.value)} />
                </div>
              </div>
            </div>
          </div>

          <button type="submit" disabled={loading} className="btn btn-primary btn-lg w-full mt-6" style={{ fontSize: 16, fontWeight: 700 }}>
            {loading ? (
              <><span className="animate-spin inline-block mr-2">âš™ï¸</span> AI Analyzing Berth Options...</>
            ) : (
              <>ðŸ§  Get Berthing Recommendation</>
            )}
          </button>
        </div>
      </form>

      {error && (
        <div style={{
          background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)',
          borderRadius: 10, padding: '12px 16px', marginBottom: 24,
          fontSize: 13, color: '#ef4444', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span>âš ï¸</span> {error}
          <button onClick={() => setError(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444' }}>âœ•</button>
        </div>
      )}

      {/* Results */}
      {results && best && (
        <>
          {/* Success banner */}
          <div style={{
            background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.3)',
            borderRadius: 10, padding: '14px 20px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12,
          }}>
            <span style={{ fontSize: 20 }}>âœ…</span>
            <span style={{ color: 'var(--color-text-secondary)', fontSize: 13 }}>
              {results.length} berth recommendation{results.length > 1 ? 's' : ''} found for <strong>{form.vessel_name || 'Vessel'}</strong> Â· {form.vessel_type} Â· ETA {form.eta_date} {form.eta_time}
            </span>
          </div>

          {/* KPI Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            {[
              { icon: 'ðŸŽ¯', value: `${best.confidence.toFixed(0)}%`, label: 'Top Confidence', color: confColor(best.confidence) },
              { icon: 'â±ï¸', value: `${best.expected_wait_hours.toFixed(1)}h`, label: 'Avg. Wait (Historical)', color: '#0ea5e9' },
              { icon: 'ðŸ”§', value: `${best.expected_service_hours.toFixed(0)}h`, label: 'Avg. Service (Historical)', color: '#8b5cf6' },
              { icon: 'ðŸ—ï¸', value: `${results.length}`, label: 'Total Berths Ranked', color: '#f59e0b' },
            ].map((kpi, i) => (
              <div key={i} className="card-flat text-center" style={{ padding: 16 }}>
                <div style={{ fontSize: 20 }}>{kpi.icon}</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: kpi.color, fontFamily: 'var(--font-display)' }}>{kpi.value}</div>
                <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{kpi.label}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 20, lineHeight: 1.5 }}>
            â„¹ï¸ <strong>Wait &amp; Service times</strong> shown above are historical averages derived from past port logs. They are <strong>not real-time</strong> â€” actual times will vary based on current port congestion, weather, and vessel queue. These values do <strong>not</strong> influence the berth ranking; ranking is based solely on vessel-berth suitability.
          </p>

          {/* Interactive Berth Timeline */}
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xl">ðŸ—“</span>
            <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--color-text-primary)' }}>
              Berth Allocation Timeline
            </h3>
            <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Hover for details</span>
          </div>
          <div className="card mb-8" style={{ padding: 20, overflow: 'auto', position: 'relative' }}>
            {(() => {
              const maxH = Math.max(...results.map(r => r.timeline_end), 48);
              return (
                <div style={{ minWidth: 500 }}>
                  {results.map((opt, i) => (
                    <div key={opt.rank} className="flex items-center gap-3 mb-3" style={{ height: 48 }}>
                      <div style={{ width: 150, fontSize: 11, textAlign: 'right' }}>
                        <div style={{ fontWeight: 700, color: RANK_COLORS[i] || '#94a3b8' }}>
                          #{opt.rank} {getBerthDisplayName(opt.berth_code)}
                        </div>
                      </div>
                      <div className="flex-1 relative" style={{ height: 40, background: 'rgba(0,0,0,0.03)', borderRadius: 8, border: '1px solid rgba(0,0,0,0.04)' }}>
                        {/* Hour markers */}
                        {Array.from({ length: Math.ceil(maxH / 8) }, (_, j) => j * 8).map(h => (
                          <div key={h} style={{ position: 'absolute', left: `${(h / maxH) * 100}%`, top: 0, bottom: 0, borderLeft: '1px dashed rgba(0,0,0,0.06)' }} />
                        ))}
                        {/* Wait period */}
                        {opt.expected_wait_hours > 0 && (
                          <div style={{
                            position: 'absolute', top: 8, height: 24, borderRadius: '4px 0 0 4px',
                            left: `${(opt.timeline_start / maxH) * 100}%`,
                            width: `${Math.max((opt.expected_wait_hours / maxH) * 100, 1)}%`,
                            background: 'repeating-linear-gradient(45deg, rgba(245,158,11,0.15), rgba(245,158,11,0.15) 4px, transparent 4px, transparent 8px)',
                            border: '1px dashed rgba(245,158,11,0.4)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: 9, color: '#f59e0b', fontWeight: 600,
                          }}>
                            â³ {opt.expected_wait_hours.toFixed(1)}h
                          </div>
                        )}
                        {/* Service period */}
                        <div
                           onMouseEnter={e => {
                             const rect = e.currentTarget.getBoundingClientRect();
                             setHoveredBar(opt);
                             setBarPos({ x: rect.left + rect.width / 2, y: rect.top - 10 });
                           }}
                           onMouseLeave={() => setHoveredBar(null)}
                           style={{
                             position: 'absolute', top: 4, height: 32, borderRadius: 6, cursor: 'pointer',
                             left: `${((opt.timeline_start + opt.expected_wait_hours) / maxH) * 100}%`,
                             width: `${Math.max((opt.expected_service_hours / maxH) * 100, 3)}%`,
                             background: `linear-gradient(135deg, ${RANK_COLORS[i] || '#94a3b8'}, ${RANK_COLORS[i] || '#94a3b8'}cc)`,
                             display: 'flex', alignItems: 'center', justifyContent: 'center',
                             fontSize: 10, fontWeight: 700, color: 'white', overflow: 'hidden', whiteSpace: 'nowrap',
                             boxShadow: hoveredBar?.rank === opt.rank ? '0 4px 12px rgba(0,0,0,0.2)' : '0 1px 3px rgba(0,0,0,0.1)',
                             transform: hoveredBar?.rank === opt.rank ? 'scale(1.03)' : 'scale(1)',
                             transition: 'transform 0.15s, box-shadow 0.15s',
                           }}>
                          {form.vessel_name || 'Vessel'} Â· {opt.confidence.toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  ))}
                  {/* Time axis */}
                  <div className="flex items-center gap-3" style={{ marginTop: 6 }}>
                    <div style={{ width: 150 }} />
                    <div className="flex-1 flex justify-between" style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                      {Array.from({ length: 5 }, (_, i) => <span key={i}>{((maxH * i) / 4).toFixed(0)}h</span>)}
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Floating Timeline Tooltip */}
            {hoveredBar && (
              <div style={{
                position: 'fixed', left: barPos.x, top: barPos.y, transform: 'translate(-50%, -100%)',
                zIndex: 1000, background: 'white', border: '1px solid #e2e8f0', borderRadius: 10,
                padding: '12px 16px', minWidth: 300, boxShadow: '0 8px 30px rgba(0,0,0,0.12)',
                fontSize: 12, lineHeight: 1.6, color: 'var(--color-text-secondary)',
              }}>
                <div style={{ fontWeight: 800, fontSize: 14, color: 'var(--color-text-primary)', marginBottom: 4 }}>
                  #{hoveredBar.rank} {getBerthDisplayName(hoveredBar.berth_code)}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px 12px', fontSize: 11, marginBottom: 6 }}>
                  <span>ðŸ“Š Confidence: <strong style={{ color: confColor(hoveredBar.confidence) }}>{hoveredBar.confidence.toFixed(0)}%</strong></span>
                  <span>â³ Wait: <strong>{hoveredBar.expected_wait_hours.toFixed(1)}h</strong></span>
                  <span>ðŸ”§ Service: <strong>{hoveredBar.expected_service_hours.toFixed(0)}h</strong></span>
                  <span>ðŸŽ¯ Suitability: <strong>{hoveredBar.suitability_score.toFixed(0)}%</strong></span>
                  <span>âš ï¸ Risk: <strong style={{ color: hoveredBar.risk_score > 20 ? '#ef4444' : '#10b981' }}>{hoveredBar.risk_score}%</strong></span>
                </div>
                <div style={{ fontSize: 10, color: 'var(--color-text-muted)', borderTop: '1px solid #f1f5f9', paddingTop: 4 }}>
                  {hoveredBar.explanation}
                </div>
              </div>
            )}
          </div>

          {/* Section Header â€” Top 3 */}
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xl">ðŸŽ¯</span>
            <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--color-text-primary)' }}>
              Top Recommended Berths
            </h3>
            <span className="badge badge-success">Top 3 of {results.length}</span>
          </div>

          {/* Recommendation Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {/* Only show top 3 cards */}
            {results.slice(0, 3).map((opt, i) => (
              <div key={opt.rank} className="card animate-fade-in-up"
                style={{ borderTop: `3px solid ${RANK_COLORS[i] || '#94a3b8'}`, animationDelay: `${i * 0.15}s`, padding: 0, overflow: 'hidden' }}>
                {/* Rank badge */}
                <div style={{
                  position: 'absolute', top: 12, right: 12, width: 32, height: 32, borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: RANK_COLORS[i] || '#94a3b8', color: 'white', fontWeight: 800, fontSize: 14,
                }}>
                  #{opt.rank}
                </div>

                <div style={{ padding: '20px 20px 16px' }}>
                  <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--color-text-primary)', fontFamily: 'var(--font-display)', marginBottom: 14 }}>
                    {getBerthDisplayName(opt.berth_code)}
                  </div>

                  {/* Metrics */}
                  <div className="grid grid-cols-3 gap-2 text-center" style={{ marginBottom: 14 }}>
                    <div>
                      <div style={{ fontSize: 20, fontWeight: 800, color: confColor(opt.confidence) }}>{opt.confidence.toFixed(0)}%</div>
                      <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>Confidence</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--color-text-primary)' }}>{opt.expected_wait_hours.toFixed(1)}h</div>
                      <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>Est. Wait</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--color-text-primary)' }}>{opt.expected_service_hours.toFixed(0)}h</div>
                      <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>Service</div>
                    </div>
                  </div>

                  {/* Pros & Cons */}
                  <div style={{ marginBottom: 12 }}>
                    {opt.pros.slice(0, 3).map((p, j) => (
                      <div key={j} className="flex items-start gap-2 mb-1">
                        <span style={{ color: '#10b981', fontSize: 11, marginTop: 2 }}>âœ“</span>
                        <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{p}</span>
                      </div>
                    ))}
                    {opt.cons.slice(0, 2).map((c, j) => (
                      <div key={j} className="flex items-start gap-2 mb-1">
                        <span style={{ color: '#ef4444', fontSize: 11, marginTop: 2 }}>âœ—</span>
                        <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{c}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* AI Agentic Explanation */}
                <div style={{ padding: '0 20px 16px' }}>
                  <details>
                    <summary style={{ fontSize: 12, cursor: 'pointer', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                      ðŸ¤– AI Agentic Explanation
                    </summary>
                    <div style={{
                      fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 8,
                      padding: '10px 14px', background: 'rgba(99,102,241,0.04)', borderRadius: 8,
                      lineHeight: 1.8, borderLeft: '3px solid rgba(99,102,241,0.3)',
                    }}>
                      {opt.ai_reasoning}
                    </div>
                  </details>
                </div>

                {/* Footer */}
                <div style={{
                  padding: '12px 20px', background: 'rgba(0,0,0,0.02)',
                  borderTop: '1px solid var(--color-border)', fontSize: 12, color: 'var(--color-text-muted)',
                }}>
                  {opt.explanation}
                </div>
              </div>
            ))}
          </div>

          {/* Complete Berth Rankings (ALL berths) */}
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xl">ðŸ“Š</span>
            <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--color-text-primary)' }}>
              Complete Berth Rankings
            </h3>
            <span className="badge" style={{ background: 'rgba(14,165,233,0.15)', color: '#0ea5e9' }}>{results.length} berths</span>
          </div>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 12 }}>All eligible berths ranked with AI reasoning for each position</p>
          <div className="card" style={{ padding: 0, overflow: 'auto', marginBottom: 24 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'rgba(0,0,0,0.02)' }}>
                  {['Rank', 'Tier', 'Berth Name', 'Confidence', 'Suitability', 'Avg Wait* (h)', 'Avg Service* (h)', 'Ranking Reason'].map(h => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, borderBottom: '2px solid var(--color-border)', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map(r => {
                  const tier = r.rank === 1 ? 'ðŸ¥‡ Top Pick' : r.rank === 2 ? 'ðŸ¥ˆ Strong' : r.rank === 3 ? 'ðŸ¥‰ Good' : r.suitability_score > 10 ? 'âœ… Viable' : 'â¬œ Low Match';
                  return (
                    <tr key={r.rank} style={{ borderBottom: '1px solid var(--color-border)', background: r.rank <= 3 ? 'rgba(16,185,129,0.03)' : undefined }}>
                      <td style={{ padding: '10px 12px', fontWeight: 700 }}>#{r.rank}</td>
                      <td style={{ padding: '10px 12px', fontSize: 12 }}>{tier}</td>
                      <td style={{ padding: '10px 12px', fontWeight: 600 }}>{getBerthDisplayName(r.berth_code)}</td>
                      <td style={{ padding: '10px 12px', color: confColor(r.confidence), fontWeight: 700 }}>{r.confidence.toFixed(1)}%</td>
                      <td style={{ padding: '10px 12px' }}>{r.suitability_score.toFixed(1)}%</td>
                      <td style={{ padding: '10px 12px' }}>{r.expected_wait_hours.toFixed(1)}</td>
                      <td style={{ padding: '10px 12px' }}>{r.expected_service_hours.toFixed(1)}</td>
                      <td style={{ padding: '10px 12px', fontSize: 12, color: 'var(--color-text-secondary)', maxWidth: 300 }}>{r.compact_reason || r.explanation}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Confidence Comparison Chart */}
          <div className="card flex flex-col justify-between" style={{ padding: 20, marginBottom: 24 }}>
            <div className="flex items-center justify-between mb-4">
              <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, color: 'var(--color-text-primary)' }}>
                ðŸ“Š Confidence Comparison
              </h4>
              <SourceBadge source="SOLVER" />
            </div>
            <div className="h-[260px] w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={results.map(r => ({ name: getBerthDisplayName(r.berth_code), Confidence: r.confidence }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} angle={-20} textAnchor="end" height={60} />
                  <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 8 }} />
                  <Bar dataKey="Confidence" fill="#10b981" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Detailed Berth Analysis - Parameter-Level Breakdown */}
          <div
            onClick={() => setBreakdownOpen(!breakdownOpen)}
            style={{
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10,
              padding: '14px 20px', background: 'var(--color-dark-card, rgba(0,0,0,0.02))',
              border: '1px solid var(--color-border)', borderRadius: 10, marginBottom: breakdownOpen ? 0 : 24,
              borderBottom: breakdownOpen ? 'none' : undefined,
              borderBottomLeftRadius: breakdownOpen ? 0 : 10, borderBottomRightRadius: breakdownOpen ? 0 : 10,
            }}
          >
            <span style={{ fontSize: 18 }}>ðŸ§ </span>
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15, color: 'var(--color-text-primary)', flex: 1 }}>
              Detailed Berth Analysis â€” Parameter-Level Breakdown
            </span>
            <span style={{ fontSize: 14, color: 'var(--color-text-muted)' }}>{breakdownOpen ? 'â–²' : 'â–¼'}</span>
          </div>
          {breakdownOpen && (
            <div style={{
              border: '1px solid var(--color-border)', borderTop: 'none',
              borderBottomLeftRadius: 10, borderBottomRightRadius: 10,
              padding: 20, marginBottom: 24, background: 'var(--color-dark-card, white)',
            }}>
              {results.map(opt => {
                const statusColor = (s: string) => s === 'pass' || s === 'ok' ? '#10b981' : s === 'tight' ? '#f59e0b' : s === 'fail' ? '#ef4444' : '#6366f1';
                const feasBadge = opt.structured_breakdown.some(c => c.status === 'fail')
                  ? { text: 'NOT FEASIBLE', bg: 'rgba(239,68,68,0.1)', color: '#ef4444' }
                  : { text: 'FEASIBLE', bg: 'rgba(16,185,129,0.1)', color: '#10b981' };
                const categories = ['Physical Fit', 'Operational', 'Performance', 'Commercial Impact'];
                const catEmoji: Record<string, string> = { 'Physical Fit': 'ðŸ”§', 'Operational': 'âš™ï¸', 'Performance': 'ðŸ“Š', 'Commercial Impact': 'ðŸ’°' };
                return (
                  <div key={opt.rank} style={{ marginBottom: 20, background: 'rgba(0,0,0,0.01)', border: '1px solid var(--color-border)', borderRadius: 10, padding: 18, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
                    {/* Header */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10, flexWrap: 'wrap', gap: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 16, fontWeight: 800 }}>ðŸ—ï¸ {getBerthDisplayName(opt.berth_code)} â€” Rank #{opt.rank}</span>
                        <span style={{ background: feasBadge.bg, color: feasBadge.color, padding: '2px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700, textTransform: 'uppercase' }}>{feasBadge.text}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ color: confColor(opt.confidence), fontWeight: 800, fontSize: 18 }}>{opt.confidence.toFixed(0)}%</span>
                        <span style={{ color: 'var(--color-text-muted)', fontSize: 12, fontWeight: 600 }}>confidence</span>
                      </div>
                    </div>
                    <div style={{ color: 'var(--color-text-secondary)', fontSize: 13, lineHeight: 1.6, marginBottom: 10 }}>{opt.explanation}</div>
                    {/* 4-category breakdown */}
                    {categories.map(cat => {
                      const checks = opt.structured_breakdown.filter(c => c.category === cat);
                      if (!checks.length) return null;
                      const pCount = checks.filter(c => c.status === 'pass' || c.status === 'ok').length;
                      const wCount = checks.filter(c => c.status === 'tight').length;
                      const fCount = checks.filter(c => c.status === 'fail').length;
                      const summaryLine = [pCount && `${pCount} pass`, wCount && `${wCount} tight`, fCount && `${fCount} fail`].filter(Boolean).join(', ');
                      return (
                        <div key={cat} style={{ background: 'rgba(0,0,0,0.02)', border: '1px solid var(--color-border)', borderRadius: 8, padding: '12px 16px', marginBottom: 8 }}>
                          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span>{catEmoji[cat]}</span>
                            <span>{cat.toUpperCase()}</span>
                            <span style={{ color: 'var(--color-text-muted)', fontWeight: 500, fontSize: 11, marginLeft: 'auto' }}>{summaryLine}</span>
                          </div>
                          {checks.map((chk, ci) => (
                            <div key={ci} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '6px 0', borderBottom: ci < checks.length - 1 ? '1px solid rgba(0,0,0,0.04)' : 'none' }}>
                              <span style={{ color: statusColor(chk.status), fontSize: 15, minWidth: 20, lineHeight: '1.3' }}>{chk.icon}</span>
                              <span style={{ color: 'var(--color-text-secondary)', fontSize: 13, flex: 1, lineHeight: 1.5 }}>{chk.detail}</span>
                            </div>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* Helper: build structured parameter breakdown */
function buildBreakdown(form: VesselForm, berthLoa: number, berthDepth: number, berthBeam: number, cargoMatch: boolean, vesselTypeMatch: boolean, waitH: number, serviceH: number): ParameterCheck[] {
  const loaSlack = berthLoa - form.loa;
  const draftSlack = berthDepth - form.draft;
  const beamSlack = berthBeam - form.beam;
  const checks: ParameterCheck[] = [];

  // Physical Fit
  const loaStatus = loaSlack > 40 ? 'pass' : loaSlack > 10 ? 'ok' : loaSlack > 0 ? 'tight' : 'fail';
  checks.push({ category: 'Physical Fit', parameter: 'LOA', status: loaStatus, icon: loaStatus === 'fail' ? 'âŒ' : loaStatus === 'tight' ? 'âš ' : 'âœ”', detail: `LOA (${form.loa}m) ${loaSlack >= 0 ? 'fits within' : 'EXCEEDS'} berth limit (${berthLoa}m) â†’ ${loaSlack >= 0 ? `Safe margin: ${loaSlack}m` : `Over by ${Math.abs(loaSlack)}m`}`, compact: `LOA ${loaSlack >= 0 ? loaSlack + 'm margin' : 'OVER'}` });

  const draftStatus = draftSlack > 3 ? 'pass' : draftSlack > 1.5 ? 'ok' : draftSlack > 0 ? 'tight' : 'fail';
  checks.push({ category: 'Physical Fit', parameter: 'Draft', status: draftStatus, icon: draftStatus === 'fail' ? 'âŒ' : draftStatus === 'tight' ? 'âš ' : 'âœ”', detail: `Draft (${form.draft}m) vs berth depth (${berthDepth}m) â†’ UKC: ${draftSlack.toFixed(1)}m ${draftSlack < 1.5 ? '(below 1.5m minimum)' : ''}`, compact: `UKC ${draftSlack.toFixed(1)}m` });

  const beamStatus = beamSlack > 10 ? 'pass' : beamSlack > 3 ? 'ok' : beamSlack > 0 ? 'tight' : 'fail';
  checks.push({ category: 'Physical Fit', parameter: 'Beam', status: beamStatus, icon: beamStatus === 'fail' ? 'âŒ' : beamStatus === 'tight' ? 'âš ' : 'âœ”', detail: `Beam (${form.beam}m) vs berth max beam (${berthBeam}m) â†’ Clearance: ${beamSlack}m`, compact: `Beam ${beamSlack}m clear` });

  // Operational
  const cargoStatus = cargoMatch ? 'pass' : 'tight';
  checks.push({ category: 'Operational', parameter: 'Cargo Type', status: cargoStatus, icon: cargoMatch ? 'âœ”' : 'âš ', detail: cargoMatch ? `${form.cargo_type} is a primary cargo type handled at this berth` : `${form.cargo_type} requires equipment adaptation at this berth`, compact: cargoMatch ? 'Cargo matched' : 'Cargo needs adaptation' });

  const vtStatus = vesselTypeMatch ? 'pass' : 'tight';
  checks.push({ category: 'Operational', parameter: 'Vessel Type', status: vtStatus, icon: vesselTypeMatch ? 'âœ”' : 'âš ', detail: vesselTypeMatch ? `${form.vessel_type} is an allowed vessel type` : `${form.vessel_type} not primary type â€” may require operational adjustments`, compact: vesselTypeMatch ? 'Type matched' : 'Type mismatch' });

  // Performance
  const waitStatus = waitH < 3 ? 'pass' : waitH < 6 ? 'ok' : 'tight';
  checks.push({ category: 'Performance', parameter: 'Wait Time', status: waitStatus, icon: waitStatus === 'tight' ? 'âš ' : 'âœ”', detail: `Historical average wait: ${waitH.toFixed(1)}h ${waitH < 3 ? 'â€” excellent availability' : waitH < 6 ? 'â€” acceptable' : 'â€” above average'}`, compact: `Wait ${waitH.toFixed(1)}h` });

  checks.push({ category: 'Performance', parameter: 'Service Time', status: 'info', icon: 'â„¹', detail: `Historical average service: ${serviceH}h (derived from past operations, not used in ranking)`, compact: `Service ${serviceH}h` });

  // Commercial
  checks.push({ category: 'Commercial Impact', parameter: 'Cost Estimate', status: 'info', icon: 'â„¹', detail: `Estimated port charges based on vessel size and berth tariff category`, compact: 'Standard tariff' });

  return checks;
}

/* Sample data for demo (when backend is unavailable) */
function getSampleResults(form: VesselForm): BerthRecommendation[] {
  const vesselName = form.vessel_name || 'Vessel';
  const loaMarginB01 = 250 - form.loa;
  const loaMarginB02 = 300 - form.loa;
  const loaMarginB06 = 200 - form.loa;
  const draftClearB01 = 14.5 - form.draft;
  const draftClearB02 = 16.2 - form.draft;

  return [
    {
      rank: 1, berth_code: '2172', berth_name: 'Berth JD1',
      confidence: 87, expected_wait_hours: 2.5, expected_service_hours: 24, suitability_score: 92, risk_score: 8,
      timeline_start: 0, timeline_end: 26.5, compact_reason: `Best physical fit (LOA margin ${loaMarginB01}m, UKC ${draftClearB01.toFixed(1)}m) with ${form.cargo_type}-optimized infrastructure`,
      pros: [
        `Deep draft clearance of ${draftClearB01.toFixed(1)}m at 14.5m depth â€” all-tide access`,
        `Gantry Crane (45t) + Conveyor Belt optimized for ${form.cargo_type} at 1,200 TPH`,
        'Direct rail access for fast cargo evacuation',
      ],
      cons: ['Higher operating cost â€” $850/hr vs avg $620/hr'],
      explanation: `Best overall match â€” LOA/draft clearance excellent, ${form.cargo_type} handling infrastructure directly aligned.`,
      ai_reasoning: `DECISION ANALYSIS: ${vesselName} (${form.vessel_type}, ${form.loa}m LOA) evaluated against 7 berths. Berth JD1 scored highest: Physical fit â€” LOA margin ${loaMarginB01}m, UKC ${draftClearB01.toFixed(1)}m. Equipment â€” purpose-built for ${form.cargo_type}. Risk â€” 8%.`,
      structured_breakdown: buildBreakdown(form, 250, 14.5, 40, true, true, 2.5, 24),
      technical_score: 95, commercial_score: 88,
    },
    {
      rank: 2, berth_code: '21943', berth_name: 'Berth JD6',
      confidence: 73, expected_wait_hours: 4.2, expected_service_hours: 28, suitability_score: 81, risk_score: 15,
      timeline_start: 0, timeline_end: 32.2, compact_reason: `Deep channel (${draftClearB02.toFixed(1)}m UKC) but container-optimized â€” requires equipment adaptation`,
      pros: [
        `Generous draft margin ${draftClearB02.toFixed(1)}m at 16.2m`,
        `LOA margin of ${loaMarginB02}m â€” substantial clearance`,
      ],
      cons: [
        'Container vessel priority queue creates 4.2h wait',
        `STS Cranes container-optimized â€” ${form.cargo_type} needs mobile equipment`,
      ],
      explanation: `Strong secondary option â€” generous physical clearance but ${form.cargo_type} requires equipment adaptation.`,
      ai_reasoning: `Berth JD6 ranks #2 at 81% suitability. Deepest channel 16.2m, ${loaMarginB02}m LOA margin. Equipment mismatch for ${form.vessel_type} adds ~4h to service.`,
      structured_breakdown: buildBreakdown(form, 300, 16.2, 45, false, false, 4.2, 28),
      technical_score: 84, commercial_score: 78,
    },
    {
      rank: 3, berth_code: '2640', berth_name: 'Berth JD2',
      confidence: 58, expected_wait_hours: 1.0, expected_service_hours: 32, suitability_score: 68, risk_score: 25,
      timeline_start: 0, timeline_end: 33, compact_reason: 'Fastest availability (1h) but lower throughput and tight physical margins',
      pros: ['Available within 1h â€” fastest', 'Multi-purpose with Mobile Crane (40t)'],
      cons: [
        `LOA margin only ${loaMarginB06}m â€” ${loaMarginB06 < 10 ? 'tugboat mandatory' : 'tight'}`,
        `600 TPH throughput â€” ${form.cargo_type} ops ~${(form.cargo_tons / 600).toFixed(1)}h`,
      ],
      explanation: `Fastest availability but sub-optimal throughput for ${form.cargo_type}.`,
      ai_reasoning: `Berth JD2 ranks #3. Immediate availability, but 600TPH throughput adds significant service time. Draft UKC ${(11.5 - form.draft).toFixed(1)}m.`,
      structured_breakdown: buildBreakdown(form, 200, 11.5, 32, false, true, 1.0, 32),
      technical_score: 70, commercial_score: 65,
    },
  ];
}
