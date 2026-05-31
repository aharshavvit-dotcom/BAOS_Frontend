import React from 'react';

type KpiCardProps = {
  icon: React.ReactNode;
  value: React.ReactNode;
  label: string;
  sublabel?: string;
  trend?: string;
  tone?: 'blue' | 'green' | 'amber' | 'red' | 'slate';
};

export default function KpiCard({
  icon,
  value,
  label,
  sublabel,
  trend,
  tone = 'blue',
}: KpiCardProps) {
  const toneClasses = {
    blue: {
      bg: 'bg-blue-50/50',
      text: 'text-blue-600',
      border: 'hover:border-blue-200',
    },
    green: {
      bg: 'bg-emerald-50/50',
      text: 'text-emerald-600',
      border: 'hover:border-emerald-200',
    },
    amber: {
      bg: 'bg-amber-50/50',
      text: 'text-amber-600',
      border: 'hover:border-amber-200',
    },
    red: {
      bg: 'bg-rose-50/50',
      text: 'text-rose-600',
      border: 'hover:border-rose-200',
    },
    slate: {
      bg: 'bg-slate-50/50',
      text: 'text-slate-600',
      border: 'hover:border-slate-300',
    },
  };

  const selectedTone = toneClasses[tone] || toneClasses.blue;

  return (
    <div className={`bg-white border border-slate-200 rounded-xl shadow-sm flex flex-col justify-between p-6 transition-all duration-300 ${selectedTone.border}`}>
      <div>
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-bold tracking-wider uppercase text-slate-400">
            {label}
          </span>
          <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${selectedTone.bg} ${selectedTone.text}`}>
            <span className="text-xl">{icon}</span>
          </div>
        </div>

        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {value}
          </span>
          {trend && (
            <span className={`text-xs font-semibold ${trend.startsWith('-') ? 'text-rose-600' : 'text-emerald-600'}`}>
              {trend}
            </span>
          )}
        </div>
      </div>

      {sublabel && (
        <div className="mt-4 border-t border-slate-100 pt-3">
          <p className="text-xs text-slate-400 font-normal">{sublabel}</p>
        </div>
      )}
    </div>
  );
}
