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
      <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      colors: ["hsl(215, 90%, 12%)", "hsl(190, 100%, 32%)", "hsl(205, 95%, 18%)", "hsl(185, 100%, 48%)"],
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
      <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      colors: ["hsl(220, 85%, 14%)", "hsl(195, 90%, 35%)", "hsl(210, 80%, 20%)", "hsl(180, 95%, 42%)"],
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
      <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      colors: ["hsl(210, 95%, 13%)", "hsl(185, 100%, 30%)", "hsl(200, 90%, 22%)", "hsl(175, 100%, 45%)"],
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
      <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      colors: ["hsl(215, 80%, 15%)", "hsl(190, 85%, 38%)", "hsl(205, 90%, 19%)", "hsl(180, 100%, 50%)"],
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
      <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      colors: ["hsl(220, 90%, 11%)", "hsl(195, 95%, 33%)", "hsl(205, 85%, 23%)", "hsl(185, 100%, 55%)"],
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
    <section className="relative w-full pt-28 md:pt-36 pb-24 lg:pb-32 px-4 sm:px-6 lg:px-8 bg-neutral-950 text-white overflow-hidden border-t border-white/10">
      {/* Background Ambient Radial Lighting */}
      <div
        className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-blue-600/10 rounded-full blur-[150px] pointer-events-none"
        aria-hidden="true"
      />

      <div className="max-w-7xl mx-auto relative z-10">
        
        {/* Section Header with Hero Typography Matching */}
        <div className="text-center mb-16 lg:mb-20 space-y-4 px-2">
          
          {/* Eyebrow Pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-neutral-900/80 border border-white/15 text-cyan-400 text-[11px] font-black uppercase tracking-[0.25em] shadow-lg backdrop-blur-md">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            MULESCOPE INTELLIGENCE
          </div>

          {/* Main Title Matching Hero Uppercase Matte Typography */}
          <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-black uppercase tracking-tighter text-white drop-shadow-xl leading-[1.05]">
            Built to Detect What{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400">
              Others Miss
            </span>
          </h2>

          {/* Subtitle */}
          <p className="text-blue-100/70 text-sm md:text-base lg:text-lg max-w-3xl mx-auto font-normal leading-relaxed text-center">
            Five intelligence layers combine machine learning, transaction topology, behavioral signals, explainability, and real-time telemetry to expose coordinated mule activity.
          </p>
        </div>

        {/* Row 1: Top 3 Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8 mb-6 lg:mb-8">
          {features.slice(0, 3).map((feature) => (
            <FeatureCard key={feature.id} feature={feature} reduceMotion={reduceMotion} />
          ))}
        </div>

        {/* Row 2: Bottom 2 Centered Cards */}
        <div className="flex flex-col md:flex-row justify-center items-stretch gap-6 lg:gap-8 max-w-5xl mx-auto">
          {features.slice(3, 5).map((feature) => (
            <div key={feature.id} className="w-full md:w-[calc(50%-12px)] lg:w-[calc(50%-16px)]">
              <FeatureCard feature={feature} reduceMotion={reduceMotion} />
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}

function FeatureCard({ feature, reduceMotion }: { feature: FeatureCardData; reduceMotion: boolean }) {
  const [hasWebGLError, setHasWebGLError] = useState(false);

  return (
    <div className="relative group h-full min-h-[380px] flex flex-col justify-between rounded-3xl overflow-hidden border border-white/10 bg-neutral-950/85 backdrop-blur-xl hover:border-cyan-400/50 transition-all duration-500 hover:-translate-y-1.5 hover:shadow-[0_15px_45px_rgba(56,189,248,0.22)] p-6 sm:p-7">
      
      {/* Background Animated WebGL Shader */}
      {!reduceMotion && !hasWebGLError && (
        <div className="absolute inset-0 opacity-35 group-hover:opacity-55 transition-opacity duration-700 pointer-events-none rounded-3xl overflow-hidden">
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

      {/* Subtle Dark Gradient Overlay for High Contrast */}
      <div className="absolute inset-0 bg-gradient-to-b from-neutral-950/60 via-neutral-950/85 to-neutral-950/98 pointer-events-none" />

      {/* Card Content Top Section */}
      <div className="relative z-10 flex flex-col space-y-4">
        
        {/* Eyebrow & Icon Row */}
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-cyan-400/90 bg-cyan-500/10 px-3 py-1 rounded-full border border-cyan-400/25">
            {feature.eyebrow}
          </span>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/10 border border-cyan-400/30 flex items-center justify-center shadow-md group-hover:scale-110 group-hover:border-cyan-400/60 transition-all duration-300">
            {feature.icon}
          </div>
        </div>

        {/* Feature Title */}
        <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-white group-hover:text-cyan-200 transition-colors leading-snug">
          {feature.title}
        </h3>

        {/* Feature Description */}
        <p className="text-xs sm:text-sm text-blue-100/70 font-normal leading-relaxed">
          {feature.description}
        </p>
      </div>

      {/* Card Content Bottom Section (Technical Chips & Link) */}
      <div className="relative z-10 mt-6 pt-4 border-t border-white/5 flex flex-col space-y-3">
        {/* Technical Chips */}
        <div className="flex flex-wrap gap-1.5">
          {feature.chips.map((chip, idx) => (
            <span
              key={idx}
              className="text-[10px] font-bold tracking-wider px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-cyan-200/80 group-hover:border-cyan-400/30 group-hover:text-cyan-300 transition-colors"
            >
              {chip}
            </span>
          ))}
        </div>

        {/* Capability Specs Link */}
        <div className="inline-flex items-center text-[11px] font-extrabold uppercase tracking-wider text-cyan-400 group-hover:text-cyan-300 transition-colors pt-1">
          <span className="mr-1.5">Capability Specs</span>
          <svg className="w-3.5 h-3.5 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>

    </div>
  );
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
