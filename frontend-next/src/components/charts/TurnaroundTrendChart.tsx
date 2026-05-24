'use client';

import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  Line,
} from 'recharts';

const defaultData = [
  { day: 'Mon', avg: 28.5, target: 24 },
  { day: 'Tue', avg: 26.2, target: 24 },
  { day: 'Wed', avg: 27.8, target: 24 },
  { day: 'Thu', avg: 24.1, target: 24 },
  { day: 'Fri', avg: 25.6, target: 24 },
  { day: 'Sat', avg: 29.3, target: 24 },
  { day: 'Sun', avg: 26.4, target: 24 },
];

export default function TurnaroundTrendChart({ data = defaultData }: { data?: any[] }) {
  return (
    <div className="h-full w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 11 }} />
          <YAxis tick={{ fill: '#64748b', fontSize: 11 }} domain={[20, 35]} tickFormatter={(v) => `${v}h`} />
          <Tooltip
            contentStyle={{
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: 12,
              boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.05)',
              color: '#0F172A',
            }}
          />
          <Area
            type="monotone"
            dataKey="avg"
            name="Avg Turnaround (hours)"
            stroke="#2563eb"
            fill="rgba(37, 99, 235, 0.05)"
            strokeWidth={2.5}
            dot={{ fill: '#2563eb', stroke: '#fff', strokeWidth: 2, r: 4 }}
          />
          <Line
            type="linear"
            dataKey="target"
            name="Target (24h)"
            stroke="#10b981"
            strokeDasharray="6 4"
            strokeWidth={2}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
