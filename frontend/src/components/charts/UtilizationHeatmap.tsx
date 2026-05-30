'use client';

const defaultHeatmapData = [
  { berth: 'Berth 1', data: [72, 85, 68, 91, 78, 45, 38] },
  { berth: 'Berth 2', data: [55, 62, 78, 70, 88, 52, 41] },
  { berth: 'Berth 3', data: [88, 92, 75, 83, 95, 60, 55] },
  { berth: 'Berth 4', data: [42, 58, 65, 72, 68, 35, 28] },
  { berth: 'Berth 5', data: [68, 75, 82, 88, 72, 48, 42] },
];
const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function getHeatmapColor(val: number) {
  if (val >= 90) return 'bg-rose-100 text-rose-800 border-rose-200';
  if (val >= 75) return 'bg-rose-50/50 text-rose-700 border-rose-100';
  if (val >= 60) return 'bg-amber-100 text-amber-800 border-amber-200';
  if (val >= 40) return 'bg-amber-50/50 text-amber-700 border-amber-100';
  return 'bg-emerald-50/50 text-emerald-700 border-emerald-100';
}

export default function UtilizationHeatmap({ data = defaultHeatmapData }: { data?: any[] }) {
  return (
    <div className="overflow-x-auto w-full">
      <div className="min-w-[760px] p-1">
        {/* Header grid */}
        <div className="grid grid-cols-[100px_repeat(7,1fr)] gap-2 mb-2">
          <div className="text-sm font-semibold text-slate-500 flex items-center">Berth</div>
          {days.map((d) => (
            <div key={d} className="text-sm font-semibold text-slate-500 text-center py-2">
              {d}
            </div>
          ))}
        </div>

        {/* Rows */}
        <div className="space-y-2">
          {data.map((row) => (
            <div key={row.berth} className="grid grid-cols-[100px_repeat(7,1fr)] gap-2">
              <div className="text-sm font-bold text-slate-700 flex items-center">
                {row.berth}
              </div>
              {row.data.map((val: number, di: number) => {
                const colorClass = getHeatmapColor(val);
                return (
                  <div
                    key={`${row.berth}-${di}`}
                    className={`rounded-xl border p-4 text-center text-sm font-extrabold transition-all duration-200 hover:scale-[1.03] ${colorClass}`}
                    title={`${row.berth} Â· ${days[di]}: ${val}%`}
                  >
                    {val}%
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
