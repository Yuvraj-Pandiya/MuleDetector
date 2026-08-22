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
    chips: ["XGBoost", "2,144:1 Imbalance", "Risk 0–100", "Isolation Forest", "Zero-Day Detection"],
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
      colors: ["hsl(215, 90%, 10%)", "hsl(190, 100%, 28%)", "hsl(205, 95%, 15%)", "hsl(185, 100%, 42%)"],
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
      colors: ["hsl(220, 85%, 12%)", "hsl(195, 90%, 30%)", "hsl(210, 80%, 17%)", "hsl(180, 95%, 38%)"],
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
      colors: ["hsl(210, 95%, 11%)", "hsl(185, 100%, 26%)", "hsl(200, 90%, 18%)", "hsl(175, 100%, 40%)"],
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
      colors: ["hsl(215, 80%, 13%)", "hsl(190, 85%, 32%)", "hsl(205, 90%, 17%)", "hsl(180, 100%, 44%)"],
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
      colors: ["hsl(220, 90%, 10%)", "hsl(195, 95%, 28%)", "hsl(205, 85%, 19%)", "hsl(185, 100%, 48%)"],
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
    <section className="relative w-full pt-32 pb-24 lg:pt-36 lg:pb-32 px-4 sm:px-6 lg:px-8 bg-neutral-950 text-white overflow-hidden border-t border-white/10">
      {/* Background Glow Overlay matching Hero Section */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-blue-600/10 rounded-full blur-[150px] pointer-events-none" aria-hidden="true" />

      <div className="max-w-7xl mx-auto relative z-10">
        
        {/* Section Header with Clear Top Padding to clear fixed top-bar */}
        <div className="text-center mb-16 lg:mb-20 space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-500/10 border border-blue-400/25 text-blue-400 text-[10px] font-black uppercase tracking-[0.25em] shadow-inner">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            MULESCOPE INTELLIGENCE
          </div>

          <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-black uppercase tracking-tighter text-white leading-tight">
            Built to Detect What <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-cyan-300 to-indigo-400">Others Miss</span>
          </h2>

          <p className="text-xs sm:text-sm md:text-base lg:text-lg text-blue-100/70 max-w-3xl mx-auto font-normal leading-relaxed tracking-wide">
            Five intelligence layers combine machine learning, transaction topology, behavioral signals, explainability, and real-time telemetry to expose coordinated mule activity.
          </p>
        </div>

        {/* Row 1: Top 3 Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8 mb-6 lg:mb-8">
          {features.slice(0, 3).map((feature) => (
            <FeatureCard key={feature.id} feature={feature} reduceMotion={reduceMotion} />
          ))}
        </div>

        {/* Row 2: Bottom 2 Centered Cards matching Row 1 Width */}
        <div className="flex flex-col md:flex-row justify-center items-center gap-6 lg:gap-8 max-w-7xl mx-auto">
          {features.slice(3, 5).map((feature) => (
            <div key={feature.id} className="w-full md:w-[calc(50%-12px)] lg:w-[calc(33.333%-16px)]">
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
    <div className="relative group h-[390px] sm:h-[410px] flex flex-col justify-between rounded-2xl overflow-hidden border border-white/10 bg-neutral-900/70 backdrop-blur-xl hover:border-blue-400/50 transition-all duration-500 hover:-translate-y-2 hover:shadow-[0_15px_40px_rgba(59,130,246,0.25)]">
      
      {/* Background Animated WebGL Shader */}
      {!reduceMotion && !hasWebGLError && (
        <div className="absolute inset-0 opacity-30 group-hover:opacity-50 transition-opacity duration-700 pointer-events-none rounded-2xl overflow-hidden">
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

      {/* Dark Glass Overlay Matching Hero Aesthetics */}
      <div className="absolute inset-0 bg-gradient-to-b from-neutral-950/40 via-neutral-950/80 to-neutral-950/95 pointer-events-none" />

      {/* Card Body */}
      <div className="relative z-10 p-6 sm:p-7 flex flex-col h-full justify-between flex-1">
        
        {/* Top Part: Eyebrow, Icon, Title, Description */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <span className="text-[9px] font-extrabold uppercase tracking-[0.2em] text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded-full border border-blue-400/20">
              {feature.eyebrow}
            </span>
            <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-400/30 flex items-center justify-center shadow-lg group-hover:scale-110 group-hover:border-blue-400/60 transition-all duration-300 shrink-0">
              {feature.icon}
            </div>
          </div>

          <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-white mb-2.5 group-hover:text-blue-200 transition-colors">
            {feature.title}
          </h3>

          <p className="text-xs sm:text-sm text-blue-100/70 leading-relaxed font-normal">
            {feature.description}
          </p>
        </div>

        {/* Bottom Part: Chips & Footer Link */}
        <div className="space-y-4 pt-4">
          <div className="flex flex-wrap gap-1.5">
            {feature.chips.map((chip, idx) => (
              <span
                key={idx}
                className="text-[10px] font-bold tracking-wide px-2.5 py-0.5 rounded-md bg-white/5 border border-white/10 text-blue-200/80 group-hover:border-blue-400/30 group-hover:text-blue-300 transition-colors"
              >
                {chip}
              </span>
            ))}
          </div>

          <div className="pt-3 border-t border-white/10 flex items-center justify-between">
            <span className="text-[10px] font-extrabold uppercase tracking-widest text-blue-400 group-hover:text-cyan-300 transition-colors">
              CAPABILITY SPECS
            </span>
            <div className="flex items-center gap-1 text-[11px] font-extrabold text-blue-400 group-hover:text-cyan-300 transition-colors">
              <span>EXPLORE</span>
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
