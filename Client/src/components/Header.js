import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Header.css';

// Session Controls Component
function SessionControls() {
  const [sessionCode, setSessionCode] = useState('');
  const [showJoinModal, setShowJoinModal] = useState(false);
  const navigate = useNavigate();

  const createNewSession = () => {
    // Generate a random session code for template building
    const newSessionCode = Math.random().toString(36).substring(2, 8).toUpperCase();
    navigate(`/session/${newSessionCode}`);
  };

  const joinSession = () => {
    if (sessionCode.trim()) {
      navigate(`/session/${sessionCode.trim().toUpperCase()}`);
      setShowJoinModal(false);
      setSessionCode('');
    }
  };

  return (
    <div className="session-controls">
      <button 
        className="nav-link session-btn" 
        onClick={createNewSession}
        title="Create New Collaborative Template Building Session"
      >
        ➕ New Template Session
      </button>
      
      <button 
        className="nav-link session-btn" 
        onClick={() => setShowJoinModal(true)}
        title="Join Existing Template Building Session"
      >
        🔗 Join Template Session
      </button>

      {showJoinModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Join Template Building Session</h3>
            <input
              type="text"
              placeholder="Enter template session code..."
              value={sessionCode}
              onChange={(e) => setSessionCode(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && joinSession()}
              autoFocus
            />
            <div className="modal-buttons">
              <button onClick={joinSession} disabled={!sessionCode.trim()}>
                Join
              </button>
              <button onClick={() => {
                setShowJoinModal(false);
                setSessionCode('');
              }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

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
            <SessionControls />
            {/* Add more navigation links as needed */}
        </nav>
      )}
    </header>
  );
}

export default Header;