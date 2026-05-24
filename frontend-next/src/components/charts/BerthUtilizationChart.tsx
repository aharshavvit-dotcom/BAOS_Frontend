'use client';

import {
  BarChart,
  Bar,
  Cell,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const defaultData = [
  { name: 'B1', utilization: 78, target: 75 },
  { name: 'B2', utilization: 62, target: 75 },
  { name: 'B3', utilization: 85, target: 75 },
  { name: 'B4', utilization: 45, target: 75 },
  { name: 'B5', utilization: 71, target: 75 },
];

const COLORS = [
  'rgba(59, 130, 246, 0.85)',   // Blue
  'rgba(16, 185, 129, 0.85)',   // Emerald
  'rgba(139, 92, 246, 0.85)',   // Violet
  'rgba(245, 158, 11, 0.85)',   // Amber
  'rgba(239, 68, 68, 0.85)',    // Rose
];

export default function BerthUtilizationChart({ data = defaultData }: { data?: any[] }) {
  return (
    <div className="h-full w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} />
          <YAxis tick={{ fill: '#64748b', fontSize: 11 }} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <Tooltip
            contentStyle={{
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: 12,
              boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.05)',
              color: '#0F172A',
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: '#475569', paddingTop: 10 }} />
          <Bar dataKey="utilization" name="Current Utilization %" radius={[6, 6, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
          <Line
            type="monotone"
            dataKey="target"
            name="Optimal Target (75%)"
            stroke="#10b981"
            strokeDasharray="6 4"
            strokeWidth={2}
            dot={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
