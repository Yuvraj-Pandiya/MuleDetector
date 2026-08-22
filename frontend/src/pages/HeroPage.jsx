import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowRight } from 'lucide-react';
import { CinematicHero } from '@/components/ui/cinematic-landing-hero';
import FeatureShaderCards from '@/components/ui/feature-shader-cards';
import SpecularButton from '@/components/ui/SpecularButton';

export default function HeroPage() {
  const navigate = useNavigate();

  const handleGetInside = () => {
    navigate('/dashboard');
  };

  return (
    <div className="relative overflow-x-hidden w-full min-h-screen bg-neutral-950">
      {/* Top Floating Branding & CTA Layer for Hero Viewport */}
      <header className="fixed top-4 left-4 right-4 md:top-5 md:left-6 md:right-8 z-50 flex items-center justify-between pointer-events-none">
        {/* Top-Left Logo / Branding */}
        <div
          onClick={() => navigate('/')}
          role="button"
          tabIndex={0}
          className="pointer-events-auto flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-neutral-950/70 border border-white/15 backdrop-blur-xl shadow-lg hover:border-blue-400/40 transition-all duration-300 cursor-pointer group"
          title="MuleScope Home"
        >
          <ShieldAlert className="w-4 h-4 text-blue-400 group-hover:scale-110 transition-transform" />
          <span className="text-xs font-black tracking-wider text-white">
            MULE<span className="text-[9px] font-bold bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded ml-1 tracking-widest">SCOPE</span>
          </span>
        </div>

        {/* Top-Right "GET INSIDE" Specular Shader CTA Button */}
        <SpecularButton
          onClick={handleGetInside}
          size="md"
          radius={9999}
          tint="#000000"
          tintOpacity={0.9}
          blur={12}
          textColor="#ffffff"
          lineColor="#ffffff"
          baseColor="#737373"
          intensity={2.2}
          shineSize={25}
          shineFade={50}
          speed={0.5}
          className="pointer-events-auto cursor-pointer shadow-2xl group"
        >
          <span className="flex items-center gap-2 text-xs md:text-sm font-extrabold tracking-wider uppercase text-white">
            GET INSIDE
            <ArrowRight className="w-4 h-4 text-white transition-transform duration-300 group-hover:translate-x-1" />
          </span>
        </SpecularButton>
      </header>

      {/* 1. Hero Viewport Section */}
      <CinematicHero
        brandName="MULE SCOPE"
        tagline1="Real-time fraud detection & risk scoring,"
        tagline2="built for analysts, not just models."
        cardHeading="Explainable AI & Mule Ring Detection"
        cardDescription={
          <>
            Scores accounts in real time, explains every decision with human-readable <span className="text-white font-semibold">SHAP feature attribution</span>, and visualizes transaction networks to expose mule rings instantly.
          </>
        }
        metricValue={1247}
        metricLabel="Accounts Monitored"
        ctaHeading="Uncover Hidden Fraud & Mule Networks"
        ctaDescription="Drag-and-drop CSV dataset upload with column previews, risk-ranked account tables, transparent model performance metrics, and analyst case management."
        onGetStarted={handleGetInside}
        onPrimaryClick={handleGetInside}
        onSecondaryClick={() => navigate('/upload')}
      />

      {/* 2. NEW FEATURES SECTION: Placed at the end/bottom of the page in its own clean vertical space */}
      <div className="relative z-20 w-full bg-black border-t border-white/10 flex justify-center items-center">
        <FeatureShaderCards />
      </div>
    </div>
  );
}
