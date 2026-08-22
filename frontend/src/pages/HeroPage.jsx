import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowRight } from 'lucide-react';
import { CinematicHero } from '@/components/ui/cinematic-landing-hero';
import FeatureShaderCards from '@/components/ui/feature-shader-cards';

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

        {/* Top-Right "GET INSIDE" CTA Gateway Button */}
        <button
          onClick={handleGetInside}
          className="pointer-events-auto group relative inline-flex items-center justify-center px-5 py-2 md:px-6 md:py-2.5 rounded-full font-bold text-xs md:text-sm tracking-wider uppercase text-white bg-neutral-950/80 hover:bg-neutral-900 border border-white/20 hover:border-blue-400/60 backdrop-blur-xl shadow-xl transition-all duration-300 hover:scale-[1.03] hover:shadow-[0_0_25px_rgba(59,130,246,0.45)] active:scale-95 cursor-pointer"
          title="Enter MuleScope Platform"
        >
          <span className="relative z-10 flex items-center gap-2">
            GET INSIDE
            <ArrowRight className="w-4 h-4 text-blue-400 transition-transform duration-300 group-hover:translate-x-1" />
          </span>
          <span className="absolute inset-0 rounded-full bg-gradient-to-r from-blue-600/25 to-indigo-600/25 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
        </button>
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

      {/* 2. CINEMATIC FRAME TRANSITION DIVIDER: Smooth gradient blend & animated glowing beam divider */}
      <div className="relative z-20 w-full bg-gradient-to-b from-[#050914] via-[#03060f] to-black flex flex-col items-center justify-center pt-8 pb-4 overflow-hidden pointer-events-none">
        
        {/* Ambient Portal Glow Orbs */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] md:w-[900px] h-[120px] bg-gradient-to-b from-cyan-500/10 via-blue-500/5 to-transparent blur-[60px] rounded-full pointer-events-none" />

        {/* Animated Laser Beam Line */}
        <div className="relative w-full max-w-6xl mx-auto flex items-center justify-center px-6 my-2">
          <div className="h-[1px] w-full bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent shadow-[0_0_12px_rgba(34,211,238,0.5)]" />
          <div className="absolute left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_10px_#22d3ee] animate-ping" />
          <div className="absolute left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_6px_#ffffff]" />
        </div>

        {/* Downward Scroll Indicator Pill */}
        <div className="relative z-10 my-2 inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-white/5 border border-white/10 text-cyan-300 text-[10px] md:text-xs font-bold tracking-[0.2em] uppercase backdrop-blur-md shadow-lg animate-bounce">
          <span>↓</span>
          <span>EXPLORE PLATFORM INTELLIGENCE</span>
          <span>↓</span>
        </div>
      </div>

      {/* 3. NEW FEATURES SECTION: Placed smoothly below the transition divider */}
      <div className="relative z-20 w-full bg-black flex justify-center items-center">
        <FeatureShaderCards />
      </div>
    </div>
  );
}
