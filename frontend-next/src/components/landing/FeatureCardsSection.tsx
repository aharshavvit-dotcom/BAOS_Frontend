'use client';

import SectionHeader from '@/components/common/SectionHeader';
import Reveal from '@/components/common/Reveal';

const features = [
  {
    icon: '🤖',
    title: 'AI-Powered Optimization',
    desc: 'Machine learning models analyze historical port calls to propose the most suitable berth candidates.',
  },
  {
    icon: '📊',
    title: 'Operational Analytics',
    desc: 'Simulated dashboard charts, utilization trends, and historical metrics for unified port visibility.',
  },
  {
    icon: '⚡',
    title: 'Constraint Solver',
    desc: 'CP-SAT constraint programming engine checks 15+ physical boundaries like LOA limits, draft, and tides.',
  },
  {
    icon: '💰',
    title: 'Commercial Intelligence',
    desc: 'Contract rules calculation tracking wait costs, SLA penalties, and simulated revenue metrics.',
  },
  {
    icon: '🔄',
    title: 'Continuous Learning',
    desc: 'Evaluation loops log actual turnaround times to retrain decision limits and keep predictions accurate.',
  },
  {
    icon: '🛡️',
    title: 'Access Management',
    desc: 'Secure token-based auth credentials, role assignments, and audit logging out of the box.',
  },
];

export default function FeatureCardsSection() {
  return (
    <section id="features" className="baos-section bg-white border-b border-slate-100">
      <div className="baos-container">
        <SectionHeader
          eyebrow="Maritime Decision Suite"
          title="Enterprise-grade tools for modern port operations"
          subtitle="Connect physical capabilities, mathematical constraints, and data-driven insights."
        />

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((f, i) => (
            <Reveal key={i} delay={i * 100}>
              <div className="premium-card h-full flex flex-col justify-between">
                <div>
                  <div className="text-3xl mb-4">{f.icon}</div>
                  <h3 className="text-lg font-bold text-slate-900 mb-2">
                    {f.title}
                  </h3>
                  <p className="text-sm text-slate-500 leading-relaxed">
                    {f.desc}
                  </p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
