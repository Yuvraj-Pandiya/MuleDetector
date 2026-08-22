import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Navbar from './Navbar';
import './Layout.css';

const PAGE_TITLES = {
  '/': 'Risk Intelligence Platform',
  '/dashboard': 'Dashboard Overview',
  '/upload': 'Upload & Analyze Dataset',
  '/accounts': 'Risk-Ranked Accounts',
  '/explain': 'XAI Explainability Engine',
  '/graph': 'Transaction Graph Topology',
  '/alerts': 'Alerts & Case Management',
  '/metrics': 'Model Performance Report',
  '/simulation': 'Live Simulation Mode',
};

export default function Layout() {
  const [theme, setTheme] = useState(() => localStorage.getItem('sage-theme') || 'dark');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const location = useLocation();

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('sage-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const currentTitle = PAGE_TITLES[location.pathname] || 'Risk Intelligence';
  const isHeroPage = location.pathname === '/';

  return (
    <div className="sage-layout">
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
      <div className="sage-main">
        {!isHeroPage && (
          <Navbar
            title={currentTitle}
            theme={theme}
            onToggleTheme={toggleTheme}
          />
        )}
        <main className={`sage-content ${isHeroPage ? 'hero-mode' : ''}`}>
          <Outlet context={{ theme, toggleTheme }} />
        </main>
      </div>
    </div>
  );
}

