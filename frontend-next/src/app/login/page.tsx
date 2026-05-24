/**
 * BAOS AI — Login Page
 * 2-column layout matching login.html
 */
'use client';

import { useState, useEffect, FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading, error, clearError } = useAuthStore();

  const [mounted, setMounted] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');

  useEffect(() => {
    setMounted(true);
    clearError();
  }, [clearError]);

  const isValidEmail = (e: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    clearError();
    setEmailError('');
    setPasswordError('');

    let valid = true;
    if (!email || !isValidEmail(email)) {
      setEmailError('Please enter a valid email address');
      valid = false;
    }
    if (!password || password.length < 4) {
      setPasswordError('Please enter your password');
      valid = false;
    }
    if (!valid) return;

    try {
      await login({ email, password });
      router.push('/dashboard');
    } catch {
      // Error already set in store
    }
  }

  function handleSocialLogin(provider: string) {
    // Mock social login for demo
    localStorage.setItem('baos_access_token', `demo_${provider}_${Date.now()}`);
    localStorage.setItem('baos_refresh_token', `refresh_${provider}_${Date.now()}`);
    useAuthStore.getState().setUser({
      id: 'demo',
      email: `user@${provider.toLowerCase()}.com`,
      full_name: `${provider} User`,
      company: 'Port Authority',
      port_code: 'INMAA',
      port_name: 'Chennai',
      role: 'operator',
    });
    router.push('/dashboard');
  }

  if (!mounted) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--color-dark)' }}>
        <div className="animate-spin text-3xl">🚢</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--color-dark)' }}>
      {/* ── Left Panel (brand) ───────────────────────────── */}
      <div
        className="hidden lg:flex flex-col justify-center p-12 flex-1"
        style={{
          background: 'linear-gradient(135deg, #F8FAFC 0%, #E2E8F0 50%, #F8FAFC 100%)',
          borderRight: '1px solid var(--color-dark-border)',
        }}
      >
        <div className="max-w-[400px]">
          <div className="flex items-center gap-3 mb-8">
            <span className="text-4xl">🚢</span>
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 28, color: 'var(--color-text-primary)' }}>
              BAOS <span style={{ color: 'var(--color-primary)' }}>AI</span>
            </span>
          </div>
          <h2 className="text-2xl font-bold mb-4" style={{ fontFamily: 'var(--font-display)' }}>
            Maritime Decision Intelligence
          </h2>
          <p className="text-sm mb-8" style={{ color: 'var(--color-text-muted)', lineHeight: 1.7 }}>
            AI-powered berth allocation optimization for modern ports.
            Reduce turnaround time, maximize revenue, and ensure SLA compliance.
          </p>
          <div className="space-y-4">
            {[
              '🤖 AI-Powered Recommendations',
              '📊 Real-time Analytics Dashboard',
              '⚡ CP-SAT Constraint Optimization',
              '💰 Commercial Intelligence',
            ].map((f, i) => (
              <div key={i} className="flex items-center gap-3 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                <span>{f}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Right Panel (form) ───────────────────────────── */}
      <div className="flex flex-col justify-center items-center flex-1 p-8">
        <div className="w-full max-w-[400px]">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8 justify-center">
            <span className="text-3xl">🚢</span>
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 24, color: 'var(--color-text-primary)' }}>
              BAOS <span style={{ color: 'var(--color-primary)' }}>AI</span>
            </span>
          </div>

          <h1 className="text-2xl font-bold mb-2" style={{ fontFamily: 'var(--font-display)' }}>Welcome Back</h1>
          <p className="text-sm mb-8" style={{ color: 'var(--color-text-muted)' }}>Sign in to your account</p>

          {/* Social login */}
          <div className="flex gap-3 mb-6">
            <button type="button" onClick={() => handleSocialLogin('Google')} className="btn btn-secondary flex-1 text-sm">
              🔵 Google
            </button>
            <button type="button" onClick={() => handleSocialLogin('Microsoft')} className="btn btn-secondary flex-1 text-sm">
              🟦 Microsoft
            </button>
          </div>

          <div className="flex items-center gap-3 mb-6">
            <div className="flex-1 h-px" style={{ background: 'var(--color-dark-border)' }}></div>
            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>or</span>
            <div className="flex-1 h-px" style={{ background: 'var(--color-dark-border)' }}></div>
          </div>

          {/* Login form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email */}
            <div>
              <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                Email Address
              </label>
              <div className="form-input-icon">
                <span className="icon">📧</span>
                <input
                  type="email"
                  autoComplete="username email"
                  className={`form-input ${emailError ? 'error' : ''}`}
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); setEmailError(''); }}
                  style={{ paddingLeft: 42 }}
                />
              </div>
              {emailError && <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>{emailError}</p>}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                Password
              </label>
              <div className="form-input-icon relative">
                <span className="icon">🔒</span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  className={`form-input ${passwordError ? 'error' : ''}`}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setPasswordError(''); }}
                  style={{ paddingLeft: 42, paddingRight: 42 }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-lg cursor-pointer bg-transparent border-none"
                >
                  {showPassword ? '🙈' : '👁'}
                </button>
              </div>
              {passwordError && <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>{passwordError}</p>}
            </div>

            {/* Remember + Forgot */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: 'var(--color-text-muted)' }}>
                <input type="checkbox" className="accent-[var(--color-primary)]" />
                Remember me
              </label>
              <a href="#" className="text-sm" style={{ color: 'var(--color-primary)' }}>Forgot password?</a>
            </div>

            {/* Global error */}
            {error && (
              <div className="p-3 rounded-lg text-sm" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid var(--color-danger)', color: 'var(--color-danger)' }}>
                {error}
              </div>
            )}

            {/* Submit */}
            <button type="submit" disabled={isLoading} className="btn btn-primary w-full btn-lg">
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <p className="text-center text-sm mt-6" style={{ color: 'var(--color-text-muted)' }}>
            Don&apos;t have an account?{' '}
            <Link href="/signup" style={{ color: 'var(--color-primary)', fontWeight: 600 }}>Sign up</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
