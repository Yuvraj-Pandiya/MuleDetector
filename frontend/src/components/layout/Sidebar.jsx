import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ShieldAlert, Sun, Moon } from 'lucide-react';
import GooeyNav from '../ui/GooeyNav';
import './Sidebar.css';

const navItems = [
  { label: 'Home', href: '/' },
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Upload', href: '/upload' },
  { label: 'Accounts', href: '/accounts' },
  { label: 'Anomaly', href: '/anomaly' },
  { label: 'Features', href: '/features' },
  { label: 'Explainability', href: '/explain' },
  { label: 'Graph', href: '/graph' },
  { label: 'Alerts', href: '/alerts' },
  { label: 'Metrics', href: '/metrics' },
  { label: 'Monitoring', href: '/monitoring' },
  { label: 'Simulation', href: '/simulation' },
];

export default function Sidebar({ theme = 'dark', onToggleTheme }) {
  const navigate = useNavigate();
  const location = useLocation();

  const activeIndex = Math.max(
    0,
    navItems.findIndex((item) => item.href === location.pathname)
  );

  return (
    <header className="gooey-header-bar">
      <div
        className="header-brand"
        onClick={() => navigate('/')}
        role="button"
        tabIndex={0}
        title="MuleScope Home"
      >
        <ShieldAlert className="brand-icon" size={20} />
        <span className="brand-name">
          MULE<span className="brand-sub">SCOPE</span>
        </span>
      </div>

      <div className="header-nav-center">
        <GooeyNav
          items={navItems}
          initialActiveIndex={activeIndex}
          onItemClick={(item) => navigate(item.href)}
          animationTime={600}
          particleCount={15}
          particleDistances={[90, 10]}
          particleR={100}
          timeVariance={300}
          colors={[1, 2, 3, 1, 2, 3, 1, 4]}
        />
      </div>

      <div className="header-actions">
        <div className="system-status" title="Engine Online">
          <span className="status-dot" />
          <span className="status-text">Online</span>
        </div>

        {onToggleTheme && (
          <button
            className="theme-switch-icon-btn"
            onClick={onToggleTheme}
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
            id="sidebar-theme-toggle"
          >
            {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        )}
      </div>
    </header>
  );
}
