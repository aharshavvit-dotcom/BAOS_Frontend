'use client';

import Link from 'next/link';
import Reveal from '@/components/common/Reveal';

export default function CTASection() {
  return (
    <section className="bg-white px-6 py-20">
      <div className="mx-auto max-w-4xl">
        <Reveal>
          <div className="rounded-3xl bg-gradient-to-r from-blue-600 to-teal-500 p-10 text-center text-white shadow-xl">
            <h2 className="text-3xl font-extrabold tracking-tight">
              Ready to Optimize Your Port?
            </h2>
            <p className="mt-3 text-lg text-blue-50">
              Start using AI-assisted berth allocation with explainable decision support.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row justify-center gap-4">
              <Link
                href="/signup"
                className="rounded-xl bg-white px-6 py-3.5 text-sm font-semibold text-blue-600 shadow-md hover:bg-slate-50 transition-colors"
              >
                Start Free Trial →
              </Link>
              <Link
                href="/login"
                className="rounded-xl border border-white/30 bg-white/10 px-6 py-3.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
              >
                Sign In
              </Link>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
