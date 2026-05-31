'use client';

import SectionHeader from '@/components/ui/SectionHeader';
import Reveal from '@/components/ui/Reveal';

import { Brain, BarChart3, Zap, DollarSign, RefreshCw, Shield } from 'lucide-react';

const features = [
  {
    icon: Brain,
    iconColor: 'text-blue-600',
    bgColor: 'bg-blue-50',
    title: 'AI-Powered Optimization',
    desc: 'Machine learning models analyze historical port calls to propose the most suitable berth candidates.',
  },
  {
    icon: BarChart3,
    iconColor: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    title: 'Operational Analytics',
    desc: 'Simulated dashboard charts, utilization trends, and historical metrics for unified port visibility.',
  },
  {
    icon: Zap,
    iconColor: 'text-amber-600',
    bgColor: 'bg-amber-50',
    title: 'Constraint Solver',
    desc: 'CP-SAT constraint programming engine checks 15+ physical boundaries like LOA limits, draft, and tides.',
  },
  {
    icon: DollarSign,
    iconColor: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
    title: 'Commercial Intelligence',
    desc: 'Contract rules calculation tracking wait costs, SLA penalties, and simulated revenue metrics.',
  },
  {
    icon: RefreshCw,
    iconColor: 'text-purple-600',
    bgColor: 'bg-purple-50',
    title: 'Continuous Learning',
    desc: 'Evaluation loops log actual turnaround times to retrain decision limits and keep predictions accurate.',
  },
  {
    icon: Shield,
    iconColor: 'text-rose-600',
    bgColor: 'bg-rose-50',
    title: 'Access Management',
    desc: 'Secure token-based auth credentials, role assignments, and audit logging out of the box.',
  },
];

export default function FeatureCardsSection() {
  return (
    <section id="features" className="baos-section bg-slate-50 border-b border-slate-100 py-20 lg:py-24">
      <div className="baos-container">
        <SectionHeader
          eyebrow="Maritime Decision Suite"
          title="Enterprise-grade tools for modern port operations"
          subtitle="Connect physical capabilities, mathematical constraints, and data-driven insights."
        />

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((f, i) => {
            const IconComponent = f.icon;
            return (
              <Reveal key={i} delay={i * 100}>
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-300 h-full flex flex-col justify-between">
                  <div>
                    <div className={`inline-flex items-center justify-center p-3 rounded-lg ${f.bgColor} ${f.iconColor} mb-4`}>
                      <IconComponent size={24} />
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 mb-2">
                      {f.title}
                    </h3>
                    <p className="text-sm text-slate-500 leading-relaxed">
                      {f.desc}
                    </p>
                  </div>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
