import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CinematicHero } from '@/components/ui/cinematic-landing-hero';
import AuthModal from '@/components/ui/AuthModal';
import { useAuth } from '@/context/AuthContext';
import '@/components/ui/AuthModal.css';

export default function HeroPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('signup');

  const handleGetStarted = () => {
    if (isAuthenticated) {
      navigate('/dashboard');
    } else {
      setAuthModalMode('signup');
      setAuthModalOpen(true);
    }
  };

  return (
    <div className="overflow-x-hidden w-[100%] min-h-screen">
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
        onGetStarted={handleGetStarted}
        onPrimaryClick={handleGetStarted}
        onSecondaryClick={handleGetStarted}
      />
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
      />
    </div>
  );
}
