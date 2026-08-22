import React from 'react';
import { Search, Bell, Shield, Sun, Moon } from 'lucide-react';
import './Navbar.css';

export default function Navbar({ title = 'SAGE Intelligence', theme = 'dark', onToggleTheme }) {
  return (
    <header className="sage-navbar">
      <div className="navbar-left">
        <h1 className="page-title">{title}</h1>
      </div>

      <div className="navbar-right">
        <div className="nav-search">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            placeholder="Search accounts, alerts, IDs..."
            className="search-input"
            id="global-search"
          />
          <kbd className="search-kbd">⌘K</kbd>
        </div>

        <button
          className="nav-icon-btn theme-toggle-btn"
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          onClick={onToggleTheme}
          id="theme-toggle-btn"
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        <button className="nav-icon-btn" title="Notifications" id="nav-notifications">
          <Bell size={17} />
          <span className="notif-dot" />
        </button>

        <div className="nav-user">
          <div className="user-avatar">
            <Shield size={14} />
          </div>
          <span className="user-label">Analyst</span>
        </div>
      </div>
    </header>
  );
}
