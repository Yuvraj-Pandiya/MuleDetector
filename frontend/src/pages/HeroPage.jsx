import React from 'react';
import { useNavigate } from 'react-router-dom';
import { CinematicHero } from '@/components/ui/cinematic-landing-hero';

export default function HeroPage() {
  const navigate = useNavigate();

  return (
    <div className="overflow-x-hidden w-[100%] min-h-screen">
      <CinematicHero
        brandName="SAGE"
        tagline1="Mule network detection,"
        tagline2="redefined for banking AI."
        cardHeading="Financial crime intelligence."
        cardDescription={
          <>
            <span className="text-white font-semibold">SAGE</span> empowers compliance teams with multi-hop GNN detection, SHAP auditability, and real-time pass-through account tracking.
          </>
        }
        metricValue={1247}
        metricLabel="Accounts Monitored"
        ctaHeading="Eliminate mule rings."
        ctaDescription="Ingest transaction telemetry in real-time or evaluate historical data with multi-hop GNN detection."
        onPrimaryClick={() => navigate('/dashboard')}
        onSecondaryClick={() => navigate('/upload')}
      />
    </div>
  );
}
