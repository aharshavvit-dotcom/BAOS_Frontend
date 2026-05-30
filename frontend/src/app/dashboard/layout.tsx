/**
 * Dashboard Layout â€” Sidebar + Topbar + Protected Route
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
  const { sidebarOpen, toasts, removeToast } = useUIStore();
  const [currentTime, setCurrentTime] = useState('');

  // Live time
  useEffect(() => {
    function updateTime() {
      setCurrentTime(new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    }
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--color-dark)' }}>
      {/* Sidebar */}
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
          <span className="text-2xl">ðŸš¢</span>
          {sidebarOpen && (
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 18, color: 'var(--color-text-primary)' }}>
              BAOS <span style={{ color: 'var(--color-primary)' }}>AI</span>
            </span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1">
          {[
            { icon: 'ðŸ“Š', label: 'Dashboard', href: '/dashboard' },
            { icon: 'ðŸ§ ', label: 'Get Recommendation', href: '/dashboard/recommend' },
            { icon: 'ðŸš€', label: 'Optimizer', href: '/dashboard/optimizer' },
            { icon: 'ðŸ’°', label: 'Commercial Intel', href: '/dashboard/commercial' },
            { icon: 'ðŸ“ˆ', label: 'Analytics', href: '/dashboard/analytics' },
            { icon: 'ðŸ””', label: 'Alerts', href: '/dashboard/alerts' },
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
            <span className="text-lg">âš™ï¸</span>
            {sidebarOpen && <span>Settings</span>}
          </Link>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen overflow-auto">
        {/* Topbar */}
        <header
          className="flex items-center justify-between px-6 h-[60px] sticky top-0 z-40"
          style={{
            background: 'rgba(255,255,255,0.95)',
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
              ðŸŸ¢ {currentTime}
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6">
          <div className="mx-auto max-w-7xl">
          {children}
          </div>
        </main>
      </div>

      {/* Toast Notifications */}
      {toasts.length > 0 && (
        <div className="toast-container">
          {toasts.map(t => (
            <div key={t.id} className={`toast toast-${t.type}`} onClick={() => removeToast(t.id)}>
              {t.type === 'success' && 'âœ…'}
              {t.type === 'error' && 'âŒ'}
              {t.type === 'info' && 'â„¹ï¸'}
              {t.type === 'warning' && 'âš ï¸'}
              {t.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
