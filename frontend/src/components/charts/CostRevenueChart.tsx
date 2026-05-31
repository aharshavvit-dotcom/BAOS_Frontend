'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const defaultData = [
  { month: 'Jan', revenue: 320, cost: 180 },
  { month: 'Feb', revenue: 380, cost: 195 },
  { month: 'Mar', revenue: 410, cost: 210 },
  { month: 'Apr', revenue: 395, cost: 200 },
  { month: 'May', revenue: 450, cost: 220 },
  { month: 'Jun', revenue: 480, cost: 230 },
];

export default function CostRevenueChart({ data = defaultData }: { data?: any[] }) {
  return (
    <div className="h-full w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: 15, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} />
          <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={(v) => `$${v}K`} />
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
          <Bar dataKey="revenue" name="Revenue ($K)" fill="rgba(59, 130, 246, 0.85)" radius={[6, 6, 0, 0]} />
          <Bar dataKey="cost" name="Cost ($K)" fill="rgba(239, 68, 68, 0.7)" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
