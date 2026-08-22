import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Shield, ArrowRight, FileSpreadsheet, Activity } from 'lucide-react';
import './cinematic-hero.css';

// Register GSAP plugin safely
if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

/**
 * CinematicHero Component
 * Premium metallic Raycast-inspired hero component with GSAP scroll-pinned animation & mouse parallax tilt.
 */
export function CinematicHero({
  brandName = "SAGE Financial Crime Intelligence",
  tagline1 = "Mule Network",
  tagline2 = "Detection Engine",
  cardHeading = "Graph Neural Intelligence & Explainable AI",
  cardDescription = (
    <>
      Targeting illicit money mule networks, rapid pass-through accounts, and circular transaction rings — built for enterprise compliance teams with full <span className="text-white font-semibold">SHAP auditability</span>.
    </>
  ),
  metricValue = 1247,
  metricLabel = "Monitored Accounts",
  ctaHeading = "Eliminate Mule Network Blind Spots",
  ctaDescription = "Ingest transaction telemetry in real-time or evaluate historical data with multi-hop GNN detection.",
  onPrimaryCtaClick,
  onSecondaryCtaClick,
}) {
  const containerRef = useRef(null);
  const cardRef = useRef(null);
  const metricNumRef = useRef(null);

  // Mouse Parallax Tilt Effect for Desktop
  useEffect(() => {
    const card = cardRef.current;
    if (!card) return;

    // Skip on touch devices
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    if (isTouchDevice) return;

    const handleMouseMove = (e) => {
      const rect = card.getBoundingClientRect();
      const cardCenterX = rect.left + rect.width / 2;
      const cardCenterY = rect.top + rect.height / 2;

      const rotateX = (e.clientY - cardCenterY) / -25;
      const rotateY = (e.clientX - cardCenterX) / 25;

      gsap.to(card, {
        rotateX: Math.max(-12, Math.min(12, rotateX)),
        rotateY: Math.max(-12, Math.min(12, rotateY)),
        duration: 0.5,
        ease: 'power2.out',
      });
    };

    const handleMouseLeave = () => {
      gsap.to(card, {
        rotateX: 0,
        rotateY: 0,
        duration: 0.8,
        ease: 'power3.out',
      });
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener('mousemove', handleMouseMove);
      container.addEventListener('mouseleave', handleMouseLeave);
    }

    return () => {
      if (container) {
        container.removeEventListener('mousemove', handleMouseMove);
        container.removeEventListener('mouseleave', handleMouseLeave);
      }
    };
  }, []);

  // GSAP Counter Animation & Fade-in Timeline
  useEffect(() => {
    const ctx = gsap.context(() => {
      // Counter animation for metricValue
      if (metricNumRef.current) {
        const obj = { val: 0 };
        gsap.to(obj, {
          val: metricValue,
          duration: 2,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: metricNumRef.current,
            start: 'top 85%',
            toggleActions: 'play none none reverse',
          },
          onUpdate: () => {
            if (metricNumRef.current) {
              metricNumRef.current.innerText = Math.floor(obj.val).toLocaleString();
            }
          },
        });
      }

      // Entry animations for title & card
      gsap.from('.cinematic-brand-badge', {
        opacity: 0,
        y: -20,
        duration: 0.8,
        ease: 'power3.out',
      });

      gsap.from('.cinematic-title-group', {
        opacity: 0,
        y: 30,
        duration: 1,
        delay: 0.2,
        ease: 'power3.out',
      });

      gsap.from('.cinematic-tilt-card', {
        opacity: 0,
        y: 40,
        duration: 1.2,
        delay: 0.4,
        ease: 'power3.out',
      });
    }, containerRef);

    return () => ctx.revert();
  }, [metricValue]);

  return (
    <div ref={containerRef} className="cinematic-hero-wrapper">
      {/* Background FX */}
      <div className="cinematic-bg-grid" />
      <div className="cinematic-glow-orb" />
      <div className="cinematic-hero-stripe" />

      <div className="cinematic-hero-container">
        {/* Brand Badge */}
        <div className="cinematic-brand-badge">
          <span className="cinematic-badge-pulse" />
          <Shield size={14} className="text-white" />
          <span>{brandName}</span>
        </div>

        {/* Primary Scaled Headline */}
        <div className="cinematic-title-group">
          <span className="tagline-solid">{tagline1}</span>
          <span className="text-silver-matte">{tagline2}</span>
        </div>

        {/* Parallax Tilt Card */}
        <div ref={cardRef} className="cinematic-tilt-card">
          <div className="card-header-bar">
            <div className="card-traffic-lights">
              <span className="traffic-dot dot-red" />
              <span className="traffic-dot dot-yellow" />
              <span className="traffic-dot dot-green" />
            </div>
            <div className="card-status-tag">
              <Activity size={13} style={{ color: '#59d499' }} />
              <span>GNN CORE ACTIVE</span>
            </div>
          </div>

          <div className="card-content-grid">
            <div>
              <h2 className="card-heading">{cardHeading}</h2>
              <div className="card-description hidden md:block">
                {cardDescription}
              </div>
            </div>

            <div className="metric-box">
              <span ref={metricNumRef} className="metric-value-num">
                0
              </span>
              <span className="metric-label-text">{metricLabel}</span>
            </div>
          </div>
        </div>

        {/* Closing CTA Scene */}
        <div className="cinematic-cta-scene">
          <h3 className="cta-heading">{ctaHeading}</h3>
          <p className="cta-description">{ctaDescription}</p>

          <div className="cta-actions-group">
            <button className="cinematic-btn-primary" onClick={onPrimaryCtaClick}>
              Explore Dashboard <ArrowRight size={18} />
            </button>
            <button className="cinematic-btn-secondary" onClick={onSecondaryCtaClick}>
              <FileSpreadsheet size={18} /> Upload Dataset
            </button>
          </div>

          {/* Inline Store Badges */}
          <div className="store-badges-group">
            <button className="store-badge-btn" title="Download iOS App">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.32c.67-.82 1.13-1.96.99-3.12-1 .04-2.22.67-2.93 1.49-.64.74-1.19 1.91-1.04 3.05 1.12.09 2.26-.58 2.98-1.42z"/>
              </svg>
              <span>App Store</span>
            </button>
            <button className="store-badge-btn" title="Download Android App">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3.609 1.814L13.792 12 3.61 22.186a2.373 2.373 0 0 1-.61-1.614V3.428c0-.624.23-1.196.609-1.614zM15.207 13.414l2.657 2.657-11.758 6.777 9.101-9.434zM15.207 10.586L6.106 1.152l11.758 6.777-2.657 2.657zM16.621 12l2.91-2.91c.483-.483.769-1.15.769-1.89 0-.74-.286-1.407-.769-1.89l-2.07-2.07L21 6.55c.78.78.78 2.05 0 2.83L16.621 12z"/>
              </svg>
              <span>Google Play</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CinematicHero;
