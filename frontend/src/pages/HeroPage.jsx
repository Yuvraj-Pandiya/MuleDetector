import React from 'react';
import { useNavigate } from 'react-router-dom';
import { CinematicHero } from '@/components/ui/cinematic-landing-hero';

export default function HeroPage() {
  const navigate = useNavigate();

  return (
    <div className="overflow-x-hidden w-[100%] min-h-screen">
      <CinematicHero
        brandBadge="⚡ AI-POWERED FINANCIAL CRIME PLATFORM"
        brandName="MULE SCOPE"
        tagline="Expose Coordinated Money Mule Rings Before Funds Disappear"
        heroDescription="Autonomous anomaly detection, point-in-time transaction graph topology, and local SHAP explainability for next-generation AML compliance."
        primaryCtaLabel="Launch Risk Console →"
        secondaryCtaLabel="Upload PaySim Dataset (.CSV)"
        cardHeading="Transaction Graph Intelligence & Mule Ring Detection"
        cardDescription={
          <>
            Scores accounts in real time, explains every decision with human-readable <span className="text-white font-semibold">SHAP feature attribution</span>, and visualizes point-in-time transaction graphs to catch mule rings instantly.
          </>
        }
        metricValue={1247}
        metricLabel="Accounts Monitored"
        ctaHeading="Uncover Hidden Fraud & Mule Networks"
        ctaDescription="Drag-and-drop CSV dataset upload with column previews, risk-ranked account tables, transparent model performance metrics, and analyst case management."
        onGetStarted={() => navigate('/dashboard')}
        onPrimaryClick={() => navigate('/dashboard')}
        onSecondaryClick={() => navigate('/upload')}
      />
    </div>
  );
}
