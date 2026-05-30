type SourceBadgeProps = {
  source: 'DEMO' | 'HISTORICAL' | 'ASSUMPTION' | 'LIVE' | 'SOLVER';
  className?: string;
};

export default function SourceBadge({ source, className = '' }: SourceBadgeProps) {
  const badgeConfig = {
    DEMO: {
      bg: 'bg-blue-100 text-blue-800 border-blue-200',
      label: 'Demo Mode',
    },
    HISTORICAL: {
      bg: 'bg-indigo-100 text-indigo-800 border-indigo-200',
      label: 'Historical Data',
    },
    ASSUMPTION: {
      bg: 'bg-amber-100 text-amber-800 border-amber-200',
      label: 'Operational Assumption',
    },
    LIVE: {
      bg: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      label: 'Live DB Connect',
    },
    SOLVER: {
      bg: 'bg-sky-100 text-sky-800 border-sky-200',
      label: 'Solver Output',
    },
  };

  const current = badgeConfig[source] || badgeConfig.DEMO;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide uppercase ${current.bg} ${className}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {current.label}
    </span>
  );
}
