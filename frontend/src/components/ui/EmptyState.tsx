/**
 * EmptyState â€” Placeholder for empty data states.
 */
'use client';

import { ClipboardList } from 'lucide-react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  message?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, message, action }: EmptyStateProps) {
  const defaultIcon = icon || <ClipboardList size={40} className="mx-auto text-slate-400 opacity-50" />;
  return (
    <div className="text-center py-12" style={{ color: 'var(--color-text-muted)' }}>
      <div style={{ display: 'block', marginBottom: 12 }}>{defaultIcon}</div>
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
