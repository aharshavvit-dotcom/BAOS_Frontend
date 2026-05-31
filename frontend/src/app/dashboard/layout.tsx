/**
 * Dashboard Layout — Sidebar + Topbar + Protected Route
 * FIX (Phase 6): Added mobile hamburger toggle, click-outside-to-close, ErrorBoundary wrapping.
 */
'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useUIStore } from '@/store/uiStore';
import { useSocket } from '@/hooks/useSocket';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import {
  LayoutDashboard, Brain, Rocket, Coins, BarChart3, Bell,
  Settings, Ship, Menu, CheckCircle2, XCircle, Info, AlertTriangle,
} from 'lucide-react';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { sidebarOpen, setSidebarOpen, toasts, removeToast } = useUIStore();
  const [currentTime, setCurrentTime] = useState('');
  // FIX (Phase 6): Mobile sidebar state — separate from desktop collapse
  const [mobileOpen, setMobileOpen] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);

  // Live time
  useEffect(() => {
    function updateTime() {
      setCurrentTime(new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    }
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // FIX (Phase 6): Click outside sidebar to close on mobile
  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (mobileOpen && sidebarRef.current && !sidebarRef.current.contains(e.target as Node)) {
      setMobileOpen(false);
    }
  }, [mobileOpen]);

  useEffect(() => {
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [handleClickOutside]);

  // Close mobile sidebar on navigation
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const navItems = [
    { icon: <LayoutDashboard size={20} />, label: 'Dashboard', href: '/dashboard' },
    { icon: <Brain size={20} />, label: 'Get Recommendation', href: '/dashboard/recommend' },
    { icon: <Rocket size={20} />, label: 'Optimizer', href: '/dashboard/optimizer' },
    { icon: <Coins size={20} />, label: 'Commercial Intel', href: '/dashboard/commercial' },
    { icon: <BarChart3 size={20} />, label: 'Analytics', href: '/dashboard/analytics' },
    { icon: <Bell size={20} />, label: 'Alerts', href: '/dashboard/alerts' },
  ];

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--color-dark)' }}>
      {/* FIX (Phase 6): Mobile overlay backdrop */}
      {mobileOpen && (
        <div
          className="sidebar-overlay"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            zIndex: 49,
          }}
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        ref={sidebarRef}
        className={`flex-shrink-0 flex flex-col border-r h-screen sticky top-0 transition-all duration-300 sidebar-desktop ${mobileOpen ? 'sidebar-mobile-open' : ''}`}
        style={{
          width: sidebarOpen ? 260 : 72,
          background: 'var(--color-dark-card)',
          borderColor: 'var(--color-dark-border)',
        }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 p-5" style={{ borderBottom: '1px solid var(--color-dark-border)' }}>
          <Ship size={28} className="text-[var(--color-primary)]" />
          {sidebarOpen && (
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 18, color: 'var(--color-text-primary)' }}>
              BAOS <span style={{ color: 'var(--color-primary)' }}>AI</span>
            </span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item, i) => (
            <Link
              key={i}
              href={item.href}
              className={`sidebar-link ${pathname === item.href ? 'active' : ''}`}
              title={item.label}
            >
              <span className="flex-shrink-0">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* Bottom nav */}
        <div className="p-3 space-y-1" style={{ borderTop: '1px solid var(--color-dark-border)' }}>
          <Link href="#" className="sidebar-link">
            <Settings size={20} />
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
          <div className="flex items-center gap-3">
            {/* FIX (Phase 6): Mobile hamburger toggle */}
            <button
              className="sidebar-hamburger"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label="Toggle sidebar"
              style={{
                display: 'none',
                background: 'none',
                border: 'none',
                fontSize: '1.5rem',
                cursor: 'pointer',
                padding: '0.25rem',
                lineHeight: 1,
              }}
            >
              <Menu size={24} />
            </button>
            <span className="text-sm font-semibold" style={{ fontFamily: 'var(--font-display)' }}>
              Port Dashboard
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-code)' }}>
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              {currentTime}
            </span>
          </div>
        </header>

        {/* Page content — wrapped in ErrorBoundary */}
        <main className="flex-1 p-6">
          <div className="mx-auto max-w-7xl">
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </div>
        </main>
      </div>

      {/* Toast Notifications */}
      {toasts.length > 0 && (
        <div className="toast-container">
          {toasts.map(t => (
            <div key={t.id} className={`toast toast-${t.type}`} onClick={() => removeToast(t.id)}>
              {t.type === 'success' && <CheckCircle2 size={16} className="text-emerald-500 flex-shrink-0" />}
              {t.type === 'error' && <XCircle size={16} className="text-red-500 flex-shrink-0" />}
              {t.type === 'info' && <Info size={16} className="text-sky-500 flex-shrink-0" />}
              {t.type === 'warning' && <AlertTriangle size={16} className="text-amber-500 flex-shrink-0" />}
              {t.message}
            </div>
          ))}
        </div>
      )}

      {/* FIX (Phase 6): Mobile-responsive sidebar styles */}
      <style>{`
        @media (max-width: 768px) {
          .sidebar-desktop {
            position: fixed !important;
            left: -280px;
            z-index: 50;
            transition: left 0.3s ease;
          }
          .sidebar-mobile-open {
            left: 0 !important;
            width: 260px !important;
          }
          .sidebar-hamburger {
            display: inline-flex !important;
          }
        }
      `}</style>
    </div>
  );
}
