import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Header.css';

// Session Controls Component
function SessionControls() {
  const [sessionCode, setSessionCode] = useState('');
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [showSessionList, setShowSessionList] = useState(false);
  const [showCurrentSessions, setShowCurrentSessions] = useState(false);
  const [userSessions, setUserSessions] = useState([]);
  const [currentSessions, setCurrentSessions] = useState([]);
  const [loading, setLoading] = useState(false);
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

  const loadUserSessions = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      let token = localStorage.getItem('token');
      
      if (!token) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          token = userData.sessionToken;
        }
      }

      if (!token) {
        console.error('No authentication token found');
        return;
      }

      const response = await fetch(`${apiUrl}/api/sessions/list`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setUserSessions(data.sessions || []);
      } else {
        console.error('Failed to load sessions:', response.status);
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadCurrentSessions = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      let token = localStorage.getItem('token');
      
      if (!token) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          token = userData.sessionToken;
        }
      }

      if (!token) {
        console.error('No authentication token found');
        return;
      }

      const response = await fetch(`${apiUrl}/api/sessions/current`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentSessions(data.sessions || []);
      } else {
        console.error('Failed to load current sessions:', response.status);
      }
    } catch (error) {
      console.error('Error loading current sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const showSessionListModal = () => {
    setShowSessionList(true);
    loadUserSessions();
  };

  const showCurrentSessionsModal = () => {
    setShowCurrentSessions(true);
    loadCurrentSessions();
  };

  const joinSessionById = (sessionCode) => {
    navigate(`/session/${sessionCode}`);
    setShowSessionList(false);
  };

  const joinCurrentSessionById = (sessionCode) => {
    navigate(`/session/${sessionCode}`);
    setShowCurrentSessions(false);
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
        🔗 Join Session
      </button>
      
      <button 
        className="nav-link session-btn" 
        onClick={showSessionListModal}
        title="View Your Template Sessions"
      >
        📋 My Sessions
      </button>
      
      <button 
        className="nav-link session-btn" 
        onClick={showCurrentSessionsModal}
        title="View Sessions You're Currently In"
      >
        🔄 Current Sessions
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

      {showSessionList && (
        <div className="modal-overlay">
          <div className="modal-content session-list-modal">
            <h3>Your Template Sessions</h3>
            
            {loading ? (
              <div className="loading">Loading sessions...</div>
            ) : userSessions.length === 0 ? (
              <div className="no-sessions">
                <p>No template sessions found.</p>
                <p>Create a new template session to get started!</p>
              </div>
            ) : (
              <div className="sessions-list">
                {userSessions.map((session) => (
                  <div key={session.session_id} className="session-item">
                    <div className="session-info">
                      <h4>{session.title}</h4>
                      <p><strong>Code:</strong> {session.session_code}</p>
                      <p><strong>Subject:</strong> {session.subject}</p>
                      <p><strong>Participants:</strong> {session.participants?.length || 0}</p>
                      <p><strong>Created:</strong> {new Date(session.created_at).toLocaleDateString()}</p>
                      {session.host_username === JSON.parse(localStorage.getItem('user') || '{}').username && (
                        <span className="host-badge">HOST</span>
                      )}
                    </div>
                    <div className="session-actions">
                      <button 
                        className="join-btn"
                        onClick={() => joinSessionById(session.session_code)}
                      >
                        Join
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            <div className="modal-buttons">
              <button onClick={() => setShowSessionList(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {showCurrentSessions && (
        <div className="modal-overlay">
          <div className="modal-content session-list-modal">
            <h3>Current Sessions</h3>
            <p>Sessions you've joined as a participant</p>
            
            {loading ? (
              <div className="loading">Loading current sessions...</div>
            ) : currentSessions.length === 0 ? (
              <div className="no-sessions">
                <p>You're not currently in any sessions.</p>
                <p>Join a session to see it here!</p>
              </div>
            ) : (
              <div className="sessions-list">
                {currentSessions.map((session) => (
                  <div key={session.session_id} className="session-item">
                    <div className="session-info">
                      <h4>{session.title}</h4>
                      <p><strong>Code:</strong> {session.session_code}</p>
                      <p><strong>Subject:</strong> {session.subject}</p>
                      <p><strong>Host:</strong> {session.host_username}</p>
                      <p><strong>Participants:</strong> {session.participants?.length || 0}</p>
                      <p><strong>Status:</strong> {session.is_active ? 'Active' : 'Inactive'}</p>
                      <span className="participant-badge">PARTICIPANT</span>
                    </div>
                    <div className="session-actions">
                      <button 
                        className="join-btn"
                        onClick={() => joinCurrentSessionById(session.session_code)}
                      >
                        Rejoin
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            <div className="modal-buttons">
              <button onClick={() => setShowCurrentSessions(false)}>
                Close
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