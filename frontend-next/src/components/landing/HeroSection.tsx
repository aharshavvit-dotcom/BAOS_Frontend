'use client';

import Link from 'next/link';
import AnimatedCounter from '@/components/common/AnimatedCounter';

function HeroMockDashboard() {
  return (
    <div className="relative rounded-2xl border border-slate-200 bg-white p-6 shadow-xl animate-fade-in-up">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-rose-500" />
          <span className="h-3 w-3 rounded-full bg-amber-500" />
          <span className="h-3 w-3 rounded-full bg-emerald-500" />
        </div>
        <div className="rounded bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-500">
          DEMO MODE ACTIVE
        </div>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-slate-50 p-3 border border-slate-100">
            <p className="text-[10px] uppercase font-bold text-slate-400">Total Port Calls</p>
            <p className="text-lg font-extrabold text-slate-700 mt-1">908 Vessels</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 border border-slate-100">
            <p className="text-[10px] uppercase font-bold text-slate-400">Berth Efficiency</p>
            <p className="text-lg font-extrabold text-emerald-600 mt-1">84.2%</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 border border-slate-100">
            <p className="text-[10px] uppercase font-bold text-slate-400">Avg Wait Time</p>
            <p className="text-lg font-extrabold text-amber-600 mt-1">1.8 hrs</p>
          </div>
        </div>

        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-bold text-slate-700">Berth Allocation Recommendation</p>
            <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-[10px] font-extrabold text-blue-800">
              AI PROPOSAL
            </span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-xs border-b border-slate-100 pb-1.5">
              <span className="font-semibold text-slate-500">Vessel: MV Orange Wave</span>
              <span className="font-bold text-slate-800">Assign to: Berth 3</span>
            </div>
            <div className="flex justify-between text-xs border-b border-slate-100 pb-1.5">
              <span className="font-semibold text-slate-500">Draft Margin</span>
              <span className="font-bold text-emerald-600">+1.5m (Safe)</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="font-semibold text-slate-500">Decision Confidence</span>
              <span className="font-bold text-blue-600">92.5%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function HeroSection() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-slate-50 via-white to-blue-50/50 border-b border-slate-100">
      {/* Decorative Glow Blobs */}
      <div className="absolute top-[-100px] left-[-100px] h-[350px] w-[350px] rounded-full bg-blue-400/5 blur-3xl pointer-events-none" />
      <div className="absolute bottom-[-100px] right-[-100px] h-[350px] w-[350px] rounded-full bg-teal-400/5 blur-3xl pointer-events-none" />

      <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-12 px-6 py-16 lg:py-24 min-h-[calc(100vh-5rem)] lg:grid-cols-2">
        <div className="text-left animate-fade-in-up">
          <div className="inline-block px-3 py-1 rounded-full text-xs font-semibold mb-6 bg-blue-50 border border-blue-200 text-blue-600">
            🚀 Maritime Decision Intelligence Platform
          </div>

          <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl lg:text-6xl leading-tight">
            Optimize Your Port with
            <span className="block bg-gradient-to-r from-blue-600 to-teal-500 bg-clip-text text-transparent mt-2">
              Decision Intelligence
            </span>
          </h1>

          <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-600">
            AI-assisted berth allocation that supports faster planning, better utilization,
            and explainable optimization decisions directly from database records.
          </p>

          <div className="mt-8 flex flex-col gap-4 sm:flex-row">
            <Link
              href="/login"
              className="rounded-xl bg-blue-600 px-6 py-4 text-center text-sm font-semibold text-white shadow-md hover:bg-blue-500 hover:shadow-lg transition-all"
            >
              Get Started Free →
            </Link>
            <a
              href="#features"
              className="rounded-xl border border-slate-200 bg-white px-6 py-4 text-center text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 transition-all"
            >
              Learn More
            </a>
          </div>

          {/* Quick Counter Stats */}
          <div className="mt-12 grid grid-cols-3 gap-6 border-t border-slate-100 pt-8">
            <div>
              <div className="text-2xl font-extrabold text-blue-600 sm:text-3xl">
                <AnimatedCounter target={94} suffix="%" />
              </div>
              <p className="text-xs font-semibold text-slate-500 mt-1">SLA Compliance <span className="text-[10px] text-slate-400">(DEMO)</span></p>
            </div>
            <div>
              <div className="text-2xl font-extrabold text-blue-600 sm:text-3xl">
                <AnimatedCounter target={26.5} suffix="h" decimals={1} />
              </div>
              <p className="text-xs font-semibold text-slate-500 mt-1">Avg Turnaround <span className="text-[10px] text-slate-400">(HISTORICAL)</span></p>
            </div>
            <div>
              <div className="text-2xl font-extrabold text-blue-600 sm:text-3xl">
                <AnimatedCounter target={480} prefix="$" suffix="K" />
              </div>
              <p className="text-xs font-semibold text-slate-500 mt-1">Monthly Revenue <span className="text-[10px] text-slate-400">(ASSUMPTION)</span></p>
            </div>
          </div>
        </div>

        <div className="flex flex-col justify-center">
          <HeroMockDashboard />
        </div>
      </div>
    </section>
  );
}
