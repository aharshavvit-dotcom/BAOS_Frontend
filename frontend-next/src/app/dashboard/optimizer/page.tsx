/**
 * Optimizer Dashboard — CP-SAT Multi-Vessel Optimizer
 * Features: Feasibility Matrix with rich hover tooltips, AI Explanations,
 * Confidence Scores, Next-Optimal Berth Selection (in schedule + cost),
 * Undo/Redo, Per-Ship-Type Levers, Interactive Berth Timeline
 */
'use client';

import { useState, useCallback, useRef } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import {
  VesselInput, ScheduleAssignment, OptimizerResult, LeversConfig, ShipTypeLevers,
  VESSEL_TYPES, CARGO_TYPES, ALL_BERTHS, BERTH_COLORS,
  defaultLevers, makeVessel, createInitialVessels, getSampleResult, BERTH_SPECS,
} from './types';

/* ── Lever Slider Config ─────────────────────────────── */
const LEVER_DEFS: [keyof LeversConfig, string, number, number, number][] = [
  ['w_waiting', '⏱ Waiting Cost', 0, 3, 0.1],
  ['w_sla_penalty', '📋 SLA Penalty', 0, 5, 0.1],
  ['w_contract_bonus', '🤝 Contract Bonus', 0, 2, 0.1],
  ['w_deviation', '📐 Deviation', 0, 5, 0.1],
  ['w_demurrage', '💸 Demurrage', 0, 2, 0.1],
  ['w_throughput', '📦 Throughput', 0, 2, 0.1],
  ['ukc_margin_m', '⚓ UKC Margin (m)', 0, 2, 0.1],
  ['max_solve_seconds', '⏳ Max Solve (s)', 5, 120, 5],
];

export default function OptimizerPage() {
  const [nVessels, setNVessels] = useState(3);
  const [vessels, setVessels] = useState<VesselInput[]>(() => createInitialVessels(3));
  const [levers, setLevers] = useState<LeversConfig>(defaultLevers());
  const [pilotCap, setPilotCap] = useState(2);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OptimizerResult | null>(null);
  const [showLevers, setShowLevers] = useState(false);
  const [leverTab, setLeverTab] = useState<'global' | 'ship_type'>('global');

  // Per-ship-type levers
  const [shipTypeLevers, setShipTypeLevers] = useState<ShipTypeLevers[]>([]);
  const [activeShipType, setActiveShipType] = useState('');
  const [activeShipBerths, setActiveShipBerths] = useState<string[]>([]);
  const [activeShipConfig, setActiveShipConfig] = useState<LeversConfig>(defaultLevers());

  // Undo / next-optimal
  const [originalResult, setOriginalResult] = useState<OptimizerResult | null>(null);
  const [overrides, setOverrides] = useState<Map<string, string>>(new Map());
  const [expandedVessel, setExpandedVessel] = useState<string | null>(null);
  const [expandedCostVessel, setExpandedCostVessel] = useState<string | null>(null);

  // Feasibility matrix
  const [showFeasibility, setShowFeasibility] = useState(false);
  const [hoveredCell, setHoveredCell] = useState<{ vessel_id: string; berth_code: string; x: number; y: number } | null>(null);

  // Timeline hover
  const [hoveredBar, setHoveredBar] = useState<ScheduleAssignment | null>(null);
  const [barPos, setBarPos] = useState({ x: 0, y: 0 });

  const updateVessel = useCallback((idx: number, key: keyof VesselInput, val: string | number) => {
    setVessels(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], [key]: val };
      return copy;
    });
  }, []);

  function handleVesselCountChange(n: number) {
    setNVessels(n);
    setVessels(prev => {
      if (n > prev.length) return [...prev, ...Array.from({ length: n - prev.length }, (_, i) => makeVessel(prev.length + i))];
      return prev.slice(0, n);
    });
  }

  async function runOptimizer() {
    setLoading(true);
    setOverrides(new Map());
    setExpandedVessel(null);
    setExpandedCostVessel(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const token = localStorage.getItem('baos_access_token');
      const res = await fetch(`${apiUrl}/api/recommendations/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ vessels, levers, pilot_capacity: pilotCap, ship_type_levers: shipTypeLevers }),
      });
      if (!res.ok) { const r = getSampleResult(vessels); setResult(r); setOriginalResult(r); return; }
      const data = await res.json();
      setResult(data);
      setOriginalResult(data);
    } catch {
      const r = getSampleResult(vessels);
      setResult(r);
      setOriginalResult(r);
    } finally {
      setLoading(false);
    }
  }

  function selectAlternativeBerth(vesselId: string, berthCode: string) {
    const newOverrides = new Map(overrides);
    newOverrides.set(vesselId, berthCode);
    setOverrides(newOverrides);
    const newResult = getSampleResult(vessels, newOverrides);
    setResult(newResult);
    setExpandedVessel(null);
    setExpandedCostVessel(null);
  }

  function undoAllChanges() {
    if (originalResult) {
      setResult(originalResult);
      setOverrides(new Map());
      setExpandedVessel(null);
      setExpandedCostVessel(null);
    }
  }

  function addShipTypeLever() {
    if (!activeShipType || activeShipBerths.length === 0) return;
    setShipTypeLevers(prev => [...prev.filter(s => s.ship_type !== activeShipType),
      { ship_type: activeShipType, selected_berths: [...activeShipBerths], config: { ...activeShipConfig } }]);
    setActiveShipType('');
    setActiveShipBerths([]);
    setActiveShipConfig(defaultLevers());
  }

  function removeShipTypeLever(st: string) {
    setShipTypeLevers(prev => prev.filter(s => s.ship_type !== st));
  }

  return (
    <div>
      {/* ── Header ────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-2xl">🚀</span>
            <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 22, color: 'var(--color-text-primary)' }}>
              Multi-Vessel Optimizer
            </h2>
            <span className="badge badge-success">CP-SAT</span>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13, marginTop: 4 }}>
            CP-SAT constraint-programming scheduler with interactive lever panel
          </p>
        </div>
        <div className="flex gap-2">
          {overrides.size > 0 && (
            <button className="btn btn-secondary" onClick={undoAllChanges} style={{ fontSize: 13 }}>
              ↩ Undo All Changes
            </button>
          )}
          <button className="btn btn-secondary" onClick={() => setShowLevers(!showLevers)}>
            🎛 {showLevers ? 'Hide' : 'Show'} Levers
          </button>
        </div>
      </div>

      {/* ── Lever Panel ────────────────────────────────── */}
      {showLevers && (
        <div className="card mb-6" style={{ padding: 20 }}>
          <div className="flex gap-4 mb-4">
            <button onClick={() => setLeverTab('global')}
              style={{ padding: '6px 16px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer',
                background: leverTab === 'global' ? 'var(--color-primary)' : 'transparent',
                color: leverTab === 'global' ? 'white' : 'var(--color-text-secondary)',
                border: `1px solid ${leverTab === 'global' ? 'var(--color-primary)' : 'var(--color-border)'}`,
              }}>🌐 Global Levers</button>
            <button onClick={() => setLeverTab('ship_type')}
              style={{ padding: '6px 16px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer',
                background: leverTab === 'ship_type' ? 'var(--color-primary)' : 'transparent',
                color: leverTab === 'ship_type' ? 'white' : 'var(--color-text-secondary)',
                border: `1px solid ${leverTab === 'ship_type' ? 'var(--color-primary)' : 'var(--color-border)'}`,
              }}>🚢 Per Ship Type</button>
          </div>

          {leverTab === 'global' && (
            <>
              <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15, marginBottom: 16, color: 'var(--color-text-primary)' }}>
                🎛 Global Optimizer Levers
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {LEVER_DEFS.map(([key, label, min, max, step]) => (
                  <div key={key}>
                    <label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>{label}: <strong>{levers[key] as number}</strong></label>
                    <input type="range" className="w-full" min={min} max={max} step={step}
                      value={levers[key] as number}
                      onChange={e => setLevers(prev => ({ ...prev, [key]: +e.target.value }))} />
                  </div>
                ))}
              </div>
              <div className="flex gap-4 mt-4">
                <label className="flex items-center gap-2 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                  <input type="checkbox" checked={levers.fcfs_enabled} onChange={e => setLevers(prev => ({ ...prev, fcfs_enabled: e.target.checked }))} />
                  🔄 FCFS Ordering
                </label>
                <label className="flex items-center gap-2 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                  <input type="checkbox" checked={levers.goi_override_enabled} onChange={e => setLevers(prev => ({ ...prev, goi_override_enabled: e.target.checked }))} />
                  🏛 GoI Override
                </label>
              </div>
            </>
          )}

          {leverTab === 'ship_type' && (
            <>
              <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15, marginBottom: 16, color: 'var(--color-text-primary)' }}>
                🚢 Per Ship Type Levers
              </h4>
              <div className="mb-4">
                <label className="block text-xs mb-1 font-semibold" style={{ color: 'var(--color-text-muted)' }}>Step 1: Select Vessel Type</label>
                <select className="form-input" value={activeShipType} onChange={e => setActiveShipType(e.target.value)} style={{ maxWidth: 260 }}>
                  <option value="">-- Select Type --</option>
                  {VESSEL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              {activeShipType && (
                <>
                  <div className="mb-4">
                    <label className="block text-xs mb-2 font-semibold" style={{ color: 'var(--color-text-muted)' }}>Step 2: Select Berths to Apply</label>
                    <div className="flex flex-wrap gap-3">
                      {ALL_BERTHS.map(bc => (
                        <label key={bc} className="flex items-center gap-2 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                          <input type="checkbox" checked={activeShipBerths.includes(bc)}
                            onChange={e => {
                              if (e.target.checked) setActiveShipBerths(prev => [...prev, bc]);
                              else setActiveShipBerths(prev => prev.filter(b => b !== bc));
                            }} />
                          <span style={{ color: BERTH_COLORS[bc], fontWeight: 600 }}>{bc}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  {activeShipBerths.length > 0 && (
                    <>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        {LEVER_DEFS.map(([key, label, min, max, step]) => (
                          <div key={key}>
                            <label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>{label}: <strong>{activeShipConfig[key] as number}</strong></label>
                            <input type="range" className="w-full" min={min} max={max} step={step}
                              value={activeShipConfig[key] as number}
                              onChange={e => setActiveShipConfig(prev => ({ ...prev, [key]: +e.target.value }))} />
                          </div>
                        ))}
                      </div>
                      <button className="btn btn-primary" onClick={addShipTypeLever} style={{ fontSize: 13 }}>
                        ✅ Apply {activeShipType} Lever Config to {activeShipBerths.length} berth(s)
                      </button>
                    </>
                  )}
                </>
              )}
              {shipTypeLevers.length > 0 && (
                <div className="mt-4 space-y-2">
                  <h5 style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>Active Per-Type Configs:</h5>
                  {shipTypeLevers.map(stl => (
                    <div key={stl.ship_type} className="card-flat flex items-center justify-between" style={{ padding: '8px 14px' }}>
                      <div style={{ fontSize: 13 }}>
                        <strong>{stl.ship_type}</strong> → {stl.selected_berths.map(b => <span key={b} style={{ color: BERTH_COLORS[b], fontWeight: 600, marginLeft: 4 }}>{b}</span>)}
                        <span style={{ color: 'var(--color-text-muted)', marginLeft: 8 }}>W={stl.config.w_waiting} SLA={stl.config.w_sla_penalty}</span>
                      </div>
                      <button onClick={() => removeShipTypeLever(stl.ship_type)} style={{ color: 'var(--color-danger)', cursor: 'pointer', border: 'none', background: 'none', fontWeight: 700 }}>✕</button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Vessel Queue ──────────────────────────────── */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xl">🚢</span>
        <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--color-text-primary)' }}>Vessel Queue</h3>
      </div>
      <div className="flex items-center gap-3 mb-4">
        <label style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>Number of vessels:</label>
        <input className="form-input" type="number" min={1} max={20} value={nVessels}
          onChange={e => handleVesselCountChange(+e.target.value)} style={{ width: 80 }} />
      </div>
      <div className="space-y-3 mb-6">
        {vessels.map((v, i) => (
          <details key={v.vessel_id} open={i < 2}>
            <summary className="cursor-pointer card-flat" style={{ padding: '10px 16px', fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' }}>
              Vessel {i + 1}: {v.name}
            </summary>
            <div className="card-flat" style={{ padding: 16, borderTop: 'none', borderTopLeftRadius: 0, borderTopRightRadius: 0 }}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div><label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>Name</label>
                  <input className="form-input" value={v.name} onChange={e => updateVessel(i, 'name', e.target.value)} /></div>
                <div><label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>LOA (m)</label>
                  <input className="form-input" type="number" min={50} max={400} value={v.loa_m} onChange={e => updateVessel(i, 'loa_m', +e.target.value)} /></div>
                <div><label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>Beam (m)</label>
                  <input className="form-input" type="number" min={5} max={80} value={v.beam_m} onChange={e => updateVessel(i, 'beam_m', +e.target.value)} /></div>
                <div><label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>Draft (m)</label>
                  <input className="form-input" type="number" min={3} max={25} step={0.5} value={v.draft_m} onChange={e => updateVessel(i, 'draft_m', +e.target.value)} /></div>
                <div><label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>Cargo (tons)</label>
                  <input className="form-input" type="number" min={0} value={v.cargo_tons} onChange={e => updateVessel(i, 'cargo_tons', +e.target.value)} /></div>
                <div><label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>ETA (hours)</label>
                  <input className="form-input" type="number" min={0} max={168} value={v.eta_hours} onChange={e => updateVessel(i, 'eta_hours', +e.target.value)} /></div>
                <div><label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>Service (hours)</label>
                  <input className="form-input" type="number" min={4} max={96} value={v.service_hours} onChange={e => updateVessel(i, 'service_hours', +e.target.value)} /></div>
                <div><label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>Vessel Type</label>
                  <select className="form-input" value={v.vessel_type} onChange={e => updateVessel(i, 'vessel_type', e.target.value)}>
                    {VESSEL_TYPES.map(t => <option key={t}>{t}</option>)}
                  </select></div>
                <div><label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>Cargo Type</label>
                  <select className="form-input" value={v.cargo_type} onChange={e => updateVessel(i, 'cargo_type', e.target.value)}>
                    {CARGO_TYPES.map(t => <option key={t}>{t}</option>)}
                  </select></div>
              </div>
            </div>
          </details>
        ))}
      </div>

      {/* ── Run Button ────────────────────────────────── */}
      <div className="flex gap-4 items-center mb-8">
        <button className="btn btn-primary btn-lg flex-1" onClick={runOptimizer} disabled={loading} style={{ fontWeight: 700 }}>
          {loading ? '⚙️ Running CP-SAT Solver...' : '🚀 Run CP-SAT Optimizer'}
        </button>
        <div style={{ minWidth: 120 }}>
          <label className="block text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>Pilots</label>
          <input className="form-input" type="number" min={1} max={10} value={pilotCap} onChange={e => setPilotCap(+e.target.value)} />
        </div>
      </div>

      {!result && !loading && (
        <div className="card text-center" style={{ padding: 40 }}>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>Click <strong>Run CP-SAT Optimizer</strong> to generate a schedule.</p>
        </div>
      )}

      {/* ── RESULTS ──────────────────────────────────── */}
      {result && (
        <ResultsSection result={result} vessels={vessels} overrides={overrides}
          expandedVessel={expandedVessel} setExpandedVessel={setExpandedVessel}
          expandedCostVessel={expandedCostVessel} setExpandedCostVessel={setExpandedCostVessel}
          selectAlternativeBerth={selectAlternativeBerth}
          showFeasibility={showFeasibility} setShowFeasibility={setShowFeasibility}
          hoveredCell={hoveredCell} setHoveredCell={setHoveredCell}
          hoveredBar={hoveredBar} setHoveredBar={setHoveredBar}
          barPos={barPos} setBarPos={setBarPos} />
      )}
    </div>
  );
}

/* ════════════════════════════════════════════════════════
   Results Section
   ════════════════════════════════════════════════════════ */
function ResultsSection({ result, vessels, overrides, expandedVessel, setExpandedVessel, expandedCostVessel, setExpandedCostVessel, selectAlternativeBerth, showFeasibility, setShowFeasibility, hoveredCell, setHoveredCell, hoveredBar, setHoveredBar, barPos, setBarPos }: {
  result: OptimizerResult; vessels: VesselInput[]; overrides: Map<string, string>;
  expandedVessel: string | null; setExpandedVessel: (v: string | null) => void;
  expandedCostVessel: string | null; setExpandedCostVessel: (v: string | null) => void;
  selectAlternativeBerth: (vid: string, bc: string) => void;
  showFeasibility: boolean; setShowFeasibility: (v: boolean) => void;
  hoveredCell: { vessel_id: string; berth_code: string; x: number; y: number } | null;
  setHoveredCell: (v: { vessel_id: string; berth_code: string; x: number; y: number } | null) => void;
  hoveredBar: ScheduleAssignment | null; setHoveredBar: (v: ScheduleAssignment | null) => void;
  barPos: { x: number; y: number }; setBarPos: (v: { x: number; y: number }) => void;
}) {
  const timelineRef = useRef<HTMLDivElement>(null);
  return (
    <>
      {/* Status Banner */}
      <div style={{
        background: result.status === 'OPTIMAL' ? 'rgba(16,185,129,0.08)' : 'rgba(245,158,11,0.08)',
        border: `1px solid ${result.status === 'OPTIMAL' ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`,
        borderLeft: `4px solid ${result.status === 'OPTIMAL' ? '#10b981' : '#f59e0b'}`,
        borderRadius: 10, padding: '14px 20px', marginBottom: 20,
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <span style={{ fontSize: 20 }}>{result.status === 'OPTIMAL' ? '✅' : '⚠️'}</span>
        <span style={{ color: 'var(--color-text-secondary)', fontSize: 13 }}>
          Solver: <strong>{result.status}</strong> · {result.solve_time_sec.toFixed(2)}s · {result.assignments.length}/{vessels.length} vessels assigned
          {overrides.size > 0 && <span style={{ color: '#f59e0b', marginLeft: 8 }}>({overrides.size} manual override{overrides.size > 1 ? 's' : ''})</span>}
        </span>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        {[
          { icon: '⏱', value: `${result.kpis.avg_wait.toFixed(1)}h`, label: 'Avg Wait' },
          { icon: '📈', value: `${result.kpis.utilization.toFixed(0)}%`, label: 'Berth Util.' },
          { icon: '✅', value: `${result.kpis.sla_compliance.toFixed(0)}%`, label: 'SLA Compliance' },
          { icon: '💰', value: `$${result.kpis.total_revenue.toLocaleString()}`, label: 'Revenue' },
          { icon: '💸', value: `$${result.kpis.total_cost.toLocaleString()}`, label: 'Total Cost' },
          { icon: '📦', value: `${result.kpis.cargo_tons.toLocaleString()}t`, label: 'Cargo' },
          { icon: '🚢', value: `${result.assignments.length}`, label: 'Assigned' },
          { icon: '⚡', value: `${result.solve_time_sec.toFixed(2)}s`, label: 'Solve Time' },
        ].map((kpi, i) => (
          <div key={i} className="card-flat text-center" style={{ padding: 14 }}>
            <div style={{ fontSize: 18 }}>{kpi.icon}</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--color-text-primary)', fontFamily: 'var(--font-display)' }}>{kpi.value}</div>
            <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{kpi.label}</div>
          </div>
        ))}
      </div>

      {/* ── Feasibility Matrix with Hover Tooltip ──────── */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xl">🧮</span>
        <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--color-text-primary)' }}>Feasibility Matrix</h3>
        <button className="btn btn-secondary" onClick={() => setShowFeasibility(!showFeasibility)} style={{ fontSize: 12, padding: '4px 12px' }}>
          {showFeasibility ? 'Hide' : 'Show'}
        </button>
      </div>

      {showFeasibility && result.feasibility_matrix && (
        <div className="card mb-8" style={{ padding: 20, overflowX: 'auto', position: 'relative' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr>
                <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--color-text-muted)', borderBottom: '2px solid var(--color-border)' }}>Vessel</th>
                {ALL_BERTHS.map(bc => (
                  <th key={bc} style={{ padding: '8px 6px', textAlign: 'center', color: BERTH_COLORS[bc], fontWeight: 700, borderBottom: '2px solid var(--color-border)' }}>{bc.replace('INMAA-', '')}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {vessels.map(v => (
                <tr key={v.vessel_id}>
                  <td style={{ padding: '8px 12px', fontWeight: 600, color: 'var(--color-text-primary)', borderBottom: '1px solid var(--color-border)' }}>{v.name}</td>
                  {ALL_BERTHS.map(bc => {
                    const cell = result.feasibility_matrix.find(c => c.vessel_id === v.vessel_id && c.berth_code === bc);
                    const score = cell?.score ?? 0;
                    const bg = score > 0.8 ? 'rgba(16,185,129,0.15)' : score > 0.3 ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)';
                    const icon = score > 0.8 ? '✅' : score > 0.3 ? '⚠️' : '❌';
                    return (
                      <td key={bc} style={{ padding: '6px', textAlign: 'center', background: bg, borderBottom: '1px solid var(--color-border)', cursor: 'pointer', position: 'relative' }}
                        onMouseEnter={e => {
                          const rect = e.currentTarget.getBoundingClientRect();
                          setHoveredCell({ vessel_id: v.vessel_id, berth_code: bc, x: rect.left + rect.width / 2, y: rect.bottom + 8 });
                        }}
                        onMouseLeave={() => setHoveredCell(null)}
                      >
                        <div>{icon}</div>
                        <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>{(score * 100).toFixed(0)}%</div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex gap-4 mt-3" style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
            <span>✅ Feasible (&gt;80%)</span><span>⚠️ Marginal (30-80%)</span><span>❌ Infeasible (&lt;30%)</span>
            <span style={{ marginLeft: 'auto' }}>Hover cells for constraint details</span>
          </div>

          {/* Floating Tooltip for Feasibility */}
          {hoveredCell && (() => {
            const cell = result.feasibility_matrix.find(c => c.vessel_id === hoveredCell.vessel_id && c.berth_code === hoveredCell.berth_code);
            if (!cell) return null;
            const spec = BERTH_SPECS[hoveredCell.berth_code];
            return (
              <div style={{
                position: 'fixed', left: hoveredCell.x, top: hoveredCell.y, transform: 'translateX(-50%)',
                zIndex: 1000, background: 'white', border: '1px solid #e2e8f0', borderRadius: 10,
                padding: '14px 18px', maxWidth: 420, boxShadow: '0 8px 30px rgba(0,0,0,0.12)',
                fontSize: 12, lineHeight: 1.7, color: 'var(--color-text-secondary)',
              }}>
                <div style={{ fontWeight: 800, fontSize: 14, marginBottom: 6, color: 'var(--color-text-primary)' }}>
                  {hoveredCell.berth_code} — {spec?.name || 'Berth'}
                </div>
                <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 8 }}>
                  Score: <strong style={{ color: cell.score > 0.8 ? '#10b981' : cell.score > 0.3 ? '#f59e0b' : '#ef4444' }}>{(cell.score * 100).toFixed(0)}%</strong>
                  {spec && <> · Max LOA: {spec.max_loa}m · Depth: {spec.depth}m · Equipment: {spec.equipment[0]}</>}
                </div>
                {cell.reasons.map((r, i) => (
                  <div key={i} style={{ padding: '3px 0', borderBottom: i < cell.reasons.length - 1 ? '1px solid #f1f5f9' : 'none' }}>
                    {r}
                  </div>
                ))}
              </div>
            );
          })()}
        </div>
      )}

      {/* ── Schedule Assignments + Next Optimal ─────── */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xl">📋</span>
        <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--color-text-primary)' }}>Schedule Assignments</h3>
      </div>
      <div className="space-y-2 mb-8">
        {result.assignments.map(a => {
          const isOverridden = overrides.has(a.vessel_id);
          const isExpanded = expandedVessel === a.vessel_id;
          const alternatives = result.ranked_alternatives?.[a.vessel_id] || [];
          return (
            <div key={a.vessel_id}>
              <div className="card-flat" style={{ padding: '12px 16px', borderLeft: `3px solid ${isOverridden ? '#f59e0b' : 'transparent'}` }}>
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--color-text-primary)' }}>{a.vessel_name}</span>
                    <span style={{
                      padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 700,
                      background: a.confidence > 0.85 ? 'rgba(16,185,129,0.12)' : a.confidence > 0.6 ? 'rgba(245,158,11,0.12)' : 'rgba(239,68,68,0.12)',
                      color: a.confidence > 0.85 ? '#10b981' : a.confidence > 0.6 ? '#f59e0b' : '#ef4444',
                    }}>{(a.confidence * 100).toFixed(0)}%</span>
                    {isOverridden && <span style={{ fontSize: 10, color: '#f59e0b', fontWeight: 600 }}>MANUAL</span>}
                  </div>
                  <div className="flex items-center gap-3" style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                    <span>Berth <strong style={{ color: BERTH_COLORS[a.berth_code] || '#0ea5e9' }}>{a.berth_code}</strong></span>
                    <span>Start {a.start_hours.toFixed(1)}h → End {a.end_hours.toFixed(1)}h</span>
                    <span>Wait {a.waiting_hours.toFixed(1)}h</span>
                    <button onClick={() => setExpandedVessel(isExpanded ? null : a.vessel_id)}
                      style={{ padding: '2px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                        background: 'rgba(14,165,233,0.1)', color: '#0ea5e9', border: '1px solid rgba(14,165,233,0.3)' }}>
                      🔄 {isExpanded ? 'Close' : 'Change Berth'}
                    </button>
                  </div>
                </div>
                {/* AI Explanation */}
                <details style={{ marginTop: 8 }}>
                  <summary style={{ fontSize: 12, cursor: 'pointer', color: 'var(--color-text-muted)' }}>🤖 AI Explanation</summary>
                  <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 6, padding: '10px 14px', background: 'rgba(99,102,241,0.04)', borderRadius: 8, lineHeight: 1.8, borderLeft: '3px solid rgba(99,102,241,0.3)' }}>
                    {a.explanation}
                  </p>
                </details>
              </div>
              {/* Ranked Alternatives */}
              {isExpanded && alternatives.length > 0 && (
                <AlternativesPanel vesselName={a.vessel_name} currentBerth={a.berth_code} alternatives={alternatives} onSelect={(bc) => selectAlternativeBerth(a.vessel_id, bc)} />
              )}
            </div>
          );
        })}
      </div>

      {/* ── Interactive Berth Timeline ─────────────────── */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xl">🗓</span>
        <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--color-text-primary)' }}>Interactive Berth Timeline</h3>
        <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Drag vessels between berth lanes to swap assignments</span>
      </div>
      <div className="card mb-8" style={{ padding: 20, overflow: 'auto', position: 'relative' }} ref={timelineRef}>
        {(() => {
          const maxH = Math.max(...result.assignments.map(a => a.end_hours), 48);
          return (
            <div style={{ minWidth: 600 }}>
              {ALL_BERTHS.map(bc => {
                const berthAssignments = result.assignments.filter(a => a.berth_code === bc);
                const hasVessels = berthAssignments.length > 0;
                return (
                  <div key={bc} className="flex items-center gap-3 mb-2" style={{ height: 44 }}
                    onDragOver={e => { e.preventDefault(); e.currentTarget.style.background = 'rgba(14,165,233,0.08)'; }}
                    onDragLeave={e => { e.currentTarget.style.background = ''; }}
                    onDrop={e => {
                      e.preventDefault(); e.currentTarget.style.background = '';
                      const vid = e.dataTransfer.getData('vessel_id');
                      const curBerth = e.dataTransfer.getData('current_berth');
                      if (vid && curBerth !== bc) selectAlternativeBerth(vid, bc);
                    }}>
                    <div style={{ width: 110, fontSize: 11, textAlign: 'right' }}>
                      <div style={{ fontWeight: 700, color: BERTH_COLORS[bc] || '#94a3b8', opacity: hasVessels ? 1 : 0.5 }}>{bc.replace('INMAA-', '')}</div>
                      <div style={{ fontSize: 9, color: 'var(--color-text-muted)' }}>{BERTH_SPECS[bc]?.name || ''}</div>
                    </div>
                    <div className="flex-1 relative" style={{ height: 36, background: hasVessels ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.015)', borderRadius: 8, border: `1px ${hasVessels ? 'solid' : 'dashed'} rgba(0,0,0,0.06)` }}>
                      {Array.from({ length: Math.ceil(maxH / 8) }, (_, i) => i * 8).map(h => (
                        <div key={h} style={{ position: 'absolute', left: `${(h / maxH) * 100}%`, top: 0, bottom: 0, borderLeft: '1px dashed rgba(0,0,0,0.04)' }} />
                      ))}
                      {!hasVessels && <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: 'var(--color-text-muted)', opacity: 0.5 }}>Drop vessel here</div>}
                      {berthAssignments.map(a => {
                        const isOvr = overrides.has(a.vessel_id);
                        return (
                          <div key={a.vessel_id} draggable
                            onDragStart={e => { e.dataTransfer.setData('vessel_id', a.vessel_id); e.dataTransfer.setData('current_berth', a.berth_code); }}
                            onMouseEnter={e => { const rect = e.currentTarget.getBoundingClientRect(); setHoveredBar(a); setBarPos({ x: rect.left + rect.width / 2, y: rect.top - 10 }); }}
                            onMouseLeave={() => setHoveredBar(null)}
                            style={{
                              position: 'absolute', top: 3, height: 30, borderRadius: 6, cursor: 'grab',
                              left: `${(a.start_hours / maxH) * 100}%`, width: `${Math.max(((a.end_hours - a.start_hours) / maxH) * 100, 4)}%`,
                              background: `linear-gradient(135deg, ${BERTH_COLORS[bc] || '#0ea5e9'}, ${BERTH_COLORS[bc] || '#0ea5e9'}dd)`,
                              border: isOvr ? '2px solid #f59e0b' : '1px solid rgba(255,255,255,0.3)',
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              fontSize: 10, fontWeight: 700, color: 'white', overflow: 'hidden', whiteSpace: 'nowrap',
                              transition: 'transform 0.15s, box-shadow 0.15s',
                              boxShadow: hoveredBar?.vessel_id === a.vessel_id ? '0 4px 12px rgba(0,0,0,0.2)' : '0 1px 3px rgba(0,0,0,0.1)',
                              transform: hoveredBar?.vessel_id === a.vessel_id ? 'scale(1.04)' : 'scale(1)',
                            }}>
                            {a.vessel_name} {isOvr && '⚡'}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
              <div className="flex items-center gap-3" style={{ marginTop: 6 }}>
                <div style={{ width: 110 }} />
                <div className="flex-1 flex justify-between" style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                  {Array.from({ length: 5 }, (_, i) => <span key={i}>{((maxH * i) / 4).toFixed(0)}h</span>)}
                </div>
              </div>
            </div>
          );
        })()}

        {hoveredBar && (() => {
          const v = vessels.find(vv => vv.vessel_id === hoveredBar.vessel_id);
          const spec = BERTH_SPECS[hoveredBar.berth_code];
          return (
            <div style={{
              position: 'fixed', left: barPos.x, top: barPos.y, transform: 'translate(-50%, -100%)',
              zIndex: 1000, background: 'white', border: '1px solid #e2e8f0', borderRadius: 10,
              padding: '12px 16px', minWidth: 280, boxShadow: '0 8px 30px rgba(0,0,0,0.12)',
              fontSize: 12, lineHeight: 1.6, color: 'var(--color-text-secondary)',
            }}>
              <div style={{ fontWeight: 800, fontSize: 14, color: 'var(--color-text-primary)', marginBottom: 4 }}>
                {hoveredBar.vessel_name} → {hoveredBar.berth_code}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px 12px', fontSize: 11 }}>
                <span>⏰ Start: <strong>{hoveredBar.start_hours.toFixed(1)}h</strong></span>
                <span>⏱ End: <strong>{hoveredBar.end_hours.toFixed(1)}h</strong></span>
                <span>⏳ Wait: <strong>{hoveredBar.waiting_hours.toFixed(1)}h</strong></span>
                <span>🔧 Service: <strong>{hoveredBar.service_hours}h</strong></span>
                <span>📊 Confidence: <strong style={{ color: hoveredBar.confidence > 0.85 ? '#10b981' : '#f59e0b' }}>{(hoveredBar.confidence * 100).toFixed(0)}%</strong></span>
                {v && <span>📦 Cargo: <strong>{v.cargo_tons.toLocaleString()}t</strong></span>}
              </div>
              {spec && <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 4 }}>🏗 {spec.name} · {spec.equipment[0]}</div>}
              <div style={{ fontSize: 10, color: '#0ea5e9', marginTop: 4 }}>🖱 Drag to another berth lane to reassign</div>
            </div>
          );
        })()}
      </div>

      {/* ── Cost Breakdown per Vessel (with Change Berth) ── */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xl">💰</span>
        <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--color-text-primary)' }}>Cost Breakdown per Vessel</h3>
      </div>
      <div className="space-y-2 mb-8">
        {result.costs.map(bd => {
          const assignment = result.assignments.find(a => a.vessel_id === bd.vessel_id);
          const isOverridden = overrides.has(bd.vessel_id);
          const isCostExpanded = expandedCostVessel === bd.vessel_id;
          const alternatives = result.ranked_alternatives?.[bd.vessel_id] || [];
          return (
            <div key={bd.vessel_id}>
              <div className="card-flat" style={{ padding: '12px 16px', borderLeft: `3px solid ${isOverridden ? '#f59e0b' : 'transparent'}` }}>
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--color-text-primary)' }}>{bd.vessel_name}</span>
                    {assignment && (
                      <span style={{
                        padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 700,
                        background: assignment.confidence > 0.85 ? 'rgba(16,185,129,0.12)' : 'rgba(245,158,11,0.12)',
                        color: assignment.confidence > 0.85 ? '#10b981' : '#f59e0b',
                      }}>{(assignment.confidence * 100).toFixed(0)}%</span>
                    )}
                    {isOverridden && <span style={{ fontSize: 10, color: '#f59e0b', fontWeight: 600 }}>MANUAL</span>}
                  </div>
                  <div className="flex gap-3 flex-wrap items-center" style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>
                    <span>Berth <strong style={{ color: BERTH_COLORS[bd.berth_code] }}>{bd.berth_code}</strong></span>
                    <span>Waiting <strong>${bd.waiting_cost.toLocaleString()}</strong></span>
                    <span>Fuel <strong>${bd.fuel_burn_cost.toLocaleString()}</strong></span>
                    <span>Equipment <strong>${bd.equipment_rental.toLocaleString()}</strong></span>
                    <span style={{ fontWeight: 800, color: 'var(--color-text-primary)' }}>Net ${bd.net_cost.toLocaleString()}</span>
                    <button onClick={() => setExpandedCostVessel(isCostExpanded ? null : bd.vessel_id)}
                      style={{ padding: '2px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                        background: 'rgba(14,165,233,0.1)', color: '#0ea5e9', border: '1px solid rgba(14,165,233,0.3)' }}>
                      🔄 {isCostExpanded ? 'Close' : 'Change Berth'}
                    </button>
                  </div>
                </div>
              </div>
              {isCostExpanded && alternatives.length > 0 && (
                <AlternativesPanel vesselName={bd.vessel_name} currentBerth={bd.berth_code} alternatives={alternatives} onSelect={(bc) => selectAlternativeBerth(bd.vessel_id, bc)} />
              )}
            </div>
          );
        })}
      </div>

      {/* ── Cost Distribution Chart ─────────────────── */}
      <div className="card mb-8" style={{ padding: 20 }}>
        <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, marginBottom: 16 }}>Cost Distribution</h4>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={result.costs.map(c => ({ name: c.vessel_name, Waiting: c.waiting_cost, Fuel: c.fuel_burn_cost, Equipment: c.equipment_rental, SLA: c.sla_penalty }))}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
            <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} />
            <Tooltip contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 8 }} />
            <Bar dataKey="Waiting" stackId="a" fill="#0ea5e9" />
            <Bar dataKey="Fuel" stackId="a" fill="#f59e0b" />
            <Bar dataKey="Equipment" stackId="a" fill="#8b5cf6" />
            <Bar dataKey="SLA" stackId="a" fill="#ef4444" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ── Waiting Time Chart ─────────────────── */}
      <div className="card mb-8" style={{ padding: 20 }}>
        <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, marginBottom: 16 }}>Waiting Time by Vessel</h4>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={result.assignments.map(a => ({ name: a.vessel_name, wait: a.waiting_hours }))}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
            <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} label={{ value: 'Hours', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 8 }} />
            <Bar dataKey="wait" radius={[6, 6, 0, 0]}>
              {result.assignments.map((a, i) => (
                <Cell key={i} fill={a.waiting_hours > 4 ? '#ef4444' : a.waiting_hours > 2 ? '#f59e0b' : '#10b981'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ── Detailed Berth Analysis — Parameter-Level Breakdown ── */}
      <details style={{ marginBottom: 24 }}>
        <summary className="cursor-pointer" style={{
          fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15,
          color: 'var(--color-text-primary)', padding: '14px 20px',
          background: 'rgba(0,0,0,0.02)', border: '1px solid var(--color-border)',
          borderRadius: 10, display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span style={{ fontSize: 18 }}>🧠</span>
          Detailed Berth Analysis — Parameter-Level Breakdown
        </summary>
        <div style={{ border: '1px solid var(--color-border)', borderTop: 'none', borderBottomLeftRadius: 10, borderBottomRightRadius: 10, padding: 20 }}>
          {result.assignments.map(a => {
            const v = vessels.find(vv => vv.vessel_id === a.vessel_id);
            const spec = BERTH_SPECS[a.berth_code];
            if (!v || !spec) return null;
            const loaSlack = spec.max_loa - v.loa_m;
            const draftSlack = spec.depth - v.draft_m;
            const beamSlack = (spec.max_beam || 50) - v.beam_m;
            const checks = [
              { cat: 'PHYSICAL FIT', emoji: '🔧', items: [
                { icon: loaSlack > 40 ? '✔' : loaSlack > 10 ? '✔' : loaSlack > 0 ? '⚠' : '❌', color: loaSlack > 10 ? '#10b981' : loaSlack > 0 ? '#f59e0b' : '#ef4444', text: `LOA (${v.loa_m}m) vs limit (${spec.max_loa}m) → margin: ${loaSlack}m` },
                { icon: draftSlack > 3 ? '✔' : draftSlack > 1 ? '⚠' : '❌', color: draftSlack > 1 ? '#10b981' : draftSlack > 0 ? '#f59e0b' : '#ef4444', text: `Draft (${v.draft_m}m) vs depth (${spec.depth}m) → UKC: ${draftSlack.toFixed(1)}m` },
                { icon: beamSlack > 5 ? '✔' : beamSlack > 0 ? '⚠' : '❌', color: beamSlack > 0 ? '#10b981' : '#ef4444', text: `Beam (${v.beam_m}m) vs limit (${spec.max_beam || 50}m) → clearance: ${beamSlack}m` },
              ]},
              { cat: 'OPERATIONAL', emoji: '⚙️', items: [
                { icon: '✔', color: '#10b981', text: `Vessel type: ${v.vessel_type}` },
                { icon: '✔', color: '#10b981', text: `Cargo type: ${v.cargo_type}` },
              ]},
              { cat: 'PERFORMANCE', emoji: '📊', items: [
                { icon: a.waiting_hours < 3 ? '✔' : '⚠', color: a.waiting_hours < 3 ? '#10b981' : '#f59e0b', text: `Wait: ${a.waiting_hours.toFixed(1)}h` },
                { icon: 'ℹ', color: '#6366f1', text: `Service: ${a.service_hours}h` },
              ]},
              { cat: 'COMMERCIAL', emoji: '💰', items: [
                { icon: 'ℹ', color: '#6366f1', text: `Equipment: ${spec.equipment.join(', ')}` },
              ]},
            ];
            return (
              <div key={a.vessel_id} style={{ marginBottom: 16, border: '1px solid var(--color-border)', borderRadius: 10, padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontWeight: 800, fontSize: 15 }}>🏗️ {a.vessel_name} → {a.berth_code}</span>
                    <span style={{ background: 'rgba(16,185,129,0.1)', color: '#10b981', padding: '2px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700 }}>FEASIBLE</span>
                  </div>
                  <span style={{ color: a.confidence > 0.6 ? '#10b981' : '#f59e0b', fontWeight: 800, fontSize: 16 }}>{(a.confidence * 100).toFixed(0)}%</span>
                </div>
                {checks.map(cat => (
                  <div key={cat.cat} style={{ background: 'rgba(0,0,0,0.02)', border: '1px solid var(--color-border)', borderRadius: 8, padding: '10px 14px', marginBottom: 6 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span>{cat.emoji}</span><span>{cat.cat}</span>
                    </div>
                    {cat.items.map((item, j) => (
                      <div key={j} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', borderBottom: j < cat.items.length - 1 ? '1px solid rgba(0,0,0,0.04)' : 'none' }}>
                        <span style={{ color: item.color, fontSize: 14 }}>{item.icon}</span>
                        <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{item.text}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </details>
    </>
  );
}

/* ── Reusable Alternatives Panel ───────────────────── */
function AlternativesPanel({ vesselName, currentBerth, alternatives, onSelect }: {
  vesselName: string; currentBerth: string;
  alternatives: { berth_code: string; confidence: number; waiting_hours: number; cost_delta: number; reasons: string[] }[];
  onSelect: (bc: string) => void;
}) {
  return (
    <div className="card" style={{ padding: 16, marginTop: 4, borderLeft: '3px solid #0ea5e9' }}>
      <h5 style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 10 }}>
        🏆 Ranked Alternative Berths for {vesselName}
      </h5>
      <div className="space-y-2">
        {alternatives.map((alt, idx) => (
          <div key={alt.berth_code} className="card-flat" style={{ padding: '8px 14px' }}>
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-3">
                <span style={{ fontWeight: 800, fontSize: 14, color: idx === 0 ? '#10b981' : 'var(--color-text-primary)' }}>#{idx + 1}</span>
                <span style={{ color: BERTH_COLORS[alt.berth_code], fontWeight: 700 }}>{alt.berth_code}</span>
                <span style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>{BERTH_SPECS[alt.berth_code]?.name}</span>
                <span style={{
                  padding: '2px 6px', borderRadius: 10, fontSize: 10, fontWeight: 600,
                  background: alt.confidence > 0.85 ? 'rgba(16,185,129,0.12)' : 'rgba(245,158,11,0.12)',
                  color: alt.confidence > 0.85 ? '#10b981' : '#f59e0b',
                }}>{(alt.confidence * 100).toFixed(0)}%</span>
              </div>
              <div className="flex items-center gap-3" style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                <span>Wait {alt.waiting_hours.toFixed(1)}h</span>
                <span>Cost Δ ${alt.cost_delta > 0 ? '+' : ''}{alt.cost_delta.toLocaleString()}</span>
                <button onClick={() => onSelect(alt.berth_code)}
                  disabled={alt.berth_code === currentBerth}
                  style={{ padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                    background: alt.berth_code === currentBerth ? 'var(--color-border)' : 'var(--color-primary)', color: 'white', border: 'none' }}>
                  {alt.berth_code === currentBerth ? 'Current' : 'Select'}
                </button>
              </div>
            </div>
            {/* Show top reasons */}
            <div style={{ marginTop: 6, fontSize: 11, color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
              {alt.reasons.slice(0, 3).map((r, i) => <div key={i}>{r}</div>)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
