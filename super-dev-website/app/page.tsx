import { Nav } from '@/components/layout/Nav';
import { Footer } from '@/components/layout/Footer';
import { HeroSection } from '@/components/sections/HeroSection';
import { HostMarquee } from '@/components/sections/HostMarquee';
import { SocialProofBand } from '@/components/sections/SocialProofBand';
import { ValuePropsSection } from '@/components/sections/ValuePropsSection';
import { WhoItsForSection } from '@/components/sections/WhoItsForSection';
import { UseCasesSection } from '@/components/sections/UseCasesSection';
import { PipelineSection } from '@/components/sections/PipelineSection';
import { HostCompatSection } from '@/components/sections/HostCompatSection';
import { CodeDemoSection } from '@/components/sections/CodeDemoSection';
import { FaqSection } from '@/components/sections/FaqSection';
import { BottomCta } from '@/components/sections/BottomCta';

export default function HomePage() {
  return (
    <>
      <Nav locale="zh" />
      <main id="main-content" lang="zh">
        <HeroSection locale="zh" />
        <HostMarquee locale="zh" />
        <SocialProofBand locale="zh" />
        <ValuePropsSection locale="zh" />
        <WhoItsForSection locale="zh" />
        <UseCasesSection locale="zh" />
        <PipelineSection locale="zh" />
        <HostCompatSection locale="zh" />
        <CodeDemoSection locale="zh" />
        <FaqSection locale="zh" />
        <BottomCta locale="zh" />
      </main>
      <Footer locale="zh" />
    </>
  );
}
