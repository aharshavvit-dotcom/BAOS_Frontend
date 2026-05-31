/**
 * Dashboard loading skeleton — shown during page transitions.
 * FIX (Phase 6): Full-page loading state for dashboard routes.
 */
export default function DashboardLoading() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
        padding: '1.5rem 0',
        animation: 'pulse 1.5s ease-in-out infinite',
      }}
    >
      {/* Header skeleton */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div
          style={{
            width: '240px',
            height: '32px',
            borderRadius: '8px',
            background: 'var(--color-dark-border, #1e293b)',
          }}
        />
        <div
          style={{
            width: '120px',
            height: '32px',
            borderRadius: '8px',
            background: 'var(--color-dark-border, #1e293b)',
          }}
        />
      </div>

      {/* KPI cards skeleton */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            style={{
              height: '130px',
              borderRadius: '16px',
              background: 'var(--color-dark-card, #1e293b)',
              border: '1px solid var(--color-dark-border, #334155)',
            }}
          />
        ))}
      </div>

      {/* Chart skeleton */}
      <div
        style={{
          height: '320px',
          borderRadius: '16px',
          background: 'var(--color-dark-card, #1e293b)',
          border: '1px solid var(--color-dark-border, #334155)',
        }}
      />

      {/* Table skeleton */}
      <div
        style={{
          height: '200px',
          borderRadius: '16px',
          background: 'var(--color-dark-card, #1e293b)',
          border: '1px solid var(--color-dark-border, #334155)',
        }}
      />

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
