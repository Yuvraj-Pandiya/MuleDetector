import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ShieldAlert, Sun, Moon, LogIn, UserPlus, LogOut } from 'lucide-react';
import GooeyNav from '../ui/GooeyNav';
import AuthModal from '../ui/AuthModal';
import { useAuth } from '../../context/AuthContext';
import '../ui/AuthModal.css';
import './Sidebar.css';

const navItems = [
  { label: 'Home', href: '/' },
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Upload', href: '/upload' },
  { label: 'Accounts', href: '/accounts' },
  { label: 'Explainability', href: '/explain' },
  { label: 'Graph', href: '/graph' },
  { label: 'Alerts', href: '/alerts' },
  { label: 'Metrics', href: '/metrics' },
  { label: 'Simulation', href: '/simulation' },
];

export default function Sidebar({ theme = 'dark', onToggleTheme }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');

  const activeIndex = Math.max(
    0,
    navItems.findIndex((item) => item.href === location.pathname)
  );

  const openLogin = () => {
    setAuthModalMode('login');
    setAuthModalOpen(true);
  };

  const openSignup = () => {
    setAuthModalMode('signup');
    setAuthModalOpen(true);
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <>
      <header className="gooey-header-bar">
        <div className="header-brand" onClick={() => navigate('/')} role="button" tabIndex={0} title="MuleScope Home">
          <ShieldAlert className="brand-icon" size={20} />
          <span className="brand-name">
            MULE<span className="brand-sub">SCOPE</span>
          </span>
        </div>

        {/* Navigation — only show when logged in */}
        <div className="header-nav-center">
          {isAuthenticated && (
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
          )}
        </div>

        <div className="header-actions">
          {isAuthenticated ? (
            <>
              {/* Status + Theme + User Info + Logout */}
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

              <div className="auth-user-menu">
                <div className="auth-user-pill">
                  <div className="auth-user-avatar">
                    {user.name?.charAt(0).toUpperCase()}
                  </div>
                  <span className="auth-user-name">{user.name}</span>
                </div>
                <button className="auth-logout-btn" onClick={handleLogout} title="Sign Out">
                  <LogOut size={13} />
                  Logout
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Login / Signup buttons */}
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

              <div className="auth-header-actions">
                <button className="auth-login-btn" onClick={openLogin}>
                  <LogIn size={14} />
                  Log In
                </button>
                <button className="auth-signup-btn" onClick={openSignup}>
                  <UserPlus size={14} />
                  Sign Up
                </button>
              </div>
            </>
          )}
        </div>
      </header>

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
      />
    </>
  );
}
