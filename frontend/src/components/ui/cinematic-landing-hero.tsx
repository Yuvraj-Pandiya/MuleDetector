"use client";

import React, { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
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

  /* INSIDE THE CARD: Hardcoded Silver/White for the dark background, deep rich shadows */
  .text-card-silver-matte {
      background: linear-gradient(180deg, #FFFFFF 0%, #A1A1AA 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      transform: translateZ(0);
      filter: 
          drop-shadow(0px 12px 24px rgba(0,0,0,0.8)) 
          drop-shadow(0px 4px 8px rgba(0,0,0,0.6));
  }

  /* Deep Physical Card with Dynamic Mouse Lighting */
  .premium-depth-card {
      background: linear-gradient(145deg, #162C6D 0%, #0A101D 100%);
      box-shadow: 
          0 40px 100px -20px rgba(0, 0, 0, 0.9),
          0 20px 40px -20px rgba(0, 0, 0, 0.8),
          inset 0 1px 2px rgba(255, 255, 255, 0.2),
          inset 0 -2px 4px rgba(0, 0, 0, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.04);
      position: relative;
  }

  .card-sheen {
      position: absolute; inset: 0; border-radius: inherit; pointer-events: none; z-index: 50;
      background: radial-gradient(800px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(255,255,255,0.06) 0%, transparent 40%);
      mix-blend-mode: screen; transition: opacity 0.3s ease;
  }

  /* Realistic iPhone Mockup Hardware */
  .iphone-bezel {
      background-color: #111;
      box-shadow: 
          inset 0 0 0 2px #52525B, 
          inset 0 0 0 7px #000, 
          0 40px 80px -15px rgba(0,0,0,0.9),
          0 15px 25px -5px rgba(0,0,0,0.7);
      transform-style: preserve-3d;
  }

  .hardware-btn {
      background: linear-gradient(90deg, #404040 0%, #171717 100%);
      box-shadow: 
          -2px 0 5px rgba(0,0,0,0.8),
          inset -1px 0 1px rgba(255,255,255,0.15),
          inset 1px 0 2px rgba(0,0,0,0.8);
      border-left: 1px solid rgba(255,255,255,0.05);
  }
  
  .screen-glare {
      background: linear-gradient(110deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0) 45%);
  }

  .widget-depth {
      background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
      box-shadow: 
          0 10px 20px rgba(0,0,0,0.3),
          inset 0 1px 1px rgba(255,255,255,0.05),
          inset 0 -1px 1px rgba(0,0,0,0.5);
      border: 1px solid rgba(255,255,255,0.03);
  }

  .floating-ui-badge {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.01) 100%);
      backdrop-filter: blur(24px); 
      -webkit-backdrop-filter: blur(24px);
      box-shadow: 
          0 0 0 1px rgba(255, 255, 255, 0.1),
          0 25px 50px -12px rgba(0, 0, 0, 0.8),
          inset 0 1px 1px rgba(255,255,255,0.2),
          inset 0 -1px 1px rgba(0,0,0,0.5);
  }

  /* Physical Tactile Buttons */
  .btn-modern-light, .btn-modern-dark {
      transition: all 0.4s cubic-bezier(0.25, 1, 0.5, 1);
  }
  .btn-modern-light {
      background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%);
      color: #0F172A;
      box-shadow: 0 0 0 1px rgba(0,0,0,0.05), 0 2px 4px rgba(0,0,0,0.1), 0 12px 24px -4px rgba(0,0,0,0.3), inset 0 1px 1px rgba(255,255,255,1), inset 0 -3px 6px rgba(0,0,0,0.06);
  }
  .btn-modern-light:hover {
      transform: translateY(-3px);
      box-shadow: 0 0 0 1px rgba(0,0,0,0.05), 0 6px 12px -2px rgba(0,0,0,0.15), 0 20px 32px -6px rgba(0,0,0,0.4), inset 0 1px 1px rgba(255,255,255,1), inset 0 -3px 6px rgba(0,0,0,0.06);
  }
  .btn-modern-light:active {
      transform: translateY(1px);
      background: linear-gradient(180deg, #F1F5F9 0%, #E2E8F0 100%);
      box-shadow: 0 0 0 1px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.1), inset 0 3px 6px rgba(0,0,0,0.1), inset 0 0 0 1px rgba(0,0,0,0.02);
  }
  .btn-modern-dark {
      background: linear-gradient(180deg, #27272A 0%, #18181B 100%);
      color: #FFFFFF;
      box-shadow: 0 0 0 1px rgba(255,255,255,0.1), 0 2px 4px rgba(0,0,0,0.6), 0 12px 24px -4px rgba(0,0,0,0.9), inset 0 1px 1px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.8);
  }
  .btn-modern-dark:hover {
      transform: translateY(-3px);
      background: linear-gradient(180deg, #3F3F46 0%, #27272A 100%);
      box-shadow: 0 0 0 1px rgba(255,255,255,0.15), 0 6px 12px -2px rgba(0,0,0,0.7), 0 20px 32px -6px rgba(0,0,0,1), inset 0 1px 1px rgba(255,255,255,0.2), inset 0 -3px 6px rgba(0,0,0,0.8);
  }
  .btn-modern-dark:active {
      transform: translateY(1px);
      background: #18181B;
      box-shadow: 0 0 0 1px rgba(255,255,255,0.05), inset 0 3px 8px rgba(0,0,0,0.9), inset 0 0 0 1px rgba(0,0,0,0.5);
  }

  .progress-ring {
      transform: rotate(-90deg);
      transform-origin: center;
      stroke-dasharray: 402;
      stroke-dashoffset: 402;
      stroke-linecap: round;
  }
`;

export interface CinematicHeroProps extends React.HTMLAttributes<HTMLDivElement> {
  brandName?: string;
  tagline1?: string;
  tagline2?: string;
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
  brandName = "MULESCOPE",
  tagline1 = "Real-Time Fraud Detection & Risk Scoring,",
  tagline2 = "Built for Analysts, Not Just Models.",
  cardHeading = "Explainable AI & Mule Network Detection",
  cardDescription = <>A real-time fraud detection and risk intelligence platform that scores accounts, explains every decision with SHAP attribution, and visualizes transaction networks to catch mule rings instantly.</>,
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

  // 1. High-Performance Mouse Interaction Logic (Using requestAnimationFrame)
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
  },[]);

  // 2. Complex Cinematic Scroll Timeline
  useEffect(() => {
    const isMobile = window.innerWidth < 768;

    const ctx = gsap.context(() => {
      gsap.set(".text-track", { autoAlpha: 0, y: 60, scale: 0.85, filter: "blur(20px)", rotationX: -20 });
      gsap.set(".text-days", { autoAlpha: 1, clipPath: "inset(0 100% 0 0)" });
      gsap.set(".main-card", { y: window.innerHeight + 200, autoAlpha: 1 });
      gsap.set([".card-left-text", ".card-right-text", ".mockup-scroll-wrapper", ".floating-badge", ".phone-widget"], { autoAlpha: 0 });
      gsap.set(".cta-wrapper", { autoAlpha: 0, scale: 0.8, filter: "blur(30px)" });

      const introTl = gsap.timeline({ delay: 0.1 });
      introTl
        .to(".text-track", { duration: 0.8, autoAlpha: 1, y: 0, scale: 1, filter: "blur(0px)", rotationX: 0, ease: "expo.out" })
        .to(".text-days", { duration: 0.7, clipPath: "inset(0 0% 0 0)", ease: "power4.inOut" }, "-=0.5");

      const scrollTl = gsap.timeline({
        scrollTrigger: {
          trigger: containerRef.current,
          start: "top top",
          end: "+=3500",
          pin: true,
          scrub: 1,
          anticipatePin: 1,
        },
      });

      scrollTl
        .to([".hero-text-wrapper", ".bg-grid-theme"], { scale: 1.1, filter: "blur(15px)", opacity: 0.2, ease: "power2.inOut", duration: 0.8 }, 0)
        .to(".main-card", { y: 0, ease: "power3.inOut", duration: 0.8 }, 0)
        .to(".main-card", { width: "100%", height: "100%", borderRadius: "0px", ease: "power3.inOut", duration: 0.6 })
        .fromTo(".mockup-scroll-wrapper",
          { y: 150, z: -300, rotationX: 30, rotationY: -15, autoAlpha: 0, scale: 0.8 },
          { y: 0, z: 0, rotationX: 0, rotationY: 0, autoAlpha: 1, scale: 1, ease: "expo.out", duration: 0.8 }, "-=0.3"
        )
        .fromTo(".phone-widget", { y: 20, autoAlpha: 0, scale: 0.95 }, { y: 0, autoAlpha: 1, scale: 1, stagger: 0.06, ease: "back.out(1.2)", duration: 0.6 }, "-=0.5")
        .to(".progress-ring", { strokeDashoffset: 60, duration: 0.8, ease: "power3.inOut" }, "-=0.5")
        .to(".counter-val", { innerHTML: metricValue, snap: { innerHTML: 1 }, duration: 0.8, ease: "expo.out" }, "-=0.8")
        .fromTo(".floating-badge", { y: 40, autoAlpha: 0, scale: 0.85, rotationZ: -5 }, { y: 0, autoAlpha: 1, scale: 1, rotationZ: 0, ease: "back.out(1.5)", duration: 0.6, stagger: 0.08 }, "-=0.8")
        .fromTo(".card-left-text", { x: -30, autoAlpha: 0 }, { x: 0, autoAlpha: 1, ease: "power4.out", duration: 0.6 }, "-=0.6")
        .fromTo(".card-right-text", { x: 30, autoAlpha: 0, scale: 0.9 }, { x: 0, autoAlpha: 1, scale: 1, ease: "expo.out", duration: 0.6 }, "<")
        // ── Instantly swap to CTA frame as soon as features finish loading ──
        .set(".hero-text-wrapper", { autoAlpha: 0 })
        .set(".cta-wrapper", { autoAlpha: 1 })
        .to([".mockup-scroll-wrapper", ".floating-badge", ".card-left-text", ".card-right-text"], {
          scale: 0.93, y: -25, z: -120, autoAlpha: 0, ease: "power3.in", duration: 0.4, stagger: 0.02,
        })
        // Responsive card pullback sizing
        .to(".main-card", { 
          width: isMobile ? "92vw" : "78vw", 
          height: isMobile ? "92vh" : "78vh", 
          borderRadius: isMobile ? "28px" : "36px", 
          ease: "expo.inOut", 
          duration: 0.6 
        }, "pullback") 
        .to(".cta-wrapper", { scale: 1, filter: "blur(0px)", ease: "expo.inOut", duration: 0.6 }, "pullback")
        .to(".main-card", { y: -window.innerHeight - 200, ease: "power3.in", duration: 0.5 });

    }, containerRef);

    return () => ctx.revert();
  },[metricValue]); 

  return (
    <div
      ref={containerRef}
      className={cn("relative w-screen h-screen overflow-hidden flex items-center justify-center bg-background text-foreground font-sans antialiased", className)}
      style={{ perspective: "1500px" }}
      {...props}
    >
      <style dangerouslySetInnerHTML={{ __html: INJECTED_STYLES }} />
      <div className="film-grain" aria-hidden="true" />
      <div className="bg-grid-theme absolute inset-0 z-0 pointer-events-none opacity-50" aria-hidden="true" />
      
      {/* SideRays Background Light Effect */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-30 overflow-hidden" aria-hidden="true">
        <SideRays
          speed={2.0}
          rayColor1="#3B82F6"
          rayColor2="#10B981"
          intensity={1.8}
          spread={2.2}
          origin="top-right"
          tilt={10}
          saturation={1.4}
          blend={0.6}
          falloff={1.5}
          opacity={0.85}
        />
      </div>

      {/* BACKGROUND LAYER: Hero Texts */}
      <div className="hero-text-wrapper absolute z-10 flex flex-col items-center justify-center text-center w-full max-w-[96vw] xl:max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 will-change-transform transform-style-3d">
        <h2 className="text-track gsap-reveal text-silver-matte text-sm sm:text-base md:text-lg lg:text-[1.35rem] xl:text-[1.65rem] font-extrabold uppercase tracking-[0.35em] mb-2 md:mb-4">
          {brandName}
        </h2>
        <h1 className="text-track gsap-reveal text-3d-matte text-2xl sm:text-3xl md:text-[2.25rem] lg:text-[3rem] xl:text-[3.5rem] 2xl:text-[4rem] font-bold tracking-tight mb-2 md:mb-3 leading-[1.1] text-center whitespace-normal lg:whitespace-nowrap">
          {tagline1}
        </h1>
        <h1 className="text-days gsap-reveal text-silver-matte text-2xl sm:text-3xl md:text-[2.25rem] lg:text-[3rem] xl:text-[3.5rem] 2xl:text-[4rem] font-extrabold tracking-tighter leading-[1.1] text-center whitespace-normal lg:whitespace-nowrap">
          {tagline2}
        </h1>
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
          Get Started →
        </SpecularButton>
      </div>

      {/* FOREGROUND LAYER: The Physical Deep Blue Card */}
      <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none" style={{ perspective: "1500px" }}>
        <div
          ref={mainCardRef}
          className="main-card premium-depth-card relative overflow-hidden gsap-reveal flex items-center justify-center pointer-events-auto w-[96vw] md:w-[94vw] lg:w-[92vw] max-w-[1550px] h-[92vh] md:h-[86vh] lg:h-[82vh] rounded-[28px] md:rounded-[36px]"
        >
          <div className="card-sheen" aria-hidden="true" />

          {/* DYNAMIC RESPONSIVE 5-SECTION COMPOSITION */}
          <div className="relative w-full h-full max-w-[1500px] mx-auto px-3 lg:px-6 flex flex-col justify-evenly lg:grid lg:grid-cols-12 items-center gap-3 lg:gap-4 z-10 py-3 lg:py-0">
            
            {/* 1. LEFT TEXT DESCRIPTION (Desktop: cols 1-3 / order 1) */}
            <div className="card-left-text gsap-reveal order-1 lg:col-span-3 flex flex-col justify-center text-center lg:text-left z-20 w-full px-2 lg:px-3">
              <h3
                className="text-white text-lg md:text-2xl lg:text-3xl font-bold mb-1.5 lg:mb-3 tracking-tight"
                style={{ color: '#ffffff', WebkitTextFillColor: '#ffffff', textShadow: '0 2px 12px rgba(0,0,0,0.6)' }}
              >
                {cardHeading}
              </h3>
              <p className="hidden md:block text-blue-100/70 text-xs md:text-sm lg:text-sm font-normal leading-relaxed mx-auto lg:mx-0 max-w-sm lg:max-w-none">
                {cardDescription}
              </p>
            </div>

            {/* 2. LEFT FEATURE CARDS STACK (Desktop: cols 4-5 / order 2) */}
            <div className="order-2 lg:col-span-2 flex flex-col justify-center space-y-4 lg:space-y-5 xl:space-y-6 z-20 w-full">
              {/* Card 1: Explainable AI Scoring */}
              <div className="floating-badge relative group flex items-center gap-1.5 lg:gap-2 w-full">
                <div className="flex-1 floating-ui-badge rounded-xl p-2.5 lg:p-3 flex items-center gap-2.5 shadow-lg border border-white/10 backdrop-blur-md bg-neutral-900/60 hover:bg-neutral-800/80 transition-all duration-300">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-b from-blue-500/20 to-blue-900/10 flex items-center justify-center border border-blue-400/30 shrink-0">
                    <span className="text-xs lg:text-sm drop-shadow-md">⚡</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight truncate">Explainable AI Scoring</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium truncate">SHAP human-readable reasoning</p>
                  </div>
                </div>
                <div className="hidden lg:flex items-center text-blue-400/70 shrink-0 w-5 xl:w-7" aria-hidden="true">
                  <div className="h-[1px] w-full bg-gradient-to-r from-blue-400/30 to-blue-400/80 border-t border-dashed border-blue-400/70" />
                  <span className="text-[10px] -ml-1 text-blue-400 font-bold">►</span>
                </div>
              </div>

              {/* Card 2: Risk-Ranked Accounts */}
              <div className="floating-badge relative group flex items-center gap-1.5 lg:gap-2 w-full">
                <div className="flex-1 floating-ui-badge rounded-xl p-2.5 lg:p-3 flex items-center gap-2.5 shadow-lg border border-white/10 backdrop-blur-md bg-neutral-900/60 hover:bg-neutral-800/80 transition-all duration-300">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-b from-amber-500/20 to-amber-900/10 flex items-center justify-center border border-amber-400/30 shrink-0">
                    <span className="text-xs lg:text-sm drop-shadow-md">📊</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight truncate">Risk-Ranked Accounts</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium truncate">Sortable, filterable, color-coded tiers</p>
                  </div>
                </div>
                <div className="hidden lg:flex items-center text-blue-400/70 shrink-0 w-5 xl:w-7" aria-hidden="true">
                  <div className="h-[1px] w-full bg-gradient-to-r from-blue-400/30 to-blue-400/80 border-t border-dashed border-blue-400/70" />
                  <span className="text-[10px] -ml-1 text-blue-400 font-bold">►</span>
                </div>
              </div>

              {/* Card 3: Upload & Ingestion */}
              <div className="floating-badge relative group flex items-center gap-1.5 lg:gap-2 w-full">
                <div className="flex-1 floating-ui-badge rounded-xl p-2.5 lg:p-3 flex items-center gap-2.5 shadow-lg border border-white/10 backdrop-blur-md bg-neutral-900/60 hover:bg-neutral-800/80 transition-all duration-300">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-b from-emerald-500/20 to-emerald-900/10 flex items-center justify-center border border-emerald-400/30 shrink-0">
                    <span className="text-xs lg:text-sm drop-shadow-md">☁️</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight truncate">Upload &amp; Ingestion</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium truncate">Drag-and-drop CSV, instant preview</p>
                  </div>
                </div>
                <div className="hidden lg:flex items-center text-blue-400/70 shrink-0 w-5 xl:w-7" aria-hidden="true">
                  <div className="h-[1px] w-full bg-gradient-to-r from-blue-400/30 to-blue-400/80 border-t border-dashed border-blue-400/70" />
                  <span className="text-[10px] -ml-1 text-blue-400 font-bold">►</span>
                </div>
              </div>

              {/* Card 4: Alerts & Case Management */}
              <div className="floating-badge relative group flex items-center gap-1.5 lg:gap-2 w-full">
                <div className="flex-1 floating-ui-badge rounded-xl p-2.5 lg:p-3 flex items-center gap-2.5 shadow-lg border border-white/10 backdrop-blur-md bg-neutral-900/60 hover:bg-neutral-800/80 transition-all duration-300">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-b from-red-500/20 to-red-900/10 flex items-center justify-center border border-red-400/30 shrink-0">
                    <span className="text-xs lg:text-sm drop-shadow-md">⚠️</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight truncate">Alerts &amp; Case Management</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium truncate">Severity alerts &amp; analyst workflow</p>
                  </div>
                </div>
                <div className="hidden lg:flex items-center text-blue-400/70 shrink-0 w-5 xl:w-7" aria-hidden="true">
                  <div className="h-[1px] w-full bg-gradient-to-r from-blue-400/30 to-blue-400/80 border-t border-dashed border-blue-400/70" />
                  <span className="text-[10px] -ml-1 text-blue-400 font-bold">►</span>
                </div>
              </div>
            </div>

            {/* 3. CENTER: CLEAN PHONE MOCKUP (Desktop: cols 6-7 / order 3) */}
            <div className="mockup-scroll-wrapper order-3 lg:col-span-2 relative w-full h-[420px] md:h-[500px] lg:h-[560px] flex items-center justify-center z-10 my-1 lg:my-0" style={{ perspective: "1000px" }}>
              <div className="relative w-full h-full flex items-center justify-center transform scale-[0.66] md:scale-[0.78] lg:scale-[0.86]">
                <div
                  ref={mockupRef}
                  className="relative w-[280px] h-[570px] rounded-[3rem] iphone-bezel flex flex-col will-change-transform transform-style-3d shadow-[0_30px_70px_rgba(0,0,0,0.85)] shrink-0"
                >
                  {/* Physical Hardware Buttons */}
                  <div className="absolute top-[120px] -left-[3px] w-[3px] h-[24px] hardware-btn rounded-l-md z-0" aria-hidden="true" />
                  <div className="absolute top-[156px] -left-[3px] w-[3px] h-[44px] hardware-btn rounded-l-md z-0" aria-hidden="true" />
                  <div className="absolute top-[212px] -left-[3px] w-[3px] h-[44px] hardware-btn rounded-l-md z-0" aria-hidden="true" />
                  <div className="absolute top-[166px] -right-[3px] w-[3px] h-[68px] hardware-btn rounded-r-md z-0 scale-x-[-1]" aria-hidden="true" />

                  {/* Inner Screen Container */}
                  <div className="absolute inset-[7px] bg-[#050914] rounded-[2.5rem] overflow-hidden shadow-[inset_0_0_20px_rgba(0,0,0,1)] text-white z-10">
                    <div className="absolute inset-0 screen-glare z-40 pointer-events-none" aria-hidden="true" />

                    {/* Dynamic Island Notch */}
                    <div className="absolute top-[7px] left-1/2 -translate-x-1/2 w-[96px] h-[24px] bg-black rounded-full z-50 flex items-center justify-end px-3 shadow-[inset_0_-1px_2px_rgba(255,255,255,0.1)]">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)] animate-pulse" />
                    </div>

                    {/* App Interface */}
                    <div className="relative w-full h-full pt-10 px-4.5 pb-7 flex flex-col justify-between">
                      
                      {/* Header */}
                      <div className="phone-widget flex justify-between items-center mb-2">
                        <div className="flex flex-col">
                          <span className="text-[9px] text-neutral-400 uppercase tracking-widest font-bold mb-0.5">Live Telemetry</span>
                          <span className="text-lg font-extrabold tracking-tight text-white drop-shadow-md">Risk Engine</span>
                        </div>
                        <div className="w-9 h-9 rounded-full bg-white/5 text-neutral-200 flex items-center justify-center font-bold text-xs border border-white/10 shadow-lg shadow-black/50">GNN</div>
                      </div>

                      {/* Circle Gauge */}
                      <div className="phone-widget relative w-40 h-40 mx-auto flex items-center justify-center mb-2 drop-shadow-[0_15px_25px_rgba(0,0,0,0.8)]">
                        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 160 160" aria-hidden="true">
                          <circle cx="80" cy="80" r="60" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="11" />
                          <circle className="progress-ring" cx="80" cy="80" r="60" fill="none" stroke="#3B82F6" strokeWidth="11" strokeDasharray="377" strokeDashoffset="90" strokeLinecap="round" />
                          <path id="textArc" d="M 32,98 A 54,54 0 0,0 128,98" fill="none" />
                          <text className="fill-blue-200/50 text-[7px] font-bold tracking-[0.15em] uppercase">
                            <textPath href="#textArc" startOffset="50%" textAnchor="middle">
                              ACCOUNT MONITORED
                            </textPath>
                          </text>
                        </svg>
                        <div className="text-center z-10 flex flex-col items-center pt-1">
                          <span className="counter-val text-4xl font-black tracking-tighter text-white">0</span>
                          <span className="text-[8px] text-blue-200/60 uppercase tracking-[0.12em] font-bold mt-0.5">{metricLabel}</span>
                        </div>
                      </div>

                      {/* 3 Internal Cards */}
                      <div className="space-y-2">
                        {/* Card 1: Alerts & Case Management */}
                        <div className="phone-widget widget-depth rounded-xl p-2.5 flex items-center bg-white/[0.03] border border-white/5">
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-600/10 flex items-center justify-center mr-2.5 border border-amber-400/30 shadow-inner flex-shrink-0">
                            <span className="text-xs">🔔</span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-[10px] font-bold text-white tracking-tight truncate">Alerts &amp; Case Management</div>
                            <div className="text-[8px] text-neutral-400 truncate">Severity alerts &amp; analyst workflow</div>
                          </div>
                        </div>

                        {/* Card 2: Model Metrics & Simulation */}
                        <div className="phone-widget widget-depth rounded-xl p-2.5 flex items-center bg-white/[0.03] border border-white/5">
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-blue-600/10 flex items-center justify-center mr-2.5 border border-blue-400/30 shadow-inner flex-shrink-0">
                            <span className="text-xs">🎯</span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-[10px] font-bold text-white tracking-tight truncate">Model Metrics &amp; Simulation</div>
                            <div className="text-[8px] text-neutral-400 truncate">Precision, ROC-AUC &amp; live streaming</div>
                          </div>
                        </div>

                        {/* Card 3: Transaction Network Graph */}
                        <div className="phone-widget widget-depth rounded-xl p-2.5 flex items-center bg-white/[0.03] border border-white/5">
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500/20 to-indigo-600/10 flex items-center justify-center mr-2.5 border border-indigo-400/30 shadow-inner flex-shrink-0">
                            <span className="text-xs">🛡️</span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-[10px] font-bold text-white tracking-tight truncate">Transaction Network Graph</div>
                            <div className="text-[8px] text-neutral-400 truncate">Force-directed mule ring engine</div>
                          </div>
                        </div>
                      </div>

                      {/* Bottom Home Bar */}
                      <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-[110px] h-[3px] bg-white/20 rounded-full shadow-[0_1px_2px_rgba(0,0,0,0.5)]" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 4. RIGHT FEATURE CARDS STACK (Desktop: cols 8-9 / order 4) */}
            <div className="order-4 lg:col-span-2 flex flex-col justify-center space-y-4 lg:space-y-5 xl:space-y-6 z-20 w-full">
              {/* Card 1: Model Metrics & Simulation */}
              <div className="floating-badge relative group flex items-center gap-1.5 lg:gap-2 w-full">
                <div className="hidden lg:flex items-center text-blue-400/70 shrink-0 w-5 xl:w-7" aria-hidden="true">
                  <span className="text-[10px] -mr-1 text-blue-400 font-bold">◄</span>
                  <div className="h-[1px] w-full bg-gradient-to-r from-blue-400/80 to-blue-400/30 border-t border-dashed border-blue-400/70" />
                </div>
                <div className="flex-1 floating-ui-badge rounded-xl p-2.5 lg:p-3 flex items-center gap-2.5 shadow-lg border border-white/10 backdrop-blur-md bg-neutral-900/60 hover:bg-neutral-800/80 transition-all duration-300">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-b from-indigo-500/20 to-indigo-900/10 flex items-center justify-center border border-indigo-400/30 shrink-0">
                    <span className="text-xs lg:text-sm drop-shadow-md">✉️</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight truncate">Model Metrics &amp; Simulation</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium truncate">Precision, Recall &amp; what-if modeling</p>
                  </div>
                </div>
              </div>

              {/* Card 2: Transaction Network Graph */}
              <div className="floating-badge relative group flex items-center gap-1.5 lg:gap-2 w-full">
                <div className="hidden lg:flex items-center text-blue-400/70 shrink-0 w-5 xl:w-7" aria-hidden="true">
                  <span className="text-[10px] -mr-1 text-blue-400 font-bold">◄</span>
                  <div className="h-[1px] w-full bg-gradient-to-r from-blue-400/80 to-blue-400/30 border-t border-dashed border-blue-400/70" />
                </div>
                <div className="flex-1 floating-ui-badge rounded-xl p-2.5 lg:p-3 flex items-center gap-2.5 shadow-lg border border-white/10 backdrop-blur-md bg-neutral-900/60 hover:bg-neutral-800/80 transition-all duration-300">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-b from-cyan-500/20 to-cyan-900/10 flex items-center justify-center border border-cyan-400/30 shrink-0">
                    <span className="text-xs lg:text-sm drop-shadow-md">🎯</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight truncate">Transaction Network Graph</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium truncate">Force-directed mule ring engine</p>
                  </div>
                </div>
              </div>

              {/* Card 3: Model Metrics & Simulation */}
              <div className="floating-badge relative group flex items-center gap-1.5 lg:gap-2 w-full">
                <div className="hidden lg:flex items-center text-blue-400/70 shrink-0 w-5 xl:w-7" aria-hidden="true">
                  <span className="text-[10px] -mr-1 text-blue-400 font-bold">◄</span>
                  <div className="h-[1px] w-full bg-gradient-to-r from-blue-400/80 to-blue-400/30 border-t border-dashed border-blue-400/70" />
                </div>
                <div className="flex-1 floating-ui-badge rounded-xl p-2.5 lg:p-3 flex items-center gap-2.5 shadow-lg border border-white/10 backdrop-blur-md bg-neutral-900/60 hover:bg-neutral-800/80 transition-all duration-300">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-b from-violet-500/20 to-violet-900/10 flex items-center justify-center border border-violet-400/30 shrink-0">
                    <span className="text-xs lg:text-sm drop-shadow-md">📈</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight truncate">Model Metrics &amp; Simulation</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium truncate">Precision, ROC-AUC &amp; live streaming</p>
                  </div>
                </div>
              </div>

              {/* Card 4: Alerts & Case Management */}
              <div className="floating-badge relative group flex items-center gap-1.5 lg:gap-2 w-full">
                <div className="hidden lg:flex items-center text-blue-400/70 shrink-0 w-5 xl:w-7" aria-hidden="true">
                  <span className="text-[10px] -mr-1 text-blue-400 font-bold">◄</span>
                  <div className="h-[1px] w-full bg-gradient-to-r from-blue-400/80 to-blue-400/30 border-t border-dashed border-blue-400/70" />
                </div>
                <div className="flex-1 floating-ui-badge rounded-xl p-2.5 lg:p-3 flex items-center gap-2.5 shadow-lg border border-white/10 backdrop-blur-md bg-neutral-900/60 hover:bg-neutral-800/80 transition-all duration-300">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-b from-rose-500/20 to-rose-900/10 flex items-center justify-center border border-rose-400/30 shrink-0">
                    <span className="text-xs lg:text-sm drop-shadow-md">🔔</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-[11px] lg:text-xs font-bold tracking-tight truncate">Alerts &amp; Case Management</p>
                    <p className="text-blue-200/50 text-[9px] lg:text-[10px] font-medium truncate">Severe alerts &amp; analyst workflow</p>
                  </div>
                </div>
              </div>
            </div>

            {/* 5. RIGHT BRANDING NAME (Desktop: cols 10-12 / order 5) */}
            <div className="card-right-text gsap-reveal order-5 lg:col-span-3 flex justify-center lg:justify-end z-20 w-full px-2 lg:px-3">
              <h2 className="text-3xl md:text-4xl lg:text-5xl xl:text-[4.25rem] 2xl:text-[4.75rem] font-black uppercase tracking-tighter text-card-silver-matte leading-[0.88] text-center lg:text-right flex flex-col items-center lg:items-end">
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

          </div>
        </div>
      </div>
    </div>
  );
}

export default CinematicHero;
