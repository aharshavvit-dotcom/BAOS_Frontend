/**
 * Dashboard Layout — Sidebar + Topbar + Protected Route
 */
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useUIStore } from '@/store/uiStore';
import { useSocket } from '@/hooks/useSocket';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, checkAuth, logout } = useAuthStore();
  const { sidebarOpen, profileDropdownOpen, setProfileDropdownOpen, toasts, removeToast } = useUIStore();
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState('');

  // Connect WebSocket for real-time updates (disabled when backend WS unavailable)
  // useSocket();

  useEffect(() => {
    checkAuth().then(() => setLoading(false));
  }, [checkAuth]);

  // Live time
  useEffect(() => {
    function updateTime() {
      setCurrentTime(new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    }
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // Redirect if not authenticated
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      const token = localStorage.getItem('baos_access_token');
      if (!token) {
        router.push('/login');
      }
    }
  }, [loading, isAuthenticated, router]);

  function handleLogout() {
    logout();
    router.push('/login');
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--color-dark)' }}>
        <div className="text-center">
          <div className="text-4xl mb-4">🚢</div>
          <p style={{ color: 'var(--color-text-muted)' }}>Loading BAOS AI...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--color-dark)' }}>
      {/* ── Sidebar ──────────────────────────────────────── */}
      <aside
        className="flex-shrink-0 flex flex-col border-r h-screen sticky top-0 transition-all duration-300"
        style={{
          width: sidebarOpen ? 260 : 72,
          background: 'var(--color-dark-card)',
          borderColor: 'var(--color-dark-border)',
        }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 p-5" style={{ borderBottom: '1px solid var(--color-dark-border)' }}>
          <span className="text-2xl">🚢</span>
          {sidebarOpen && (
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 18, color: 'var(--color-text-primary)' }}>
              BAOS <span style={{ color: 'var(--color-primary)' }}>AI</span>
            </span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1">
          {[
            { icon: '📊', label: 'Dashboard', href: '/dashboard' },
            { icon: '🧠', label: 'Get Recommendation', href: '/dashboard/recommend' },
            { icon: '🚀', label: 'Optimizer', href: '/dashboard/optimizer' },
            { icon: '💰', label: 'Commercial Intel', href: '/dashboard/commercial' },
            { icon: '📈', label: 'Analytics', href: '/dashboard/analytics' },
            { icon: '🔔', label: 'Alerts', href: '/dashboard/alerts' },
          ].map((item, i) => (
            <Link
              key={i}
              href={item.href}
              className={`sidebar-link ${pathname === item.href ? 'active' : ''}`}
              title={item.label}
            >
              <span className="text-lg">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* Bottom nav */}
        <div className="p-3 space-y-1" style={{ borderTop: '1px solid var(--color-dark-border)' }}>
          <Link href="#" className="sidebar-link">
            <span className="text-lg">⚙️</span>
            {sidebarOpen && <span>Settings</span>}
          </Link>
          <button onClick={handleLogout} className="sidebar-link w-full text-left">
            <span className="text-lg">🚪</span>
            {sidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-h-screen overflow-auto">
        {/* Topbar */}
        <header
          className="flex items-center justify-between px-6 h-[60px] sticky top-0 z-40"
          style={{
            background: 'rgba(15,23,42,0.95)',
            backdropFilter: 'blur(8px)',
            borderBottom: '1px solid var(--color-dark-border)',
          }}
        >
          <div>
            <span className="text-sm font-semibold" style={{ fontFamily: 'var(--font-display)' }}>
              Port Dashboard
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs" style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-code)' }}>
              🟢 {currentTime}
            </span>
            <div className="relative">
              <button
                onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg transition-colors"
                style={{ background: profileDropdownOpen ? 'rgba(255,255,255,0.05)' : 'transparent' }}
              >
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
                     style={{ background: 'var(--color-primary)', color: 'white' }}>
                  {user?.full_name?.[0] || 'U'}
                </div>
                {sidebarOpen && (
                  <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                    {user?.full_name || 'User'}
                  </span>
                )}
              </button>

              <div className={`profile-dropdown ${profileDropdownOpen ? 'show' : ''}`}>
                <div className="px-3 py-2 mb-1" style={{ borderBottom: '1px solid var(--color-dark-border)' }}>
                  <p className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                    {user?.full_name || 'User'}
                  </p>
                  <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                    {user?.email || 'user@baos.ai'}
                  </p>
                </div>
                <button className="profile-dropdown-item">👤 Profile</button>
                <button className="profile-dropdown-item">⚙️ Settings</button>
                <button className="profile-dropdown-item" onClick={handleLogout}>🚪 Logout</button>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>

      {/* ── Toast Notifications ──────────────────────────── */}
      {toasts.length > 0 && (
        <div className="toast-container">
          {toasts.map(t => (
            <div key={t.id} className={`toast toast-${t.type}`} onClick={() => removeToast(t.id)}>
              {t.type === 'success' && '✅'}
              {t.type === 'error' && '❌'}
              {t.type === 'info' && 'ℹ️'}
              {t.type === 'warning' && '⚠️'}
              {t.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
