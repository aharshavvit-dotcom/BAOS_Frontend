import Link from 'next/link';

/**
 * Custom 404 page — BAOS branded.
 * FIX (Phase 6): Replaces the default Next.js 404 with a branded page.
 */
export default function NotFound() {
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
      <div style={{ fontSize: '5rem', marginBottom: '1rem', opacity: 0.7 }}>🚢</div>
      <h1
        style={{
          fontFamily: 'var(--font-display, Space Grotesk, sans-serif)',
          fontSize: '6rem',
          fontWeight: 900,
          lineHeight: 1,
          background: 'linear-gradient(135deg, #6366f1, #a78bfa)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: '0.5rem',
        }}
      >
        404
      </h1>
      <h2
        style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          marginBottom: '0.75rem',
          fontFamily: 'var(--font-display, Space Grotesk, sans-serif)',
        }}
      >
        Port Not Found
      </h2>
      <p
        style={{
          fontSize: '1rem',
          color: '#94a3b8',
          maxWidth: '400px',
          lineHeight: 1.6,
          marginBottom: '2rem',
        }}
      >
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
        Check the URL or navigate back to the dashboard.
      </p>
      <Link
        href="/dashboard"
        style={{
          padding: '0.75rem 2rem',
          borderRadius: '10px',
          background: 'var(--color-primary, #6366f1)',
          color: '#fff',
          fontWeight: 700,
          fontSize: '0.9375rem',
          textDecoration: 'none',
        }}
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
