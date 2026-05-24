import LandingNavbar from '@/components/layout/LandingNavbar';
import HeroSection from '@/components/landing/HeroSection';
import FeatureCardsSection from '@/components/landing/FeatureCardsSection';
import MetricsPreviewSection from '@/components/landing/MetricsPreviewSection';
import AnalyticsPreviewSection from '@/components/landing/AnalyticsPreviewSection';
import HeatmapPreviewSection from '@/components/landing/HeatmapPreviewSection';
import CTASection from '@/components/landing/CTASection';
import LandingFooter from '@/components/layout/LandingFooter';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <LandingNavbar />
      <main className="pt-20">
        <HeroSection />
        <FeatureCardsSection />
        <MetricsPreviewSection />
        <AnalyticsPreviewSection />
        <HeatmapPreviewSection />
        <CTASection />
      </main>
      <LandingFooter />
    </div>
  );
}
