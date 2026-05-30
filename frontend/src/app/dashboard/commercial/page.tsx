/**
 * Commercial Intelligence Page
 * Migrated from ui/commercial_page.py — 4 tabs:
 * 1. Configuration & Scoring
 * 2. Partnership Manager
 * 3. Revenue Dashboard
 * 4. Learning Analytics
 */
'use client';

import { useState } from 'react';

/* --- Types --- */
interface ScoringForm {
  vessel_type: string;
  company: string;
  hazmat: boolean;
  cargo_quantity: number;
  cargo_size: string;
  service_hours: number;
  berth_codes: string;
  utilization: number;
}

interface BerthScore {
  berth_code: string;
  final_score: number;
  technical_score: number;
  commercial_score: number;
  strategic_score: number;
  net_revenue: number;
  profit_margin: number;
  revenue_tier: string;
  berth_class: string;
  pricing_note: string;
  discount_pct: number;
}

interface Partnership {
  company_id: string;
  display_name: string;
  tier: string;
  discount_pct: number;
  annual_value: number;
  is_contract: boolean;
  visits_per_year: number;
  contact: string;
  email: string;
}

interface BerthEcon {
  berth_code: string;
  berth_class: string;
  specialization: string;
  avg_revenue_per_call: number;
  profit_margin: number;
  operating_cost_per_hour: number;
  dynamic_price_adj: string;
  pricing_reason: string;
  est_revenue_now: number;
}

const TABS = ['🎛 Configuration & Scoring', '🤝 Partnership Manager', '📊 Revenue Dashboard', '📈 Learning Analytics'];
const TIER_COLORS: Record<string, string> = { VIP: '#f59e0b', PREMIUM: '#0ea5e9', STANDARD: '#64748b', STRATEGIC_PROSPECT: '#8b5cf6' };
const TIER_BADGES: Record<string, string> = { VIP: '👑 VIP', PREMIUM: '💎 PREMIUM', STANDARD: '📦 STANDARD', STRATEGIC_PROSPECT: '⭐ STRATEGIC' };
const REVENUE_COLORS: Record<string, string> = { HIGH: '#10b981', MEDIUM: '#f59e0b', LOW: '#ef4444' };

export default function CommercialPage() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <div>
      {/* --- Header --- */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <span className="text-2xl">💰</span>
          <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 22, color: 'var(--color-text-primary)' }}>
            Commercial Intelligence
          </h2>
          <span className="badge badge-success">COMMERCIAL AI</span>
        </div>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>
          Revenue optimization, partnership management & dynamic pricing
        </p>
      </div>

      {/* --- Tab Navigation --- */}
      <div className="flex gap-2 mb-6" style={{ borderBottom: '1px solid var(--color-dark-border)', paddingBottom: 12 }}>
        {TABS.map((tab, i) => (
          <button
            key={i}
            className={`rec-tab ${activeTab === i ? 'active' : ''}`}
            onClick={() => setActiveTab(i)}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* --- Tab 1: Configuration & Scoring --- */}
      {activeTab === 0 && <ScoringTab />}

      {/* --- Tab 2: Partnership Manager --- */}
      {activeTab === 1 && <PartnershipTab />}

      {/* --- Tab 3: Revenue Dashboard --- */}
      {activeTab === 2 && <RevenueTab />}

      {/* --- Tab 4: Learning Analytics --- */}
      {activeTab === 3 && <LearningTab />}
    </div>
  );
}

/* ===
   TAB 1: Configuration & Scoring
   === */
function ScoringTab() {
  const [config, setConfig] = useState({ commercial_flag: false, partnership: true, dynamic_pricing: true, mode: 'balanced' });
  const [form, setForm] = useState<ScoringForm>({
    vessel_type: 'Container', company: 'MAERSK', hazmat: false,
    cargo_quantity: 200, cargo_size: '40ft', service_hours: 36,
    berth_codes: 'CTB3\nCTB2\nCTB1\nJD5', utilization: 75,
  });
  const [results, setResults] = useState<BerthScore[] | null>(null);
  const [loading, setLoading] = useState(false);

  const modeDesc: Record<string, [string, string]> = {
    technical_only: ['Tech 50% • Constraints 50%', '#64748b'],
    balanced: ['Tech 35% • Revenue 25% • Partnership 20% • Constraints 20%', '#0ea5e9'],
    revenue_first: ['Tech 30% • Revenue 50% • Constraints 20%', '#10b981'],
    partnership_focused: ['Tech 25% • Partnership 40% • Revenue 15% • Constraints 20%', '#f59e0b'],
  };

  async function computeScores(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const token = localStorage.getItem('baos_access_token');
      const res = await fetch(`${apiUrl}/api/commercial/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(form),
      });
      if (!res.ok) { setResults(getSampleScores()); return; }
      setResults(await res.json());
    } catch {
      setResults(getSampleScores());
    } finally {
      setLoading(false);
    }
  }

  const [mdesc, mcolor] = modeDesc[config.mode] || ['', '#94a3b8'];
  const RANK_COLORS = ['#10b981', '#0ea5e9', '#8b5cf6', '#f59e0b'];

  return (
    <div>
      <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, marginBottom: 16 }}>⚙️ Commercial Decision Engine Configuration</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="space-y-3">
          {([
            ['commercial_flag', '🔥 Enable Commercial Intelligence'],
            ['partnership', '🤝 Partnership System'],
            ['dynamic_pricing', '⚡ Dynamic Pricing'],
          ] as [keyof typeof config, string][]).map(([key, label]) => (
            <label key={key} className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" checked={!!config[key]}
                disabled={key !== 'commercial_flag' && !config.commercial_flag}
                onChange={e => setConfig(prev => ({ ...prev, [key]: e.target.checked }))}
                style={{ width: 18, height: 18, accentColor: 'var(--color-primary)' }}
              />
              <span style={{ fontSize: 14, color: 'var(--color-text-secondary)' }}>{label}</span>
            </label>
          ))}
        </div>
        <div>
          <label className="block text-xs font-semibold mb-2" style={{ color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Decision Mode</label>
          {(['technical_only', 'balanced', 'revenue_first', 'partnership_focused'] as const).map(m => (
            <label key={m} className="flex items-center gap-2 mb-2 cursor-pointer">
              <input type="radio" name="mode" value={m} checked={config.mode === m}
                disabled={!config.commercial_flag}
                onChange={() => setConfig(prev => ({ ...prev, mode: m }))}
              />
              <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>
                {{ technical_only: '🔧 Technical Only', balanced: '⚖️ Balanced', revenue_first: '💰 Revenue First', partnership_focused: '🤝 Partnership Focused' }[m]}
              </span>
            </label>
          ))}
        </div>
        <div>
          {config.commercial_flag ? (
            <div style={{ background: `${mcolor}11`, border: `1px solid ${mcolor}33`, borderRadius: 8, padding: '10px 16px', fontSize: 12, color: mcolor }}>
              <strong>Weight breakdown:</strong> {mdesc}
            </div>
          ) : (
            <div className="card-flat" style={{ padding: 16, fontSize: 13, color: 'var(--color-text-muted)' }}>
              🔧 Commercial Intelligence is <strong>OFF</strong>. Enable the toggle to use revenue & partnership scoring.
            </div>
          )}
        </div>
      </div>

      <hr style={{ borderColor: 'var(--color-dark-border)', margin: '24px 0' }} />
      <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, marginBottom: 16 }}>🧪 Commercial Score Calculator</h3>

      <form onSubmit={computeScores}>
        <div className="card" style={{ padding: 20 }}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)' }}>Vessel Type</label>
                <select className="form-input" value={form.vessel_type} onChange={e => setForm(p => ({ ...p, vessel_type: e.target.value }))}>
                  {['Bulk Dry', 'Chemical', 'Container', 'General Cargo', 'Oil', 'Other Dry Cargo', 'Ro-Ro Cargo', 'Bulk Carrier', 'Crude Oil Tanker', 'Chemical Tanker', 'RoRo', 'LPG Tanker', 'LNG Tanker'].map(v => <option key={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)' }}>Shipping Company</label>
                <input className="form-input" value={form.company} onChange={e => setForm(p => ({ ...p, company: e.target.value }))} placeholder="MAERSK, SHELL, ONE..." />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.hazmat} onChange={e => setForm(p => ({ ...p, hazmat: e.target.checked }))} />
                <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>Hazmat Cargo</span>
              </label>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)' }}>Cargo Quantity</label>
                <input className="form-input" type="number" value={form.cargo_quantity} onChange={e => setForm(p => ({ ...p, cargo_quantity: +e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)' }}>Cargo Size</label>
                <select className="form-input" value={form.cargo_size} onChange={e => setForm(p => ({ ...p, cargo_size: e.target.value }))}>
                  {['20ft', '40ft', 'reefer', 'small', 'medium', 'large'].map(s => <option key={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)' }}>Service Hours</label>
                <input className="form-input" type="number" value={form.service_hours} onChange={e => setForm(p => ({ ...p, service_hours: +e.target.value }))} />
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)' }}>Berth Codes (one per line)</label>
                <textarea className="form-input" rows={4} value={form.berth_codes} onChange={e => setForm(p => ({ ...p, berth_codes: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)' }}>Current Berth Utilization %: {form.utilization}</label>
                <input type="range" className="w-full" min={0} max={100} value={form.utilization} onChange={e => setForm(p => ({ ...p, utilization: +e.target.value }))} />
              </div>
            </div>
          </div>
          <button type="submit" disabled={loading} className="btn btn-primary btn-lg w-full mt-6" style={{ fontWeight: 700 }}>
            {loading ? '⚙️ Computing...' : '⚡ Compute Commercial Scores'}
          </button>
        </div>
      </form>

      {/* Results */}
      {results && (
        <div style={{ marginTop: 24 }}>
          <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, marginBottom: 16 }}>🏗️ Berth Scores (Best First)</h4>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {results.map((r, i) => {
              const col = RANK_COLORS[i % RANK_COLORS.length];
              const revCol = REVENUE_COLORS[r.revenue_tier] || '#64748b';
              return (
                <div key={r.berth_code} style={{ border: '1px solid rgba(255,255,255,0.1)', borderTop: `3px solid ${col}`, borderRadius: 10, padding: 16 }}>
                  <div style={{ fontSize: 20, fontWeight: 800, color: col }}>#{i + 1} Berth {r.berth_code}</div>
                  <div style={{ fontSize: 32, fontWeight: 900, color: '#fff', margin: '6px 0' }}>
                    {r.final_score.toFixed(0)}<span style={{ fontSize: 14, color: '#94a3b8' }}>/100</span>
                  </div>
                  <div style={{ fontSize: 12, color: '#94a3b8', margin: '2px 0' }}>
                    Revenue: ${r.net_revenue.toLocaleString()}{' '}
                    <span style={{ background: `${revCol}22`, border: `1px solid ${revCol}`, borderRadius: 6, padding: '2px 8px', fontSize: 11, fontWeight: 700, color: revCol }}>{r.revenue_tier}</span>
                  </div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>Margin: {(r.profit_margin * 100).toFixed(0)}% | {r.berth_class}</div>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 8, borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 8 }}>
                    Tech: {r.technical_score.toFixed(0)} | Comm: {r.commercial_score.toFixed(0)} | Strat: {r.strategic_score.toFixed(0)}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Detailed table */}
          <details>
            <summary className="cursor-pointer" style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15, marginBottom: 12, color: 'var(--color-text-primary)' }}>
              📊 Detailed Breakdown Table
            </summary>
            <div className="card" style={{ padding: 0, overflow: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'rgba(255,255,255,0.03)' }}>
                    {['Berth', 'Final', 'Technical', 'Commercial', 'Strategic', 'Revenue', 'Margin', 'Tier', 'Discount'].map(h => (
                      <th key={h} style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', borderBottom: '1px solid var(--color-dark-border)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {results.map(r => (
                    <tr key={r.berth_code} style={{ borderBottom: '1px solid var(--color-dark-border)' }}>
                      <td style={{ padding: '10px 14px', fontWeight: 600 }}>{r.berth_code}</td>
                      <td style={{ padding: '10px 14px', fontWeight: 700 }}>{r.final_score.toFixed(1)}</td>
                      <td style={{ padding: '10px 14px' }}>{r.technical_score.toFixed(1)}</td>
                      <td style={{ padding: '10px 14px' }}>{r.commercial_score.toFixed(1)}</td>
                      <td style={{ padding: '10px 14px' }}>{r.strategic_score.toFixed(1)}</td>
                      <td style={{ padding: '10px 14px' }}>${r.net_revenue.toLocaleString()}</td>
                      <td style={{ padding: '10px 14px' }}>{(r.profit_margin * 100).toFixed(1)}%</td>
                      <td style={{ padding: '10px 14px' }}>{r.revenue_tier}</td>
                      <td style={{ padding: '10px 14px' }}>{r.discount_pct.toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}

/* ===
   TAB 2: Partnership Manager
   === */
function PartnershipTab() {
  const [lookupName, setLookupName] = useState('');
  const partners = getSamplePartners();
  const matched = lookupName ? partners.find(p => p.display_name.toLowerCase().includes(lookupName.toLowerCase())) || partners[0] : null;

  return (
    <div>
      <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, marginBottom: 16 }}>🔍 Company Quick Lookup</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div>
          <input className="form-input" placeholder="e.g. MAERSK, SHELL, MSC..." value={lookupName} onChange={e => setLookupName(e.target.value)} />
        </div>
        {matched && (
          <div className="md:col-span-2">
            <div style={{ background: `${TIER_COLORS[matched.tier]}11`, border: `1px solid ${TIER_COLORS[matched.tier]}33`, borderRadius: 10, padding: '16px 20px' }}>
              <div className="flex items-center justify-between mb-3">
                <span style={{ fontSize: 16, fontWeight: 800, color: '#fff' }}>{matched.display_name}</span>
                <span style={{ background: `${TIER_COLORS[matched.tier]}22`, border: `1px solid ${TIER_COLORS[matched.tier]}`, borderRadius: 6, padding: '2px 10px', fontSize: 11, fontWeight: 700, color: TIER_COLORS[matched.tier] }}>
                  {TIER_BADGES[matched.tier]}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2" style={{ fontSize: 12 }}>
                <div><span style={{ color: '#94a3b8' }}>Discount:</span> <strong style={{ color: '#10b981' }}>{matched.discount_pct}%</strong></div>
                <div><span style={{ color: '#94a3b8' }}>Annual Value:</span> <strong>${matched.annual_value.toLocaleString()}</strong></div>
                <div><span style={{ color: '#94a3b8' }}>Contract:</span> <strong>{matched.is_contract ? '✅ Active' : '❌ None'}</strong></div>
                <div><span style={{ color: '#94a3b8' }}>Visits/yr:</span> <strong>{matched.visits_per_year}</strong></div>
              </div>
              {matched.contact && (
                <div style={{ marginTop: 10, fontSize: 11, color: '#94a3b8' }}>Contact: {matched.contact}</div>
              )}
            </div>
          </div>
        )}
      </div>

      <hr style={{ borderColor: 'var(--color-dark-border)', margin: '24px 0' }} />
      <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, marginBottom: 16 }}>📋 All Partnerships</h3>
      <div className="card" style={{ padding: 0, overflow: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'rgba(255,255,255,0.03)' }}>
              {['Company', 'Tier', 'Discount', 'Annual Value', 'Contract', 'Visits/yr'].map(h => (
                <th key={h} style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', borderBottom: '1px solid var(--color-dark-border)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {partners.map((p) => (
              <tr key={p.company_id} style={{ borderBottom: '1px solid var(--color-dark-border)' }}>
                <td style={{ padding: '10px 14px', fontWeight: 600 }}>{p.display_name}</td>
                <td style={{ padding: '10px 14px' }}>
                  <span style={{ background: `${TIER_COLORS[p.tier]}22`, border: `1px solid ${TIER_COLORS[p.tier]}`, borderRadius: 6, padding: '2px 8px', fontSize: 11, fontWeight: 700, color: TIER_COLORS[p.tier] }}>{TIER_BADGES[p.tier]}</span>
                </td>
                <td style={{ padding: '10px 14px', color: '#10b981', fontWeight: 700 }}>{p.discount_pct}%</td>
                <td style={{ padding: '10px 14px' }}>${p.annual_value.toLocaleString()}</td>
                <td style={{ padding: '10px 14px' }}>{p.is_contract ? '✅' : '❌'}</td>
                <td style={{ padding: '10px 14px' }}>{p.visits_per_year}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ===
   TAB 3: Revenue Dashboard
   === */
function RevenueTab() {
  const [utilPct, setUtilPct] = useState(78);
  const econ = getSampleBerthEcon(utilPct);
  const premiumCount = econ.filter(e => e.berth_class === 'PREMIUM').length;
  const avgRev = econ.reduce((s, e) => s + e.avg_revenue_per_call, 0) / econ.length;
  const avgMargin = econ.reduce((s, e) => s + e.profit_margin, 0) / econ.length;

  return (
    <div>
      <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, marginBottom: 16 }}>⚡ Real-Time Utilization & Pricing</h3>
      <div className="grid grid-cols-2 gap-6 mb-6">
        <div>
          <label className="block text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)' }}>Cluster Utilization %: {utilPct}</label>
          <input type="range" className="w-full" min={0} max={100} value={utilPct} onChange={e => setUtilPct(+e.target.value)} />
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { icon: '🏗️', value: `${econ.length}`, label: 'Berths Configured' },
          { icon: '⭐', value: `${premiumCount}`, label: 'Premium Berths', color: '#f59e0b' },
          { icon: '💵', value: `$${avgRev.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, label: 'Avg Revenue/Call', color: '#10b981' },
          { icon: '📈', value: `${(avgMargin * 100).toFixed(0)}%`, label: 'Avg Profit Margin' },
        ].map((kpi, i) => (
          <div key={i} className="card-flat text-center" style={{ padding: 14 }}>
            <div style={{ fontSize: 18 }}>{kpi.icon}</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: kpi.color || 'var(--color-text-primary)', fontFamily: 'var(--font-display)' }}>{kpi.value}</div>
            <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{kpi.label}</div>
          </div>
        ))}
      </div>

      {/* Berth Economics Table */}
      <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, marginBottom: 16 }}>🏗️ Berth Economics & Pricing</h3>
      <div className="card mb-8" style={{ padding: 0, overflow: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'rgba(255,255,255,0.03)' }}>
              {['Berth', 'Class', 'Type', 'Avg Rev/Call', `Est. Rev Now`, 'Margin', 'Op. Cost/hr', `Price @ ${utilPct}%`, 'Reason'].map(h => (
                <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: 'var(--color-text-muted)', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', borderBottom: '1px solid var(--color-dark-border)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {econ.map(e => (
              <tr key={e.berth_code} style={{ borderBottom: '1px solid var(--color-dark-border)' }}>
                <td style={{ padding: '10px 12px', fontWeight: 600 }}>{e.berth_code}</td>
                <td style={{ padding: '10px 12px' }}>{e.berth_class}</td>
                <td style={{ padding: '10px 12px' }}>{e.specialization}</td>
                <td style={{ padding: '10px 12px' }}>${e.avg_revenue_per_call.toLocaleString()}</td>
                <td style={{ padding: '10px 12px', color: '#10b981', fontWeight: 700 }}>${e.est_revenue_now.toLocaleString()}</td>
                <td style={{ padding: '10px 12px' }}>{(e.profit_margin * 100).toFixed(0)}%</td>
                <td style={{ padding: '10px 12px' }}>${e.operating_cost_per_hour.toLocaleString()}</td>
                <td style={{ padding: '10px 12px', color: e.dynamic_price_adj.startsWith('+') ? '#10b981' : 'var(--color-text-secondary)' }}>{e.dynamic_price_adj}</td>
                <td style={{ padding: '10px 12px', fontSize: 11, color: 'var(--color-text-muted)' }}>{e.pricing_reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Revenue Tier Breakdown */}
      <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, marginBottom: 16 }}>💰 Revenue Tier Breakdown</h3>
      <div className="grid grid-cols-3 gap-4">
        {([
          ['HIGH Revenue', econ.filter(e => e.avg_revenue_per_call >= 100000), '#10b981'],
          ['MEDIUM Revenue', econ.filter(e => e.avg_revenue_per_call >= 50000 && e.avg_revenue_per_call < 100000), '#f59e0b'],
          ['LOW Revenue', econ.filter(e => e.avg_revenue_per_call < 50000), '#ef4444'],
        ] as [string, BerthEcon[], string][]).map(([label, berths, color]) => (
          <div key={label} style={{ background: `${color}11`, border: `1px solid ${color}33`, borderRadius: 10, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 11, color, fontWeight: 700, textTransform: 'uppercase' }}>{label}</div>
            <div style={{ fontSize: 28, fontWeight: 900, color }}>{berths.length}</div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>{berths.map(b => b.berth_code).join(', ') || 'None'}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ===
   TAB 4: Learning Analytics
   === */
function LearningTab() {
  return (
    <div>
      <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 17, marginBottom: 16 }}>📈 Learning Analytics</h3>
      <div className="card" style={{ padding: 24, textAlign: 'center' }}>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 14, marginBottom: 16 }}>
          No commercial assignments recorded yet. Assignments are logged automatically when commercial-scored recommendations are made.
        </p>
        <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15, marginBottom: 16 }}>📊 Dashboard Preview (Sample Metrics)</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { icon: '📊', value: '—', label: 'Total Assignments' },
            { icon: '🎯', value: '—', label: 'Revenue Accuracy' },
            { icon: '✅', value: '—', label: 'SLA Compliance (VIP)' },
            { icon: '💰', value: '—', label: 'Avg Predicted Revenue' },
          ].map((kpi, i) => (
            <div key={i} className="card-flat text-center" style={{ padding: 14 }}>
              <div style={{ fontSize: 18 }}>{kpi.icon}</div>
              <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--color-text-primary)' }}>{kpi.value}</div>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{kpi.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* --- Sample Data Functions --- */
function getSampleScores(): BerthScore[] {
  return [
    { berth_code: 'CTB3', final_score: 88, technical_score: 80, commercial_score: 92, strategic_score: 85, net_revenue: 145000, profit_margin: 0.38, revenue_tier: 'HIGH', berth_class: 'PREMIUM', pricing_note: 'Peak demand surcharge', discount_pct: 15 },
    { berth_code: 'CTB2', final_score: 82, technical_score: 80, commercial_score: 85, strategic_score: 78, net_revenue: 128000, profit_margin: 0.32, revenue_tier: 'HIGH', berth_class: 'PREMIUM', pricing_note: 'Standard rate', discount_pct: 15 },
    { berth_code: 'CTB1', final_score: 75, technical_score: 80, commercial_score: 72, strategic_score: 68, net_revenue: 95000, profit_margin: 0.25, revenue_tier: 'MEDIUM', berth_class: 'STANDARD', pricing_note: 'Standard rate', discount_pct: 15 },
    { berth_code: 'JD5', final_score: 62, technical_score: 80, commercial_score: 55, strategic_score: 48, net_revenue: 42000, profit_margin: 0.18, revenue_tier: 'LOW', berth_class: 'ECONOMY', pricing_note: 'Off-peak discount', discount_pct: 15 },
  ];
}

function getSamplePartners(): Partnership[] {
  return [
    { company_id: 'MAERSK', display_name: 'Maersk Line', tier: 'VIP', discount_pct: 15, annual_value: 12000000, is_contract: true, visits_per_year: 240, contact: 'S. Jensen (VP Ops)', email: 'ops@maersk.com' },
    { company_id: 'MSC', display_name: 'MSC Mediterranean', tier: 'VIP', discount_pct: 12, annual_value: 9500000, is_contract: true, visits_per_year: 180, contact: 'M. Rossi (Dir.)', email: 'port@msc.com' },
    { company_id: 'ONE', display_name: 'Ocean Network Express', tier: 'PREMIUM', discount_pct: 8, annual_value: 4200000, is_contract: true, visits_per_year: 96, contact: 'T. Yamada', email: 'ops@one-line.com' },
    { company_id: 'EVERGREEN', display_name: 'Evergreen Marine', tier: 'PREMIUM', discount_pct: 7, annual_value: 3800000, is_contract: true, visits_per_year: 72, contact: 'C. Lin', email: 'ops@evergreen.com' },
    { company_id: 'SHELL', display_name: 'Shell Tankers', tier: 'STRATEGIC_PROSPECT', discount_pct: 5, annual_value: 0, is_contract: false, visits_per_year: 24, contact: 'J. Brown', email: '' },
    { company_id: 'LOCAL', display_name: 'Local Coastal Shipping', tier: 'STANDARD', discount_pct: 0, annual_value: 0, is_contract: false, visits_per_year: 48, contact: '', email: '' },
  ];
}

function getSampleBerthEcon(util: number): BerthEcon[] {
  const mult = util > 85 ? 1.15 : util > 70 ? 1.0 : 0.92;
  return [
    { berth_code: 'CTB3', berth_class: 'PREMIUM', specialization: 'Container', avg_revenue_per_call: 145000, profit_margin: 0.38, operating_cost_per_hour: 850, dynamic_price_adj: mult > 1 ? `+${((mult - 1) * 100).toFixed(1)}%` : 'Standard', pricing_reason: mult > 1 ? 'High demand surcharge' : 'Normal pricing', est_revenue_now: Math.round(145000 * mult) },
    { berth_code: 'CTB2', berth_class: 'PREMIUM', specialization: 'Container', avg_revenue_per_call: 128000, profit_margin: 0.32, operating_cost_per_hour: 780, dynamic_price_adj: mult > 1 ? `+${((mult - 1) * 100).toFixed(1)}%` : 'Standard', pricing_reason: mult > 1 ? 'High demand surcharge' : 'Normal pricing', est_revenue_now: Math.round(128000 * mult) },
    { berth_code: 'CTB1', berth_class: 'STANDARD', specialization: 'Container', avg_revenue_per_call: 95000, profit_margin: 0.25, operating_cost_per_hour: 620, dynamic_price_adj: 'Standard', pricing_reason: 'Normal pricing', est_revenue_now: Math.round(95000 * mult) },
    { berth_code: 'JD5', berth_class: 'STANDARD', specialization: 'Bulk', avg_revenue_per_call: 68000, profit_margin: 0.22, operating_cost_per_hour: 480, dynamic_price_adj: mult < 1 ? `${((mult - 1) * 100).toFixed(1)}%` : 'Standard', pricing_reason: mult < 1 ? 'Low demand discount' : 'Normal pricing', est_revenue_now: Math.round(68000 * mult) },
    { berth_code: 'OT1', berth_class: 'PREMIUM', specialization: 'Tanker', avg_revenue_per_call: 185000, profit_margin: 0.42, operating_cost_per_hour: 1200, dynamic_price_adj: mult > 1 ? `+${((mult - 1) * 100).toFixed(1)}%` : 'Standard', pricing_reason: mult > 1 ? 'High demand surcharge' : 'Normal pricing', est_revenue_now: Math.round(185000 * mult) },
    { berth_code: 'GP2', berth_class: 'ECONOMY', specialization: 'General', avg_revenue_per_call: 32000, profit_margin: 0.15, operating_cost_per_hour: 320, dynamic_price_adj: 'Standard', pricing_reason: 'Normal pricing', est_revenue_now: Math.round(32000 * mult) },
  ];
}

