'use client';

import Link from 'next/link';
import Reveal from '@/components/ui/Reveal';
import { ArrowRight } from 'lucide-react';

export default function CTASection() {
  return (
    <section className="bg-slate-50 px-6 py-20">
      <div className="mx-auto max-w-4xl">
        <Reveal>
          <div className="rounded-3xl bg-gradient-to-r from-blue-600 to-teal-500 p-10 text-center text-white shadow-xl">
            <h2 className="text-3xl font-extrabold tracking-tight">
              Ready to Optimize Your Port?
            </h2>
            <p className="mt-3 text-lg text-blue-50">
              Start using AI-assisted berth allocation with explainable decision support.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row justify-center items-center gap-6">
              <Link
                href="/login"
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-white px-6 py-4 text-sm font-bold text-slate-900 shadow-lg hover:bg-slate-50 hover:scale-[1.02] transition-all"
              >
                Start Free Trial <ArrowRight size={16} />
              </Link>
              <Link
                href="/login"
                className="inline-flex items-center justify-center gap-1 py-4 text-sm font-bold text-white hover:underline transition-all"
              >
                Sign In <ArrowRight size={14} className="inline-block ml-1" />
              </Link>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
