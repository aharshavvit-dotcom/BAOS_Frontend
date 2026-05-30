'use client';

import SectionHeader from '@/components/ui/SectionHeader';
import KpiCard from '@/components/ui/KpiCard';
import AnimatedCounter from '@/components/ui/AnimatedCounter';
import SourceBadge from '@/components/ui/SourceBadge';
import Reveal from '@/components/ui/Reveal';

export default function MetricsPreviewSection() {
  return (
    <section id="metrics" className="baos-section bg-slate-50/50 border-b border-slate-100">
      <div className="baos-container">
        <div className="flex flex-col items-center mb-6">
          <SourceBadge source="HISTORICAL" className="mb-4" />
          <SectionHeader
            title="Operational Performance Overview"
            subtitle="Operational insights derived from historical log analysis of port records"
            className="!mb-8"
          />
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
          <Reveal delay={0}>
            <KpiCard
              icon="ðŸš¢"
              label="Active Vessels"
              value={<AnimatedCounter target={142} />}
              sublabel="+8.4% compared to prior period"
              tone="blue"
            />
          </Reveal>
          <Reveal delay={100}>
            <KpiCard
              icon="â±ï¸"
              label="Avg Turnaround"
              value={<AnimatedCounter target={26.5} suffix="h" decimals={1} />}
              sublabel="-12% turnaround reduction achieved"
              tone="green"
            />
          </Reveal>
          <Reveal delay={200}>
            <KpiCard
              icon="ðŸ“ˆ"
              label="Berth Utilization"
              value={<AnimatedCounter target={78} suffix="%" />}
              sublabel="Target utilization range: 70% - 85%"
              tone="amber"
            />
          </Reveal>
          <Reveal delay={300}>
            <KpiCard
              icon="ðŸ’°"
              label="Monthly Revenue"
              value={<AnimatedCounter target={480} prefix="$" suffix="K" />}
              sublabel="+14.3% commercial revenue growth"
              tone="slate"
            />
          </Reveal>
        </div>
      </div>
    </section>
  );
}
