import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowRight, ChevronDown } from 'lucide-react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { CinematicHero } from '@/components/ui/cinematic-landing-hero';
import FeatureShaderCards from '@/components/ui/feature-shader-cards';

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

export default function HeroPage() {
  const navigate = useNavigate();
  const featureSectionRef = useRef(null);

  const handleGetInside = () => {
    navigate('/dashboard');
  };

  useEffect(() => {
    if (!featureSectionRef.current) return;

    const ctx = gsap.context(() => {
      // Scroll-triggered Fade-Up & Scale Reveal Animation for the Feature Section
      gsap.fromTo(
        featureSectionRef.current,
        {
          opacity: 0,
          y: 60,
          scale: 0.97,
        },
        {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 1.2,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: featureSectionRef.current,
            start: 'top 85%',
            end: 'top 30%',
            scrub: 0.8,
          },
        }
      );
    });

    return () => ctx.revert();
  }, []);

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

      {/* 2. CINEMATIC SECTION TRANSITION DIVIDER */}
      <div className="relative w-full z-30 pointer-events-none flex flex-col items-center justify-center -mt-8 mb-4">
        {/* Soft Gradient Fade Overlay Mask connecting Hero & Features */}
        <div className="absolute -top-24 left-0 right-0 h-36 bg-gradient-to-b from-transparent via-neutral-950/80 to-black" />
        
        {/* Luminous Glowing Transition Line */}
        <div className="relative w-full max-w-5xl h-[1px] bg-gradient-to-r from-transparent via-white/25 to-transparent shadow-[0_0_15px_rgba(255,255,255,0.2)]">
          <div className="absolute left-1/2 -translate-x-1/2 -top-3 px-4 py-1 rounded-full bg-black/90 border border-white/15 backdrop-blur-xl flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-[0.25em] text-zinc-400 shadow-2xl">
            <span>EXPLORE PLATFORM LAYERS</span>
            <ChevronDown className="w-3 h-3 text-cyan-400 animate-bounce" />
          </div>
        </div>
      </div>

      {/* 3. FEATURES SECTION WITH SCROLL FADE-UP ANIMATION */}
      <div
        ref={featureSectionRef}
        className="relative z-20 w-full bg-black flex justify-center items-center transform will-change-transform"
      >
        <FeatureShaderCards />
      </div>
    </div>
  );
}
