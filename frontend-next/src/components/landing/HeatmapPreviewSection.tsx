'use client';

import SectionHeader from '@/components/common/SectionHeader';
import UtilizationHeatmap from '@/components/charts/UtilizationHeatmap';
import SourceBadge from '@/components/common/SourceBadge';
import Reveal from '@/components/common/Reveal';

export default function HeatmapPreviewSection() {
  return (
    <section className="baos-section bg-slate-50/50 border-b border-slate-100">
      <div className="baos-container">
        <div className="flex flex-col items-center mb-6">
          <SourceBadge source="DEMO" className="mb-4" />
          <SectionHeader
            title="Berth Occupancy Heatmap"
            subtitle="Weekly occupancy visualizer detailing high and low traffic periods across berths"
            className="!mb-8"
          />
        </div>

        <Reveal>
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <UtilizationHeatmap />
          </div>
        </Reveal>
      </div>
    </section>
  );
}
