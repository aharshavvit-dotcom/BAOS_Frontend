'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function LandingNavbar() {
  const [navScrolled, setNavScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setNavScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 h-20 border-b transition-all duration-300 ${
        navScrolled
          ? 'border-slate-200 bg-white/95 backdrop-blur-md shadow-sm'
          : 'border-transparent bg-white/90 backdrop-blur-xl'
      }`}
    >
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2 no-underline">
          <span className="text-2xl">🚢</span>
          <span className="font-extrabold text-xl tracking-tight text-slate-900">
            BAOS <span className="text-blue-600">AI</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          <a href="#features" className="text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors">
            Features
          </a>
          <a href="#metrics" className="text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors">
            Metrics
          </a>
          <a href="#analytics" className="text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors">
            Analytics
          </a>
        </nav>

        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 hover:text-slate-900 transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 transition-colors"
          >
            Get Started
          </Link>
        </div>
      </div>
    </header>
  );
}
