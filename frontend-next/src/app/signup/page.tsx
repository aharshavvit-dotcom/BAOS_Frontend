/**
 * BAOS AI — Signup Page
 * Multi-step form matching signup.html
 */
'use client';

import { useState, FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

const STEPS = [
  { label: 'Company', num: 1 },
  { label: 'Personal', num: 2 },
  { label: 'Confirm', num: 3 },
];

function PasswordStrength({ password }: { password: string }) {
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  let label = '', colorClass = '';
  if (score <= 1) { label = 'Weak'; colorClass = 'weak'; }
  else if (score <= 2) { label = 'Fair'; colorClass = 'medium'; }
  else if (score <= 3) { label = 'Good'; colorClass = 'medium'; }
  else { label = 'Strong'; colorClass = 'strong'; }

  const barsActive = score <= 1 ? 1 : score <= 2 ? 2 : score <= 3 ? 3 : 4;

  if (!password) return null;

  return (
    <div className="mt-2">
      <div className="password-strength-bars">
        {[0, 1, 2, 3].map(i => (
          <div key={i} className={`password-strength-bar ${i < barsActive ? colorClass : ''}`} />
        ))}
      </div>
      <span className="text-xs mt-1 inline-block" style={{
        color: colorClass === 'weak' ? 'var(--color-danger)' : colorClass === 'medium' ? 'var(--color-warning)' : 'var(--color-success)'
      }}>
        {label}
      </span>
    </div>
  );
}

export default function SignupPage() {
  const router = useRouter();
  const { signup, isLoading, error, clearError } = useAuthStore();

  const [step, setStep] = useState(1);
  const [showSuccess, setShowSuccess] = useState(false);

  // Form data
  const [company, setCompany] = useState('');
  const [port, setPort] = useState('Chennai');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Errors
  const [errors, setErrors] = useState<Record<string, string>>({});

  function validateStep(s: number): boolean {
    const errs: Record<string, string> = {};

    if (s === 1) {
      if (!company.trim()) errs.company = 'Company name is required';
    }

    if (s === 2) {
      if (!fullName.trim()) errs.fullName = 'Full name is required';
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errs.email = 'Valid email required';
      if (password.length < 8) errs.password = 'Minimum 8 characters';
      if (confirmPassword !== password) errs.confirmPassword = 'Passwords do not match';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function nextStep() {
    if (!validateStep(step)) return;
    setStep(step + 1);
  }

  function prevStep() {
    setStep(step - 1);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    clearError();

    const portCode = port === 'Chennai' ? 'INMAA' : 'INMAA';

    try {
      await signup({
        email,
        password,
        full_name: fullName,
        company,
        port_code: portCode,
      });

      setShowSuccess(true);
      setTimeout(() => router.push('/dashboard'), 2000);
    } catch {
      // Error from store
    }
  }

  if (showSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--color-dark)' }}>
        <div className="text-center animate-fade-in-up">
          <div className="text-6xl mb-4">✅</div>
          <h2 className="text-2xl font-bold mb-2" style={{ fontFamily: 'var(--font-display)' }}>Account Created!</h2>
          <p style={{ color: 'var(--color-text-muted)' }}>Redirecting to your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--color-dark)' }}>
      {/* ── Left Panel ───────────────────────────────────── */}
      <div
        className="hidden lg:flex flex-col justify-center p-12 flex-1"
        style={{
          background: 'linear-gradient(135deg, #0F172A 0%, #1E3A5F 50%, #0F172A 100%)',
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
            Join the Future of Port Management
          </h2>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)', lineHeight: 1.7 }}>
            Create your account and start optimizing berth allocations with AI-powered intelligence.
          </p>
        </div>
      </div>

      {/* ── Right Panel ──────────────────────────────────── */}
      <div className="flex flex-col justify-center items-center flex-1 p-8">
        <div className="w-full max-w-[440px]">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8 justify-center">
            <span className="text-3xl">🚢</span>
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 24, color: 'var(--color-text-primary)' }}>
              BAOS <span style={{ color: 'var(--color-primary)' }}>AI</span>
            </span>
          </div>

          <h1 className="text-2xl font-bold mb-2" style={{ fontFamily: 'var(--font-display)' }}>Create Account</h1>
          <p className="text-sm mb-8" style={{ color: 'var(--color-text-muted)' }}>Set up your port management profile</p>

          {/* Step Progress */}
          <div className="step-progress mb-8">
            {STEPS.map((s, i) => (
              <div key={s.num} className="contents">
                <div className={`step-item ${step === s.num ? 'active' : step > s.num ? 'completed' : ''}`} data-step={s.num}>
                  <div className="step-circle">{step > s.num ? '✓' : s.num}</div>
                  <div className="step-label">{s.label}</div>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`step-line ${step > s.num ? 'completed' : ''}`}></div>
                )}
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit}>
            {/* Step 1: Company */}
            {step === 1 && (
              <div className="space-y-5 animate-fade-in">
                <div>
                  <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                    Company Name *
                  </label>
                  <input
                    type="text"
                    className={`form-input ${errors.company ? 'error' : ''}`}
                    placeholder="Enter your company name"
                    value={company}
                    onChange={(e) => { setCompany(e.target.value); setErrors({}); }}
                  />
                  {errors.company && <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>{errors.company}</p>}
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                    Port
                  </label>
                  <select className="form-input" value={port} onChange={(e) => setPort(e.target.value)}>
                    <option>Chennai</option>
                    <option>Mumbai</option>
                    <option>Kolkata</option>
                    <option>Visakhapatnam</option>
                  </select>
                </div>
                <button type="button" onClick={nextStep} className="btn btn-primary w-full btn-lg">Next Step →</button>
              </div>
            )}

            {/* Step 2: Personal */}
            {step === 2 && (
              <div className="space-y-5 animate-fade-in">
                <div>
                  <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--color-text-secondary)' }}>Full Name *</label>
                  <input type="text" className={`form-input ${errors.fullName ? 'error' : ''}`} placeholder="Your full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
                  {errors.fullName && <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>{errors.fullName}</p>}
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--color-text-secondary)' }}>Email Address *</label>
                  <input type="email" className={`form-input ${errors.email ? 'error' : ''}`} placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} />
                  {errors.email && <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>{errors.email}</p>}
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--color-text-secondary)' }}>Password *</label>
                  <input type="password" className={`form-input ${errors.password ? 'error' : ''}`} placeholder="Min 8 characters" value={password} onChange={(e) => setPassword(e.target.value)} />
                  <PasswordStrength password={password} />
                  {errors.password && <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>{errors.password}</p>}
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-2" style={{ color: 'var(--color-text-secondary)' }}>Confirm Password *</label>
                  <input type="password" className={`form-input ${errors.confirmPassword ? 'error' : ''}`} placeholder="Re-enter password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
                  {errors.confirmPassword && <p className="text-xs mt-1" style={{ color: 'var(--color-danger)' }}>{errors.confirmPassword}</p>}
                </div>
                <div className="flex gap-3">
                  <button type="button" onClick={prevStep} className="btn btn-secondary flex-1 btn-lg">← Back</button>
                  <button type="button" onClick={nextStep} className="btn btn-primary flex-1 btn-lg">Next Step →</button>
                </div>
              </div>
            )}

            {/* Step 3: Confirm */}
            {step === 3 && (
              <div className="space-y-5 animate-fade-in">
                <div className="card-flat">
                  <h3 className="text-sm font-bold mb-4" style={{ fontFamily: 'var(--font-display)' }}>Review Your Details</h3>
                  <div className="space-y-3 text-sm">
                    {[
                      ['Company', company],
                      ['Port', port],
                      ['Name', fullName],
                      ['Email', email],
                    ].map(([label, value]) => (
                      <div key={label} className="flex justify-between">
                        <span style={{ color: 'var(--color-text-muted)' }}>{label}</span>
                        <span style={{ color: 'var(--color-text-primary)', fontWeight: 600 }}>{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <label className="flex items-start gap-3 text-sm cursor-pointer" style={{ color: 'var(--color-text-muted)' }}>
                  <input type="checkbox" className="accent-[var(--color-primary)] mt-1" defaultChecked />
                  I agree to the Terms of Service and Privacy Policy
                </label>

                {error && (
                  <div className="p-3 rounded-lg text-sm" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid var(--color-danger)', color: 'var(--color-danger)' }}>
                    {error}
                  </div>
                )}

                <div className="flex gap-3">
                  <button type="button" onClick={prevStep} className="btn btn-secondary flex-1 btn-lg">← Back</button>
                  <button type="submit" disabled={isLoading} className="btn btn-primary flex-1 btn-lg">
                    {isLoading ? 'Creating...' : 'Create Account'}
                  </button>
                </div>
              </div>
            )}
          </form>

          <p className="text-center text-sm mt-6" style={{ color: 'var(--color-text-muted)' }}>
            Already have an account?{' '}
            <Link href="/login" style={{ color: 'var(--color-primary)', fontWeight: 600 }}>Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
