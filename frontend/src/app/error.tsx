'use client';

/**
 * Next.js App Router error page — catches errors at the root layout level.
 * FIX (Phase 6): Provides a user-friendly error page with reset capability.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'var(--color-dark, #0f172a)',
        color: '#e2e8f0',
        fontFamily: 'var(--font-body, Inter, sans-serif)',
        padding: '2rem',
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: '4rem', marginBottom: '1.5rem' }}>🚢</div>
      <h1
        style={{
          fontFamily: 'var(--font-display, Space Grotesk, sans-serif)',
          fontSize: '2rem',
          fontWeight: 800,
          marginBottom: '0.75rem',
        }}
      >
        Something went wrong
      </h1>
      <p
        style={{
          fontSize: '1rem',
          color: '#94a3b8',
          maxWidth: '500px',
          marginBottom: '0.5rem',
          lineHeight: 1.6,
        }}
      >
        An unexpected error occurred in the BAOS application.
        {process.env.NODE_ENV === 'development' && error?.message && (
          <span
            style={{
              display: 'block',
              marginTop: '0.5rem',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-code, monospace)',
              color: '#f87171',
              background: 'rgba(248, 113, 113, 0.1)',
              padding: '0.5rem 1rem',
              borderRadius: '6px',
            }}
          >
            {error.message}
          </span>
        )}
      </p>
      <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
        <button
          onClick={reset}
          style={{
            padding: '0.75rem 2rem',
            borderRadius: '10px',
            border: 'none',
            background: 'var(--color-primary, #6366f1)',
            color: '#fff',
            fontWeight: 700,
            fontSize: '0.9375rem',
            cursor: 'pointer',
          }}
        >
          Try Again
        </button>
        <a
          href="/dashboard"
          style={{
            padding: '0.75rem 2rem',
            borderRadius: '10px',
            border: '1px solid #334155',
            background: 'transparent',
            color: '#e2e8f0',
            fontWeight: 600,
            fontSize: '0.9375rem',
            textDecoration: 'none',
            display: 'inline-flex',
            alignItems: 'center',
          }}
        >
          Go to Dashboard
        </a>
      </div>
    </div>
  );
}
