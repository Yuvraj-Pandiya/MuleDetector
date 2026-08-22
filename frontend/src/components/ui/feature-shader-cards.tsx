"use client";

import React, { useState, useEffect } from "react";
import { Warp } from "@paper-design/shaders-react";

interface FeatureCardData {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  chips: string[];
  icon: React.ReactNode;
  shader: {
    proportion: number;
    softness: number;
    distortion: number;
    swirl: number;
    swirlIterations: number;
    shape: "checks" | "dots";
    shapeScale: number;
    colors: string[];
  };
}

const features: FeatureCardData[] = [
  {
    id: "dual-ai",
    eyebrow: "01 — HYBRID ML",
    title: "Dual AI/ML Detection Engine",
    description:
      "Combine supervised and unsupervised intelligence to identify both known and emerging mule-account behavior.",
    chips: ["XGBoost", "2,144:1 Imbalance", "Risk Score 0–100", "Isolation Forest", "Zero-Day Detection"],
    icon: (
      <svg className="w-5 h-5 text-zinc-100" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    shader: {
      proportion: 0.35,
      softness: 0.9,
      distortion: 0.15,
      swirl: 0.65,
      swirlIterations: 8,
      shape: "dots",
      shapeScale: 0.08,
      colors: ["hsl(0, 0%, 6%)", "hsl(0, 0%, 22%)", "hsl(0, 0%, 12%)", "hsl(0, 0%, 35%)"],
    },
  },
  {
    id: "graph-topology",
    eyebrow: "02 — NETWORK GRAPH",
    title: "Transaction Graph Topology",
    description:
      "Map the hidden structure of financial relationships to expose mule rings, laundering hubs, and circular transaction paths.",
    chips: ["Mule Rings", "High Density", "diag(A²+A³+A⁴)", "PageRank", "Hub Centrality"],
    icon: (
      <svg className="w-5 h-5 text-zinc-100" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 21a9 9 0 100-18 9 9 0 000 18ptM9 10a2 2 0 11-4 0 2 2 0 014 0zM19 10a2 2 0 11-4 0 2 2 0 014 0zM14 17a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
    shader: {
      proportion: 0.4,
      softness: 1.1,
      distortion: 0.18,
      swirl: 0.8,
      swirlIterations: 10,
      shape: "checks",
      shapeScale: 0.1,
      colors: ["hsl(220, 5%, 8%)", "hsl(220, 5%, 24%)", "hsl(220, 5%, 14%)", "hsl(220, 5%, 38%)"],
    },
  },
  {
    id: "zero-leakage",
    eyebrow: "03 — FEATURE ENGINEERING",
    title: "74 Zero-Leakage Features",
    description:
      "Extract temporal, behavioral, and transaction-flow signals without leaking future information into model decisions.",
    chips: ["74 Signals", "FIFO Matching", "5m-7d Windows", "11PM-5AM", "Spike Detection"],
    icon: (
      <svg className="w-5 h-5 text-zinc-100" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    shader: {
      proportion: 0.38,
      softness: 0.95,
      distortion: 0.16,
      swirl: 0.7,
      swirlIterations: 9,
      shape: "dots",
      shapeScale: 0.09,
      colors: ["hsl(0, 0%, 7%)", "hsl(0, 0%, 20%)", "hsl(0, 0%, 13%)", "hsl(0, 0%, 32%)"],
    },
  },
  {
    id: "explainable-ai",
    eyebrow: "04 — GOVERNANCE",
    title: "Explainable AI & Compliance Audit",
    description:
      "Turn every risk score into an investigator-ready explanation and preserve the complete compliance decision trail.",
    chips: ["SHAP Reasoning", "Attribution", "Confirmed Mule", "False Positive", "Audit Logs"],
    icon: (
      <svg className="w-5 h-5 text-zinc-100" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    shader: {
      proportion: 0.42,
      softness: 1.0,
      distortion: 0.17,
      swirl: 0.75,
      swirlIterations: 11,
      shape: "checks",
      shapeScale: 0.11,
      colors: ["hsl(0, 0%, 8%)", "hsl(0, 0%, 26%)", "hsl(0, 0%, 15%)", "hsl(0, 0%, 40%)"],
    },
  },
  {
    id: "real-time",
    eyebrow: "05 — LIVE TELEMETRY",
    title: "Real-Time Telemetry",
    description:
      "Monitor transaction risk continuously with live scoring, model-health signals, and rapid dataset ingestion.",
    chips: ["WebSocket Ticker", "Sub-Second", "PSI Drift", "PaySim & CSV", "Auto Quality"],
    icon: (
      <svg className="w-5 h-5 text-zinc-100" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    shader: {
      proportion: 0.36,
      softness: 0.9,
      distortion: 0.16,
      swirl: 0.65,
      swirlIterations: 8,
      shape: "dots",
      shapeScale: 0.08,
      colors: ["hsl(220, 4%, 6%)", "hsl(220, 4%, 21%)", "hsl(220, 4%, 11%)", "hsl(220, 4%, 30%)"],
    },
  },
];

export default function FeatureShaderCards() {
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mediaQuery.matches);
    const listener = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mediaQuery.addEventListener("change", listener);
    return () => mediaQuery.removeEventListener("change", listener);
  }, []);

  return (
    <section className="relative w-full py-16 lg:py-24 px-4 sm:px-6 lg:px-8 bg-black text-white overflow-hidden border-t border-zinc-900 font-sans antialiased flex flex-col items-center justify-center">
      {/* Background Radial Glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-white/[0.02] rounded-full blur-[150px] pointer-events-none" aria-hidden="true" />

      <div className="w-full max-w-[1360px] mx-auto relative z-10 flex flex-col items-center text-center">
        
        {/* Section Header: Matching Reference Screenshot Exactly */}
        <div className="flex flex-col items-center text-center max-w-4xl mx-auto mb-12 lg:mb-14 space-y-4 w-full">
          
          {/* Eyebrow Badge */}
          <div className="inline-flex items-center justify-center gap-2 px-4 py-1 rounded-full bg-zinc-900/90 border border-zinc-800 text-zinc-300 text-xs font-bold uppercase tracking-[0.25em]">
            <span>•</span>
            <span>MULESCOPE INTELLIGENCE</span>
            <span>•</span>
          </div>

          {/* Heading */}
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black uppercase tracking-tight text-white leading-[1.15] text-center w-full max-w-3xl">
            BUILT TO DETECT WHAT OTHERS MISS
          </h2>

          {/* Subtitle / Description */}
          <p className="text-sm sm:text-base text-zinc-400 max-w-2xl mx-auto font-normal leading-relaxed text-center">
            Five intelligence layers combine machine learning, transaction topology, behavioral signals, explainability, and real-time telemetry to expose coordinated mule activity.
          </p>
        </div>

        {/* 5-Card Layout: Responsive Grid (1 column on mobile, 2 on tablet, 3 on desktop) */}
        <div className="w-full max-w-[1400px] mx-auto space-y-6 lg:space-y-8">
          
          {/* Row 1: 3 Cards on Desktop, 2 on Tablet, 1 on Mobile */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8 w-full">
            {features.slice(0, 3).map((feature) => (
              <FeatureCard key={feature.id} feature={feature} reduceMotion={reduceMotion} />
            ))}
          </div>

          {/* Row 2: 2 Centered Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8 w-full max-w-[920px] mx-auto">
            {features.slice(3, 5).map((feature) => (
              <FeatureCard key={feature.id} feature={feature} reduceMotion={reduceMotion} />
            ))}
          </div>

        </div>

      </div>
    </section>
  );
}

function FeatureCard({ feature, reduceMotion }: { feature: FeatureCardData; reduceMotion: boolean }) {
  const [hasWebGLError, setHasWebGLError] = useState(false);

  return (
    <div className="relative group w-full h-full flex flex-col rounded-xl overflow-hidden border border-zinc-800/80 bg-zinc-950/90 backdrop-blur-xl hover:border-zinc-600 transition-all duration-500 hover:shadow-[0_8px_30px_rgba(0,0,0,0.9)]">
      
      {/* Background Animated WebGL Shader */}
      {!reduceMotion && !hasWebGLError && (
        <div className="absolute inset-0 opacity-20 group-hover:opacity-40 transition-opacity duration-500 pointer-events-none rounded-xl overflow-hidden">
          <ErrorBoundary onError={() => setHasWebGLError(true)}>
            <Warp
              style={{ height: "100%", width: "100%" }}
              proportion={feature.shader.proportion}
              softness={feature.shader.softness}
              distortion={feature.shader.distortion}
              swirl={feature.shader.swirl}
              swirlIterations={feature.shader.swirlIterations}
              shape={feature.shader.shape}
              shapeScale={feature.shader.shapeScale}
              scale={1}
              rotation={0}
              speed={0.4}
              colors={feature.shader.colors}
            />
          </ErrorBoundary>
        </div>
      )}

      {/* Minimal Black & White Hover Gradient Glow Overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-zinc-900/20 to-black opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none rounded-xl" />

      {/* Subtle Top Border White Highlight Line */}
      <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-white/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

      {/* Glass Tint Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-zinc-950/60 via-black/80 to-black/95 pointer-events-none" />

      {/* Card Content Container */}
      <div className="relative z-10 p-5 sm:p-6 lg:p-7 flex flex-col flex-1 h-full text-left">
        
        {/* Eyebrow & Icon Row */}
        <div className="flex items-center justify-between mb-3.5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-300 bg-zinc-900/90 group-hover:bg-zinc-800/90 group-hover:text-white px-3 py-1 rounded-full border border-zinc-800 group-hover:border-zinc-700 transition-colors">
            {feature.eyebrow}
          </span>
          <div className="w-8 h-8 rounded-lg bg-zinc-900/80 group-hover:bg-zinc-800/90 border border-zinc-800 group-hover:border-zinc-700 flex items-center justify-center text-zinc-300 group-hover:text-white shrink-0 transition-colors">
            {feature.icon}
          </div>
        </div>

        {/* Feature Title */}
        <h3 className="text-lg font-bold tracking-tight text-white mb-2 group-hover:text-zinc-100 transition-colors leading-snug">
          {feature.title}
        </h3>

        {/* Feature Description */}
        <p className="text-xs lg:text-sm text-zinc-400 font-normal leading-relaxed mb-4">
          {feature.description}
        </p>

        {/* Feature Specific Visual Graphic Badge Section */}
        <div className="mb-4 w-full">
          <FeatureVisualGraphic featureId={feature.id} />
        </div>

        {/* Technical Chips */}
        <div className="flex flex-wrap gap-1.5">
          {feature.chips.map((chip, idx) => (
            <span
              key={idx}
              className="text-[11px] font-medium tracking-wide px-2.5 py-0.5 rounded-full bg-zinc-900/90 group-hover:bg-zinc-800/80 border border-zinc-800 group-hover:border-zinc-700 text-zinc-300 group-hover:text-zinc-200 transition-colors"
            >
              {chip}
            </span>
          ))}
        </div>

      </div>
    </div>
  );
}

function FeatureVisualGraphic({ featureId }: { featureId: string }) {
  const boxHoverClasses = "w-full bg-gradient-to-r from-black via-zinc-950 to-black hover:from-zinc-900 hover:via-zinc-800/60 hover:to-zinc-950 border border-zinc-800 hover:border-zinc-600/80 hover:shadow-[0_0_20px_rgba(255,255,255,0.06)] transition-all duration-500 rounded-lg p-3 sm:p-3.5 px-3.5 sm:px-4 overflow-hidden box-border";

  switch (featureId) {
    case "dual-ai":
      return (
        <div className={`${boxHoverClasses} flex flex-col gap-2`}>
          <div className="flex items-center justify-between text-xs gap-2 min-w-0 w-full">
            <span className="flex items-center gap-1.5 font-bold text-zinc-200 min-w-0 truncate">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)] shrink-0" />
              <span className="truncate text-[11px] sm:text-xs">XGBoost + Isolation Forest</span>
            </span>
            <span className="text-[10px] sm:text-[11px] font-mono text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800 shrink-0 ml-auto">
              99.4% ROC-AUC
            </span>
          </div>
          <div className="flex items-center justify-between gap-2.5 mt-0.5 min-w-0 w-full">
            <div className="flex-1 bg-zinc-900 rounded-full h-1.5 overflow-hidden border border-zinc-800 min-w-0">
              <div className="bg-gradient-to-r from-zinc-400 to-white h-full w-[94%]" />
            </div>
            <span className="text-[10px] sm:text-[11px] font-mono text-zinc-400 shrink-0">14ms</span>
          </div>
        </div>
      );

    case "graph-topology":
      return (
        <div className={`${boxHoverClasses} flex items-center justify-between gap-2`}>
          <div className="flex items-center gap-2.5 min-w-0 truncate">
            {/* SVG Network Topology Node Diagram matching reference image */}
            <svg className="w-10 h-6 text-zinc-300 shrink-0" viewBox="0 0 48 36" fill="none">
              <circle cx="10" cy="18" r="4" fill="#E4E4E7" />
              <circle cx="24" cy="8" r="5" fill="#FFFFFF" />
              <circle cx="24" cy="28" r="4" fill="#A1A1AA" />
              <circle cx="38" cy="18" r="4.5" fill="#E4E4E7" />
              <path d="M14 16L20 10M14 20L20 26M28 10L34 16M28 26L34 20" stroke="#71717A" strokeWidth="1.5" strokeDasharray="2 2" />
            </svg>
            <div className="flex flex-col text-left min-w-0 truncate">
              <span className="text-xs font-bold text-zinc-200 truncate">Mule Ring Density</span>
              <span className="text-[10px] sm:text-[11px] text-zinc-400 font-mono truncate">diag(A² + A³ + A⁴)</span>
            </div>
          </div>
          <span className="text-[10px] font-mono uppercase bg-zinc-900 px-2 py-0.5 rounded text-zinc-300 border border-zinc-800 font-bold shrink-0 ml-auto">
            PAGERANK
          </span>
        </div>
      );

    case "zero-leakage":
      return (
        <div className={`${boxHoverClasses} flex items-center justify-between gap-2`}>
          <div className="flex items-center gap-2.5 min-w-0 truncate">
            {/* Waveform / Sparkline SVG matching reference image */}
            <svg className="w-11 h-6 text-zinc-200 shrink-0" viewBox="0 0 64 32" fill="none">
              <path d="M0 20 L12 20 L18 8 L24 24 L30 14 L36 22 L44 10 L52 20 L64 20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <div className="flex flex-col text-left min-w-0 truncate">
              <span className="text-xs font-bold text-zinc-200 truncate">74 Signals Stream</span>
              <span className="text-[10px] sm:text-[11px] text-zinc-400 font-mono truncate">Zero Temporal Leak</span>
            </div>
          </div>
          <span className="text-[10px] font-mono bg-zinc-900 text-zinc-300 px-2 py-0.5 rounded border border-zinc-800 font-bold shrink-0 ml-auto">
            5m–7d
          </span>
        </div>
      );

    case "explainable-ai":
      return (
        <div className={`${boxHoverClasses} flex flex-col gap-2`}>
          <div className="flex justify-between items-center text-[10px] sm:text-[11px] font-mono text-zinc-300 min-w-0 w-full">
            <span className="truncate min-w-0">Amount Velocity</span>
            <span className="font-bold text-white shrink-0 ml-auto">+48% SHAP</span>
          </div>
          <div className="w-full bg-zinc-900 rounded-full h-1.5 overflow-hidden border border-zinc-800 min-w-0">
            <div className="bg-gradient-to-r from-zinc-400 to-white h-full w-[82%]" />
          </div>
          <div className="flex justify-between items-center text-[10px] sm:text-[11px] font-mono text-zinc-400 min-w-0 w-full">
            <span className="truncate min-w-0">Off-Hours Spike</span>
            <span className="font-bold text-zinc-300 shrink-0 ml-auto">+32% SHAP</span>
          </div>
        </div>
      );

    case "real-time":
      return (
        <div className={`${boxHoverClasses} flex items-center justify-between gap-2`}>
          <div className="flex items-center gap-2 min-w-0 truncate">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)] shrink-0" />
            <span className="text-xs font-bold text-zinc-200 truncate">WebSocket Ticker</span>
          </div>
          <div className="flex items-center gap-1.5 font-mono text-[10px] sm:text-[11px] text-zinc-300 bg-zinc-900 px-2 py-0.5 rounded-md border border-zinc-800 shrink-0 ml-auto">
            <span>&lt; 45ms</span>
            <span className="text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/50 text-[9px] font-bold">Live</span>
          </div>
        </div>
      );

    default:
      return null;
  }
}

class ErrorBoundary extends React.Component<{ children: React.ReactNode; onError: () => void }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch() {
    this.props.onError();
  }

  render() {
    if (this.state.hasError) {
      return null;
    }
    return this.props.children;
  }
}
