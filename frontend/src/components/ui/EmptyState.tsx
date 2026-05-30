/**
 * EmptyState â€” Placeholder for empty data states.
 */
'use client';

interface EmptyStateProps {
  icon?: string;
  title: string;
  message?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon = 'ðŸ“‹', title, message, action }: EmptyStateProps) {
  return (
    <div className="text-center py-12" style={{ color: 'var(--color-text-muted)' }}>
      <span style={{ fontSize: 40, display: 'block', marginBottom: 12 }}>{icon}</span>
      <h3 style={{
        fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16,
        color: 'var(--color-text-primary)', marginBottom: 4,
      }}>
        {title}
      </h3>
      {message && <p style={{ fontSize: 13, marginBottom: 16, maxWidth: 400, margin: '0 auto 16px' }}>{message}</p>}
      {action}
    </div>
  );
}
