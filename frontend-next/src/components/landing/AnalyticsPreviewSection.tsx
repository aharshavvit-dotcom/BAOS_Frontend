'use client';

import SectionHeader from '@/components/common/SectionHeader';
import ChartCard from '@/components/common/ChartCard';
import SourceBadge from '@/components/common/SourceBadge';
import Reveal from '@/components/common/Reveal';

import BerthUtilizationChart from '@/components/charts/BerthUtilizationChart';
import TurnaroundTrendChart from '@/components/charts/TurnaroundTrendChart';
import CostRevenueChart from '@/components/charts/CostRevenueChart';
import VesselMixChart from '@/components/charts/VesselMixChart';

export default function AnalyticsPreviewSection() {
  return (
    <section id="analytics" className="baos-section bg-white border-b border-slate-100">
      <div className="baos-container-wide">
        <div className="flex flex-col items-center mb-6">
          <SourceBadge source="DEMO" className="mb-4" />
          <SectionHeader
            title="Operational Insights & Analytics"
            subtitle="Explore simulated performance distributions, turnaround rates, and commercial trends"
            className="!mb-8"
          />
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2 mt-12">
          <Reveal delay={0}>
            <ChartCard
              title="Berth Utilization"
              subtitle="Comparison of actual occupancy compared to target optimal utilization rate"
            >
              <BerthUtilizationChart />
            </ChartCard>
          </Reveal>

          <Reveal delay={100}>
            <ChartCard
              title="Vessel Turnaround Trend"
              subtitle="Weekly average vessel turnaround times against standard targets"
            >
              <TurnaroundTrendChart />
            </ChartCard>
          </Reveal>

          <Reveal delay={200}>
            <ChartCard
              title="Revenue vs Operational Cost"
              subtitle="Comparative overview of simulated revenue generated vs wait-associated costs"
            >
              <CostRevenueChart />
            </ChartCard>
          </Reveal>

          <Reveal delay={300}>
            <ChartCard
              title="Vessel Mix Distribution"
              subtitle="Distribution of vessel types processed within the simulation period"
            >
              <VesselMixChart />
            </ChartCard>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
