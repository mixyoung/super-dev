import type { Metadata } from 'next';
import { Nav } from '@/components/layout/Nav';
import { Footer } from '@/components/layout/Footer';
import { HeroSection } from '@/components/sections/HeroSection';
import { SocialProofBand } from '@/components/sections/SocialProofBand';
import { ValuePropsSection } from '@/components/sections/ValuePropsSection';
import { WhoItsForSection } from '@/components/sections/WhoItsForSection';
import { UseCasesSection } from '@/components/sections/UseCasesSection';
import { PipelineSection } from '@/components/sections/PipelineSection';
import { HostCompatSection } from '@/components/sections/HostCompatSection';
import { CodeDemoSection } from '@/components/sections/CodeDemoSection';
import { FaqSection } from '@/components/sections/FaqSection';
import { BottomCta } from '@/components/sections/BottomCta';

export const metadata: Metadata = {
  title: 'Super Dev — The Governance Layer for AI Coding',
  description: 'Super Dev governs how AI hosts deliver work: research, the three core docs, approval gates, runtime validation, quality gates, and auditable delivery outputs.',
};

export default function HomePageEn() {
  return (
    <>
      <Nav locale="en" />
      <main id="main-content" lang="en">
        <HeroSection locale="en" />
        <SocialProofBand locale="en" />
        <ValuePropsSection locale="en" />
        <WhoItsForSection locale="en" />
        <UseCasesSection locale="en" />
        <PipelineSection locale="en" />
        <HostCompatSection locale="en" />
        <CodeDemoSection locale="en" />
        <FaqSection locale="en" />
        <BottomCta locale="en" />
      </main>
      <Footer locale="en" />
    </>
  );
}
