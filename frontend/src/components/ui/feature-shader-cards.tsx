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
      "Combine supervised and unsupervised intelligence to identify both known and emerging mule-account behavior in real time.",
    chips: ["XGBoost", "2,144:1 Imbalance", "Risk Score 0–100", "Isolation Forest", "Zero-Day Detection"],
    icon: (
      <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      colors: ["hsl(217, 91%, 12%)", "hsl(199, 89%, 36%)", "hsl(210, 95%, 20%)", "hsl(187, 100%, 50%)"],
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
      <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      colors: ["hsl(222, 85%, 14%)", "hsl(195, 92%, 38%)", "hsl(212, 82%, 22%)", "hsl(182, 95%, 45%)"],
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
      <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      colors: ["hsl(214, 95%, 13%)", "hsl(188, 100%, 34%)", "hsl(203, 90%, 24%)", "hsl(178, 100%, 48%)"],
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
      <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      colors: ["hsl(217, 85%, 16%)", "hsl(192, 88%, 42%)", "hsl(208, 92%, 21%)", "hsl(183, 100%, 52%)"],
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
      <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      colors: ["hsl(220, 92%, 11%)", "hsl(196, 96%, 36%)", "hsl(207, 88%, 25%)", "hsl(186, 100%, 55%)"],
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
    <section className="relative w-full py-16 lg:py-24 px-4 sm:px-6 lg:px-8 bg-neutral-950 text-white overflow-hidden border-t border-white/10">
      {/* Background Radial Ambient Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-blue-600/10 rounded-full blur-[140px] pointer-events-none" aria-hidden="true" />

      <div className="max-w-7xl mx-auto relative z-10">
        
        {/* Section Header - Matched to MuleScope Core Hero Typography */}
        <div className="text-center mb-12 lg:mb-16 space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-blue-500/10 border border-blue-400/30 text-blue-400 text-[11px] font-black uppercase tracking-[0.25em] shadow-lg">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            MULESCOPE INTELLIGENCE
          </div>

          <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-black uppercase tracking-tight text-white drop-shadow-md">
            Built to Detect What <span className="text-blue-400">Others Miss</span>
          </h2>

          <p className="text-xs sm:text-sm md:text-base text-blue-200/60 max-w-3xl mx-auto font-medium leading-relaxed">
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6 lg:gap-8 max-w-4xl mx-auto w-full">
          {features.slice(3, 5).map((feature) => (
            <FeatureCard key={feature.id} feature={feature} reduceMotion={reduceMotion} />
          ))}
        </div>

      </div>
    </section>
  );
}

function FeatureCard({ feature, reduceMotion }: { feature: FeatureCardData; reduceMotion: boolean }) {
  const [hasWebGLError, setHasWebGLError] = useState(false);

  return (
    <div className="relative group flex flex-col justify-between rounded-2xl lg:rounded-3xl overflow-hidden border border-white/10 bg-neutral-900/60 backdrop-blur-xl hover:border-blue-400/50 hover:bg-neutral-800/80 transition-all duration-300 hover:-translate-y-1.5 hover:shadow-[0_15px_35px_rgba(59,130,246,0.2)]">
      
      {/* Background Animated WebGL Shader */}
      {!reduceMotion && !hasWebGLError && (
        <div className="absolute inset-0 opacity-35 group-hover:opacity-55 transition-opacity duration-500 pointer-events-none rounded-2xl lg:rounded-3xl overflow-hidden">
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

      {/* Glass Overlay Shader Pattern */}
      <div className="absolute inset-0 bg-gradient-to-b from-neutral-950/40 via-neutral-950/75 to-neutral-950/90 pointer-events-none" />

      {/* Card Body Container */}
      <div className="relative z-10 p-6 sm:p-7 flex flex-col justify-between flex-1 space-y-5">
        
        {/* Top Header Block */}
        <div className="space-y-3.5">
          {/* Eyebrow & Icon Badge Row */}
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded-full border border-blue-400/20">
              {feature.eyebrow}
            </span>
            <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-400/30 flex items-center justify-center shadow-md group-hover:scale-105 group-hover:border-blue-400/60 transition-all duration-300">
              {feature.icon}
            </div>
          </div>

          {/* Feature Title */}
          <h3 className="text-lg sm:text-xl font-extrabold tracking-tight text-white group-hover:text-blue-300 transition-colors">
            {feature.title}
          </h3>

          {/* Feature Description */}
          <p className="text-xs sm:text-sm text-neutral-300/80 leading-relaxed font-normal">
            {feature.description}
          </p>
        </div>

        {/* Bottom Metadata & Actions Block */}
        <div className="space-y-4 pt-2">
          {/* Technical Chips */}
          <div className="flex flex-wrap gap-1.5">
            {feature.chips.map((chip, idx) => (
              <span
                key={idx}
                className="text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md bg-white/5 border border-white/10 text-neutral-300 group-hover:border-blue-400/30 group-hover:text-blue-200 transition-colors"
              >
                {chip}
              </span>
            ))}
          </div>

          {/* Footer Action Bar */}
          <div className="flex items-center justify-between text-[11px] font-extrabold uppercase tracking-wider text-blue-400 group-hover:text-cyan-300 pt-3 border-t border-white/10">
            <span>Capability Specs</span>
            <div className="flex items-center gap-1">
              <span>Explore</span>
              <svg className="w-3.5 h-3.5 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </div>
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
