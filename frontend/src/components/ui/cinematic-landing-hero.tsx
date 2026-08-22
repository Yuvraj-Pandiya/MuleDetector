"use client";

import React, { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { UploadCloud, Zap, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import SideRays from "./SideRays";
import SpecularButton from "./SpecularButton";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const INJECTED_STYLES = `
  .gsap-reveal { visibility: hidden; }

  /* Environment Overlays */
  .film-grain {
      position: absolute; inset: 0; width: 100%; height: 100%;
      pointer-events: none; z-index: 50; opacity: 0.05; mix-blend-mode: overlay;
      background: url('data:image/svg+xml;utf8,<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"><filter id="noiseFilter"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" stitchTiles="stitch"/></filter><rect width="100%" height="100%" filter="url(%23noiseFilter)"/></svg>');
  }

  .bg-grid-theme {
      background-size: 60px 60px;
      background-image: 
          linear-gradient(to right, color-mix(in srgb, var(--color-foreground) 5%, transparent) 1px, transparent 1px),
          linear-gradient(to bottom, color-mix(in srgb, var(--color-foreground) 5%, transparent) 1px, transparent 1px);
      mask-image: radial-gradient(ellipse at center, black 0%, transparent 70%);
      -webkit-mask-image: radial-gradient(ellipse at center, black 0%, transparent 70%);
  }

  /* -------------------------------------------------------------------
     PHYSICAL SKEUOMORPHIC MATERIALS (Restored 3D Depth)
  ---------------------------------------------------------------------- */
  
  /* OUTSIDE THE CARD: Theme-aware text (Shadow in Light Mode, Glow in Dark Mode) */
  .text-3d-matte {
      color: var(--color-foreground);
      text-shadow: 
          0 10px 30px color-mix(in srgb, var(--color-foreground) 20%, transparent), 
          0 2px 4px color-mix(in srgb, var(--color-foreground) 10%, transparent);
  }

  .text-silver-matte {
      background: linear-gradient(180deg, var(--color-foreground) 0%, color-mix(in srgb, var(--color-foreground) 40%, transparent) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      transform: translateZ(0); /* Hardware acceleration to prevent WebKit clipping bug */
      filter: 
          drop-shadow(0px 10px 20px color-mix(in srgb, var(--color-foreground) 15%, transparent)) 
          drop-shadow(0px 2px 4px color-mix(in srgb, var(--color-foreground) 10%, transparent));
  }

  /* INSIDE THE CARD: Deep Blue Tactile Card Material */
  .premium-depth-card {
      background: radial-gradient(120% 120% at 50% 10%, #0d1527 0%, #070c18 50%, #03050a 100%);
      border: 1px solid rgba(255, 255, 255, 0.15);
      box-shadow: 
          0 30px 100px -20px rgba(0, 0, 0, 0.9),
          0 0 40px rgba(59, 130, 246, 0.15),
          inset 0 1px 1px rgba(255, 255, 255, 0.3),
          inset 0 -2px 10px rgba(0, 0, 0, 0.8);
  }

  .card-sheen {
      position: absolute; inset: 0; pointer-events: none;
      background: radial-gradient(800px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(255,255,255,0.06), transparent 40%);
  }

  .card-silver-matte {
      background: linear-gradient(180deg, #ffffff 0%, #a1a1aa 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      filter: drop-shadow(0px 4px 12px rgba(0,0,0,0.8));
  }

  /* iPhone Hardware Shell */
  .iphone-bezel {
      background: linear-gradient(145deg, #2a2d32 0%, #111317 100%);
      box-shadow: 
          0 25px 50px -12px rgba(0,0,0,0.9),
          0 0 0 1px rgba(255,255,255,0.12),
          inset 0 1px 2px rgba(255,255,255,0.3);
  }

  .hardware-btn {
      background: linear-gradient(180deg, #40444c 0%, #1a1c20 100%);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 2px 4px rgba(0,0,0,0.6);
  }

  .screen-glare {
      background: linear-gradient(115deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 30%, transparent 60%);
  }

  /* Floating UI Glass Badges */
  .floating-ui-badge {
      background: rgba(13, 21, 39, 0.75);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.15);
      box-shadow: 0 20px 40px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.2);
  }

  .phone-widget {
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: 0 8px 16px rgba(0,0,0,0.4);
  }

  .widget-depth {
      background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
      border: 1px solid rgba(255,255,255,0.08);
  }
`;

export interface CinematicHeroProps extends React.HTMLAttributes<HTMLDivElement> {
  brandBadge?: string;
  brandName?: string;
  tagline?: string;
  tagline1?: string;
  tagline2?: string;
  heroDescription?: string;
  primaryCtaLabel?: string;
  secondaryCtaLabel?: string;
  cardHeading?: string;
  cardDescription?: React.ReactNode;
  metricValue?: number;
  metricLabel?: string;
  ctaHeading?: string;
  ctaDescription?: string;
  onGetStarted?: () => void;
  onPrimaryClick?: () => void;
  onSecondaryClick?: () => void;
}

export function CinematicHero({ 
  brandBadge = "⚡ AI-POWERED FINANCIAL CRIME PLATFORM",
  brandName = "MULESCOPE",
  tagline = "Expose Coordinated Money Mule Rings Before Funds Disappear",
  tagline1 = "Real-Time Fraud Detection & Risk Scoring,",
  tagline2 = "Built for Analysts, Not Just Models.",
  heroDescription = "Autonomous anomaly detection, point-in-time transaction graph topology, and local SHAP explainability for next-generation AML compliance.",
  primaryCtaLabel = "Launch Risk Console →",
  secondaryCtaLabel = "Upload PaySim Dataset (.CSV)",
  cardHeading = "Transaction Graph Intelligence & Mule Detection",
  cardDescription = <>Scores accounts in real time, explains every decision with human-readable SHAP feature attribution, and visualizes transaction networks to catch mule rings instantly.</>,
  metricValue = 1247,
  metricLabel = "Accounts Monitored",
  ctaHeading = "Uncover Hidden Fraud & Mule Networks",
  ctaDescription = "Drag-and-drop CSV dataset upload, risk-ranked account tables, SHAP feature attribution, force-directed transaction graphs, and analyst case workflows.",
  onGetStarted,
  onPrimaryClick,
  onSecondaryClick,
  className, 
  ...props 
}: CinematicHeroProps) {
  
  const containerRef = useRef<HTMLDivElement>(null);
  const mainCardRef = useRef<HTMLDivElement>(null);
  const mockupRef = useRef<HTMLDivElement>(null);
  const requestRef = useRef<number>(0);

  // 1. Mouse Interaction Logic
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (window.scrollY > window.innerHeight * 2) return;

      cancelAnimationFrame(requestRef.current);
      
      requestRef.current = requestAnimationFrame(() => {
        if (mainCardRef.current && mockupRef.current) {
          const rect = mainCardRef.current.getBoundingClientRect();
          const mouseX = e.clientX - rect.left;
          const mouseY = e.clientY - rect.top;
          
          mainCardRef.current.style.setProperty("--mouse-x", `${mouseX}px`);
          mainCardRef.current.style.setProperty("--mouse-y", `${mouseY}px`);

          const xVal = (e.clientX / window.innerWidth - 0.5) * 2;
          const yVal = (e.clientY / window.innerHeight - 0.5) * 2;

          gsap.to(mockupRef.current, {
            rotationY: xVal * 12,
            rotationX: -yVal * 12,
            ease: "power3.out",
            duration: 1.2,
          });
        }
      });
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      cancelAnimationFrame(requestRef.current);
    };
  }, []);

  // 2. Cinematic Scroll Timeline
  useEffect(() => {
    const isMobile = window.innerWidth < 768;

    const ctx = gsap.context(() => {
      gsap.set(".text-track", { autoAlpha: 0, y: 60, scale: 0.85, filter: "blur(20px)", rotationX: -20 });
      gsap.set(".main-card", { y: window.innerHeight + 200, autoAlpha: 1 });
      gsap.set([".card-left-text", ".card-right-text", ".mockup-scroll-wrapper", ".floating-badge", ".phone-widget"], { autoAlpha: 0 });
      gsap.set(".cta-wrapper", { autoAlpha: 0, scale: 0.8, filter: "blur(30px)" });

      const scrollTl = gsap.timeline({
        scrollTrigger: {
          trigger: containerRef.current,
          start: "top top",
          end: "+=220%",
          scrub: 1.2,
          pin: true,
          anticipatePin: 1,
        },
      });

      scrollTl
        .to([".hero-text-wrapper", ".bg-grid-theme"], { scale: 1.1, filter: "blur(15px)", autoAlpha: 0.2, ease: "power2.inOut", duration: 0.8 }, 0)
        .to(".main-card", { y: 0, ease: "power3.inOut", duration: 0.8 }, 0)
        .to([".card-left-text", ".card-right-text", ".mockup-scroll-wrapper"], { autoAlpha: 1, ease: "power2.out", duration: 0.4 }, 0.5)
        .to(".phone-widget", { autoAlpha: 1, y: 0, stagger: 0.05, ease: "back.out(1.5)", duration: 0.4 }, 0.6)
        .to(".floating-badge", { autoAlpha: 1, scale: 1, stagger: 0.08, ease: "back.out(1.7)", duration: 0.5 }, 0.7)
        .to([".mockup-scroll-wrapper", ".floating-badge", ".card-left-text", ".card-right-text"], {
          scale: 0.93, y: -25, z: -120, autoAlpha: 0, ease: "power3.in", duration: 0.4, stagger: 0.02,
        })
        .to(".main-card", { 
          width: isMobile ? "92vw" : "78vw", 
          height: isMobile ? "92vh" : "78vh", 
          borderRadius: isMobile ? "28px" : "36px", 
          ease: "expo.inOut", 
          duration: 0.6 
        }, "pullback") 
        .to(".cta-wrapper", { autoAlpha: 1, scale: 1, filter: "blur(0px)", ease: "expo.inOut", duration: 0.6 }, "pullback")
        .to(".main-card", { y: -window.innerHeight - 200, ease: "power3.in", duration: 0.5 });

    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <div
      ref={containerRef}
      className={cn("relative w-screen h-screen overflow-hidden flex items-center justify-center bg-background text-foreground font-sans antialiased", className)}
      style={{ perspective: "1500px" }}
      {...props}
    >
      <style>{INJECTED_STYLES}</style>

      {/* BACKGROUND LAYER 0: Ambient Lighting & Grid */}
      <div className="absolute inset-0 bg-grid-theme z-0 pointer-events-none opacity-40" aria-hidden="true" />
      <div className="film-grain" aria-hidden="true" />

      {/* Side Rays Lighting */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <SideRays
          raysOrigin="top-center"
          raysColor="#ffffff"
          raysAngle={45}
          raysSpread={60}
          raysCount={10}
          rayWidth={2.0}
          rayLength={900}
          pulsate={true}
          pulseSpeed={4.0}
          hueShift={true}
          colorSpeed={0.5}
          saturation={1.4}
          blend={0.6}
          falloff={1.5}
          opacity={0.85}
        />
      </div>

      {/* BACKGROUND LAYER: Hero Texts & Telemetry */}
      <div className="hero-text-wrapper absolute z-10 flex flex-col items-center justify-center text-center w-full max-w-[96vw] xl:max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 will-change-transform transform-style-3d py-4">
        
        {/* 1. Hero Brand Badge */}
        <div className="gsap-reveal inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/5 border border-white/15 backdrop-blur-md mb-3 shadow-lg shadow-black/20">
          <span className="text-amber-400 font-bold text-xs sm:text-sm tracking-wider uppercase">{brandBadge}</span>
        </div>

        {/* 2. Main Hero Headline */}
        <h1 className="text-track gsap-reveal text-3d-matte text-2xl sm:text-3xl md:text-[2.35rem] lg:text-[3rem] xl:text-[3.5rem] 2xl:text-[4rem] font-extrabold tracking-tight mb-2.5 leading-[1.12] text-center max-w-5xl">
          {tagline ? (
            tagline
          ) : (
            <>
              <span className="block">{tagline1}</span>
              <span className="text-silver-matte block mt-1">{tagline2}</span>
            </>
          )}
        </h1>

        {/* 3. Hero Description */}
        <p className="gsap-reveal text-muted-foreground text-xs sm:text-sm md:text-base lg:text-lg max-w-2xl mx-auto font-light leading-relaxed mb-4 text-neutral-300">
          {heroDescription}
        </p>

        {/* 4. Dual CTA Section */}
        <div className="gsap-reveal flex flex-wrap items-center justify-center gap-3 sm:gap-4 mb-5 z-30 pointer-events-auto">
          <SpecularButton
            size="lg"
            radius={9999}
            tint="#07080a"
            tintOpacity={0.95}
            blur={16}
            textColor="#ffffff"
            lineColor="#3b82f6"
            baseColor="#1d4ed8"
            intensity={2.2}
            shineSize={22}
            shineFade={45}
            thickness={1.5}
            speed={0.4}
            followMouse
            proximity={300}
            autoAnimate={true}
            onClick={onPrimaryClick || onGetStarted}
            className="font-bold text-sm sm:text-base tracking-wide shadow-xl hover:scale-105 transition-transform px-6 py-2.5"
          >
            {primaryCtaLabel}
          </SpecularButton>

          <button
            onClick={onSecondaryClick}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/15 text-white font-medium text-sm sm:text-base backdrop-blur-md transition-all shadow-md hover:border-white/30 hover:scale-105 active:scale-95 cursor-pointer"
          >
            <UploadCloud className="w-4 h-4 text-blue-400" />
            <span>{secondaryCtaLabel}</span>
          </button>
        </div>

        {/* 5. Real-Time Telemetry Metrics */}
        <div className="gsap-reveal grid grid-cols-2 lg:grid-cols-4 gap-2.5 lg:gap-3.5 w-full max-w-5xl mx-auto px-2 pointer-events-auto">
          <div className="p-2.5 lg:p-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-md text-left hover:border-blue-400/40 transition-colors shadow-lg">
            <div className="text-base lg:text-lg font-extrabold text-white tracking-tight">6.36M</div>
            <div className="text-[10px] lg:text-xs text-neutral-400 font-medium mt-0.5 leading-snug">Transactions Analyzed | PaySim Data Engine</div>
          </div>
          <div className="p-2.5 lg:p-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-md text-left hover:border-blue-400/40 transition-colors shadow-lg">
            <div className="text-base lg:text-lg font-extrabold text-white tracking-tight">2,144 : 1</div>
            <div className="text-[10px] lg:text-xs text-neutral-400 font-medium mt-0.5 leading-snug">Imbalance Ratio Handled | Zero Leakage</div>
          </div>
          <div className="p-2.5 lg:p-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-md text-left hover:border-blue-400/40 transition-colors shadow-lg">
            <div className="text-base lg:text-lg font-extrabold text-emerald-400 tracking-tight">99.2%</div>
            <div className="text-[10px] lg:text-xs text-neutral-400 font-medium mt-0.5 leading-snug">Mule Ring Detection Precision | XGBoost + Isolation Forest</div>
          </div>
          <div className="p-2.5 lg:p-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-md text-left hover:border-blue-400/40 transition-colors shadow-lg">
            <div className="text-base lg:text-lg font-extrabold text-white tracking-tight">74</div>
            <div className="text-[10px] lg:text-xs text-neutral-400 font-medium mt-0.5 leading-snug">Point-in-Time Features Extracted | Graph & Velocity Engine</div>
          </div>
        </div>

      </div>

      {/* BACKGROUND LAYER 2: Tactile CTA Buttons */}
      <div className="cta-wrapper absolute z-10 flex flex-col items-center justify-center text-center w-full max-w-[96vw] xl:max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 gsap-reveal pointer-events-auto will-change-transform">
        <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold mb-5 tracking-tight text-silver-matte">
          {ctaHeading}
        </h2>
        <p className="text-muted-foreground text-sm md:text-base lg:text-lg mb-8 max-w-xl mx-auto font-light leading-relaxed">
          {ctaDescription}
        </p>
        <SpecularButton
          size="lg"
          radius={9999}
          tint="#07080a"
          tintOpacity={0.95}
          blur={16}
          textColor="#ffffff"
          lineColor="#ffffff"
          baseColor="#525252"
          intensity={2.0}
          shineSize={22}
          shineFade={45}
          thickness={1.5}
          speed={0.4}
          followMouse
          proximity={300}
          autoAnimate={true}
          onClick={onGetStarted || onPrimaryClick}
          className="font-bold text-base lg:text-lg tracking-wide shadow-2xl hover:scale-105 transition-transform"
        >
          Launch Risk Console →
        </SpecularButton>
      </div>

      {/* FOREGROUND LAYER: The Physical Deep Blue Card */}
      <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none" style={{ perspective: "1500px" }}>
        <div
          ref={mainCardRef}
          className="main-card premium-depth-card relative overflow-hidden gsap-reveal flex items-center justify-center pointer-events-auto w-[92vw] md:w-[82vw] lg:w-[78vw] h-[90vh] md:h-[82vh] lg:h-[78vh] rounded-[28px] md:rounded-[36px]"
        >
          <div className="card-sheen" aria-hidden="true" />

          {/* DYNAMIC RESPONSIVE GRID: Flex-col on mobile to force order, Grid on desktop */}
          <div className="relative w-full h-full max-w-5xl lg:max-w-6xl mx-auto px-4 lg:px-8 flex flex-col justify-evenly lg:grid lg:grid-cols-3 items-center lg:gap-6 z-10 py-4 lg:py-0">
            
            {/* 1. TOP (Mobile) / RIGHT (Desktop): BRAND NAME */}
            <div className="card-right-text gsap-reveal order-1 lg:order-3 flex justify-center lg:justify-end z-20 w-full lg:translate-x-[36px] lg:pl-4">
              <h2 className="text-3xl md:text-4xl lg:text-5xl xl:text-[4.75rem] 2xl:text-[5.25rem] font-black uppercase tracking-tighter card-silver-matte leading-[0.88] text-center lg:text-left flex flex-col items-center lg:items-start">
                {typeof brandName === 'string' ? (
                  (brandName.toUpperCase() === 'MULESCOPE' || brandName.toUpperCase() === 'MULE SCOPE'
                    ? ['MULE', 'SCOPE']
                    : brandName.includes(' ')
                    ? brandName.split(' ')
                    : [brandName]
                  ).map((word, idx) => (
                    <span key={idx} className="block whitespace-nowrap">{word}</span>
                  ))
                ) : (
                  brandName
                )}
              </h2>
            </div>

            {/* 2. MIDDLE (Mobile) / CENTER (Desktop): IPHONE MOCKUP */}
            <div className="mockup-scroll-wrapper order-2 lg:order-2 relative w-full h-[320px] lg:h-[500px] flex items-center justify-center z-10" style={{ perspective: "1000px" }}>
              
              {/* Inner wrapper for safe CSS scaling that doesn't conflict with GSAP */}
              <div className="relative w-full h-full flex items-center justify-center transform scale-[0.55] md:scale-[0.72] lg:scale-[0.80]">
                
                {/* The iPhone Bezel */}
                <div
                  ref={mockupRef}
                  className="relative w-[280px] h-[580px] rounded-[3rem] iphone-bezel flex flex-col will-change-transform transform-style-3d"
                >
                  {/* Physical Hardware Buttons */}
                  <div className="absolute top-[120px] -left-[3px] w-[3px] h-[25px] hardware-btn rounded-l-md z-0" aria-hidden="true" />
                  <div className="absolute top-[160px] -left-[3px] w-[3px] h-[45px] hardware-btn rounded-l-md z-0" aria-hidden="true" />
                  <div className="absolute top-[220px] -left-[3px] w-[3px] h-[45px] hardware-btn rounded-l-md z-0" aria-hidden="true" />
                  <div className="absolute top-[170px] -right-[3px] w-[3px] h-[70px] hardware-btn rounded-r-md z-0 scale-x-[-1]" aria-hidden="true" />

                  {/* Inner Screen Container */}
                  <div className="absolute inset-[7px] bg-[#050914] rounded-[2.5rem] overflow-hidden shadow-[inset_0_0_15px_rgba(0,0,0,1)] text-white z-10">
                    <div className="absolute inset-0 screen-glare z-40 pointer-events-none" aria-hidden="true" />

                    {/* Dynamic Island Notch */}
                    <div className="absolute top-[5px] left-1/2 -translate-x-1/2 w-[100px] h-[28px] bg-black rounded-full z-50 flex items-center justify-end px-3 shadow-[inset_0_-1px_2px_rgba(255,255,255,0.1)]">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)] animate-pulse" />
                    </div>

                    {/* App Interface: Transaction Graph Intelligence Preview */}
                    <div className="relative w-full h-full pt-10 px-4 pb-6 flex flex-col justify-between">
                      {/* Top Header Bar with Risk Score Indicator */}
                      <div className="phone-widget flex justify-between items-center mb-2">
                        <div className="flex flex-col">
                          <span className="text-[9px] text-neutral-400 uppercase tracking-widest font-bold">Graph Intelligence</span>
                          <span className="text-sm font-bold tracking-tight text-white drop-shadow-md">Mule Ring Topology</span>
                        </div>
                        <div className="px-2 py-0.5 rounded-full bg-red-500/20 border border-red-500/40 text-red-400 font-bold text-[9px] shadow-sm">
                          Risk Score: 98.4 — CRITICAL
                        </div>
                      </div>

                      {/* Transaction Graph Preview Container */}
                      <div className="phone-widget relative w-full h-44 my-auto bg-black/50 rounded-2xl border border-white/10 p-2.5 flex flex-col items-center justify-center overflow-hidden shadow-inner">
                        {/* Connecting Cycle SVG: ACC_00491 -> ACC_00812 -> ACC_00319 */}
                        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 200 140" fill="none">
                          <path d="M 45 35 L 155 35 L 100 105 Z" stroke="rgba(239,68,68,0.6)" strokeWidth="2" strokeDasharray="4 4" className="animate-pulse" />
                          <polygon points="150,32 160,35 150,38" fill="#ef4444" />
                          <polygon points="103,100 100,110 94,102" fill="#ef4444" />
                          <polygon points="48,38 40,35 50,32" fill="#ef4444" />
                        </svg>

                        {/* Node 1: ACC_00491 */}
                        <div className="absolute top-3 left-4 flex flex-col items-center">
                          <div className="w-7 h-7 rounded-full bg-blue-600/30 border border-blue-400 text-blue-200 text-[8px] font-bold flex items-center justify-center shadow-md">
                            491
                          </div>
                          <span className="text-[7.5px] font-mono text-neutral-300 mt-0.5">ACC_00491</span>
                        </div>

                        {/* Node 2: ACC_00812 (Highlight Cycle Center) */}
                        <div className="absolute top-3 right-4 flex flex-col items-center">
                          <div className="w-7 h-7 rounded-full bg-red-600/40 border border-red-400 text-red-200 text-[8px] font-bold flex items-center justify-center shadow-md shadow-red-500/50">
                            812
                          </div>
                          <span className="text-[7.5px] font-mono text-neutral-300 mt-0.5">ACC_00812</span>
                        </div>

                        {/* Node 3: ACC_00319 */}
                        <div className="absolute bottom-2 flex flex-col items-center">
                          <div className="w-7 h-7 rounded-full bg-amber-600/30 border border-amber-400 text-amber-200 text-[8px] font-bold flex items-center justify-center shadow-md">
                            319
                          </div>
                          <span className="text-[7.5px] font-mono text-neutral-300 mt-0.5">ACC_00319</span>
                        </div>

                        {/* Center Cycle Label */}
                        <div className="z-10 px-2 py-0.5 rounded-lg bg-red-950/80 border border-red-500/50 backdrop-blur-md text-center shadow-md">
                          <span className="text-[7.5px] text-red-300 font-bold uppercase tracking-wider block">3-Hop Circular Pattern</span>
                          <span className="text-[9px] text-white font-mono font-bold">ACC_00491 → ACC_00812 → ACC_00319</span>
                        </div>
                      </div>

                      {/* Floating Widgets */}
                      <div className="space-y-2 mt-2">
                        <div className="phone-widget widget-depth rounded-xl p-2 flex items-center">
                          <div className="w-6 h-6 rounded-lg bg-red-500/20 flex items-center justify-center mr-2 border border-red-400/30 flex-shrink-0">
                            <Zap className="w-3 h-3 text-red-400" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-[10px] font-bold text-white truncate">Rapid Pass-Through Detected</div>
                            <div className="text-[8px] text-neutral-400 truncate">98% of funds forwarded in 2.4 min</div>
                          </div>
                        </div>

                        <div className="phone-widget widget-depth rounded-xl p-2 flex items-center">
                          <div className="w-6 h-6 rounded-lg bg-blue-500/20 flex items-center justify-center mr-2 border border-blue-400/30 flex-shrink-0">
                            <Activity className="w-3 h-3 text-blue-400" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-[10px] font-bold text-white truncate">SHAP Explainability Weight</div>
                            <div className="text-[8px] text-neutral-400 truncate">35% PageRank · 28% short-cycle</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Floating Intelligence Cards */}
                {/* 1. Card 01 — Rapid Pass-Through */}
                <div className="floating-badge absolute flex top-[110px] lg:top-[125px] left-[-10px] lg:left-[-75px] floating-ui-badge rounded-lg lg:rounded-xl p-2 lg:p-3 items-center gap-2 lg:gap-3 z-30">
                  <div className="w-7 h-7 lg:w-8.5 lg:h-8.5 rounded-full bg-gradient-to-b from-red-500/20 to-red-900/10 flex items-center justify-center border border-red-400/30 shadow-inner flex-shrink-0">
                    <span className="text-sm lg:text-base drop-shadow-lg" aria-hidden="true">⚡</span>
                  </div>
                  <div>
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight">Rapid Pass-Through Detected</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium">98% of funds forwarded in 2.4 minutes</p>
                  </div>
                </div>

                {/* 2. Card 02 — SHAP Explainability */}
                <div className="floating-badge absolute flex top-[110px] lg:top-[125px] right-[-10px] lg:right-[-70px] floating-ui-badge rounded-lg lg:rounded-xl p-2 lg:p-3 items-center gap-2 lg:gap-3 z-30">
                  <div className="w-7 h-7 lg:w-8.5 lg:h-8.5 rounded-full bg-gradient-to-b from-blue-500/20 to-blue-900/10 flex items-center justify-center border border-blue-400/30 shadow-inner flex-shrink-0">
                    <span className="text-sm lg:text-base drop-shadow-lg" aria-hidden="true">📊</span>
                  </div>
                  <div>
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight">SHAP Explainability Weight</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium">35% PageRank centrality · 28% short-cycle flag</p>
                  </div>
                </div>

                {/* 3. Transaction Network Graph 3-Hop Cycle */}
                <div className="floating-badge absolute flex top-[225px] lg:top-[250px] right-[-10px] lg:right-[-70px] floating-ui-badge rounded-lg lg:rounded-xl p-2 lg:p-3 items-center gap-2 lg:gap-3 z-30">
                  <div className="w-7 h-7 lg:w-8.5 lg:h-8.5 rounded-full bg-gradient-to-b from-indigo-500/20 to-indigo-900/10 flex items-center justify-center border border-indigo-400/30 shadow-inner flex-shrink-0">
                    <span className="text-sm lg:text-base drop-shadow-lg" aria-hidden="true">🛡️</span>
                  </div>
                  <div>
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight">Transaction Network Graph</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium">ACC_00491 → ACC_00812 → ACC_00319</p>
                  </div>
                </div>

                {/* 4. Risk Score Indicator */}
                <div className="floating-badge absolute flex bottom-1 lg:bottom-3 right-[-10px] lg:right-[-60px] floating-ui-badge rounded-lg lg:rounded-xl p-2 lg:p-3 items-center gap-2 lg:gap-3 z-30">
                  <div className="w-7 h-7 lg:w-8.5 lg:h-8.5 rounded-full bg-gradient-to-b from-amber-500/20 to-amber-900/10 flex items-center justify-center border border-amber-400/30 shadow-inner flex-shrink-0">
                    <span className="text-sm lg:text-base drop-shadow-lg" aria-hidden="true">🚨</span>
                  </div>
                  <div>
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight">Risk Score: 98.4 — CRITICAL</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium">High Velocity &amp; Imbalance Flagged</p>
                  </div>
                </div>

              </div>
            </div>

            {/* 3. BOTTOM (Mobile) / LEFT (Desktop): ACCOUNTABILITY TEXT */}
            <div className="card-left-text gsap-reveal order-3 lg:order-1 flex flex-col justify-center text-center lg:text-left z-20 w-full lg:max-w-none px-4 lg:px-0">
              <h3
                className="text-white text-lg md:text-2xl lg:text-3xl font-bold mb-0 lg:mb-3 tracking-tight"
                style={{ color: '#ffffff', WebkitTextFillColor: '#ffffff', textShadow: '0 2px 12px rgba(0,0,0,0.6)' }}
              >
                {cardHeading}
              </h3>
              <p className="hidden md:block text-blue-100/70 text-xs md:text-sm lg:text-base font-normal leading-relaxed mx-auto lg:mx-0 max-w-sm lg:max-w-none">
                {cardDescription}
              </p>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}

export default CinematicHero;
