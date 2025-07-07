import React from 'react';
import { Link } from 'react-router-dom';
import './Header.css';

function Header({ title, subtitle, username, onLogout, isAuthenticated }) {
  return (
    <header className="app-header">
      <div className="header-content">
        <div className="header-title">
          <h1>{title}</h1>
          <p className="subtitle">{subtitle}</p>
        </div>

        {isAuthenticated && (
          <div className="user-controls">
            <div className="user-info">
              <span className="username">{username || 'User'}</span>
              <button
                className="logout-button"
                onClick={onLogout}
                aria-label="Logout"
              >
                Logout
              </button>
            </div>
          </div>
        )}
      </div>

      {isAuthenticated && (
        <nav className="main-nav">
            <Link to="/" className="nav-link">Home</Link>
            <Link to="/templates" className="nav-link">Templates</Link>
            {/* Add more navigation links as needed */}
        </nav>
      )}
    </header>
  );
}

export default Header;