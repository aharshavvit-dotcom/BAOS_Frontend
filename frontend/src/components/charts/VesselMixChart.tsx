'use client';

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const defaultData = [
  { name: 'Container', value: 40, color: '#3b82f6' },        // Blue
  { name: 'Bulk Carrier', value: 25, color: '#10b981' },    // Emerald
  { name: 'General Cargo', value: 20, color: '#8b5cf6' },    // Violet
  { name: 'Tanker', value: 15, color: '#f59e0b' },           // Amber
];

export default function VesselMixChart({ data = defaultData }: { data?: any[] }) {
  return (
    <div className="h-full w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={2}
            dataKey="value"
            nameKey="name"
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: 12,
              boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.05)',
              color: '#0F172A',
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: '#475569', paddingTop: 10 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
