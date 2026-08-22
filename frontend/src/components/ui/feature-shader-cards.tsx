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
      <svg className="w-4 h-4 text-zinc-100" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      <svg className="w-4 h-4 text-zinc-100" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      <svg className="w-4 h-4 text-zinc-100" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      <svg className="w-4 h-4 text-zinc-100" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
      <svg className="w-4 h-4 text-zinc-100" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
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
    <section className="relative w-full py-12 lg:py-16 px-4 sm:px-6 lg:px-8 bg-black text-white overflow-hidden border-t border-white/10 font-sans antialiased flex flex-col items-center justify-center">
      {/* Background Radial Glow Matching Hero Monochromatic Theme */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-white/5 rounded-full blur-[150px] pointer-events-none" aria-hidden="true" />

      <div className="w-full max-w-[1450px] mx-auto relative z-10 flex flex-col items-center text-center">
        
        {/* Section Header: Matching Hero Black & White / Silver-Matte Typography */}
        <div className="flex flex-col items-center text-center max-w-4xl mx-auto mb-10 lg:mb-12 space-y-3 w-full">
          
          {/* Eyebrow Badge */}
          <div className="inline-flex items-center justify-center gap-2 px-3.5 py-1 rounded-full bg-white/5 border border-white/15 text-zinc-300 text-xs lg:text-[13px] font-extrabold uppercase tracking-[0.35em] shadow-lg backdrop-blur-md">
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-300 animate-pulse" />
            MULESCOPE INTELLIGENCE
          </div>

          {/* Heading */}
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black uppercase tracking-tight text-white drop-shadow-md leading-[1.1] text-center w-full">
            Built to Detect What <span className="text-transparent bg-clip-text bg-gradient-to-b from-white via-zinc-200 to-zinc-400">Others Miss</span>
          </h2>

          {/* Subtitle / Description */}
          <p className="text-sm md:text-base text-zinc-400 max-w-3xl mx-auto font-normal leading-relaxed text-center">
            Five intelligence layers combine machine learning, transaction topology, behavioral signals, explainability, and real-time telemetry to expose coordinated mule activity.
          </p>
        </div>

        {/* 5-Card Layout: Centered Flex Wrapper */}
        <div className="flex flex-wrap justify-center items-stretch gap-5 lg:gap-6 w-full max-w-[1450px] mx-auto">
          {features.map((feature) => (
            <div
              key={feature.id}
              className="w-full sm:w-[calc(50%-10px)] lg:w-[calc(33.333%-16px)] max-w-[440px] flex flex-col"
            >
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
    <div className="relative group w-full h-full flex flex-col rounded-2xl overflow-hidden border border-white/10 bg-gradient-to-b from-zinc-900/80 via-zinc-950/90 to-black backdrop-blur-xl hover:border-white/30 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_8px_25px_rgba(255,255,255,0.06)]">
      
      {/* Background Animated WebGL Shader */}
      {!reduceMotion && !hasWebGLError && (
        <div className="absolute inset-0 opacity-30 group-hover:opacity-50 transition-opacity duration-500 pointer-events-none rounded-2xl overflow-hidden">
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

      {/* Glass Tint Fallback Pattern */}
      <div className="absolute inset-0 bg-gradient-to-b from-zinc-900/50 via-zinc-950/80 to-black/95 pointer-events-none" />

      {/* Card Content Container */}
      <div className="relative z-10 p-5 lg:p-6 flex flex-col justify-between flex-1 h-full">
        
        <div className="flex flex-col text-left">
          {/* Eyebrow & Icon Row */}
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-zinc-300 bg-white/5 px-2.5 py-0.5 rounded-full border border-white/10">
              {feature.eyebrow}
            </span>
            <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/15 flex items-center justify-center shadow-md group-hover:scale-105 group-hover:border-white/40 transition-all duration-300 shrink-0">
              {feature.icon}
            </div>
          </div>

          {/* Feature Title */}
          <h3 className="text-lg lg:text-xl font-bold tracking-tight text-white mb-2 group-hover:text-zinc-200 transition-colors">
            {feature.title}
          </h3>

          {/* Feature Description */}
          <p className="text-xs lg:text-[13px] text-zinc-400 font-normal leading-relaxed mb-4">
            {feature.description}
          </p>
        </div>

        {/* Technical Chips & Link */}
        <div className="mt-auto pt-1 text-left">
          <div className="flex flex-wrap gap-1.5 mb-3.5">
            {feature.chips.map((chip, idx) => (
              <span
                key={idx}
                className="text-[10px] font-semibold tracking-wide px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-zinc-300 group-hover:border-white/20 group-hover:text-white transition-colors"
              >
                {chip}
              </span>
            ))}
          </div>

          {/* Capability Specs Link */}
          <div className="flex items-center text-[11px] font-extrabold uppercase tracking-wider text-zinc-300 group-hover:text-white transition-colors">
            <span>Capability Specs</span>
            <svg className="w-3.5 h-3.5 ml-1.5 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
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
