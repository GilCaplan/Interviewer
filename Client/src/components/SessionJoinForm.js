import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './SessionJoinForm.css';

const SessionJoinForm = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [joinMode, setJoinMode] = useState('join'); // 'join' or 'create'
  const [sessionCode, setSessionCode] = useState('');
  const [password, setPassword] = useState('');
  const [createForm, setCreateForm] = useState({
    title: '',
    subject: 'general',
    description: '',
    password: '',
    maxParticipants: 10,
    maxQuestions: 15
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleJoinSession = async (e) => {
    e.preventDefault();
    if (!sessionCode.trim()) {
      setError('Please enter a session code');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const token = localStorage.getItem('token') || user?.sessionToken;
      
      if (!token) {
        setError('Please login to join sessions');
        return;
      }

      const requestBody = {};
      if (password.trim()) {
        requestBody.password = password.trim();
      }

      const response = await fetch(`${apiUrl}/api/sessions/join/${sessionCode}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        navigate(`/session/${sessionCode}`);
      } else if (response.status === 401) {
        const errorData = await response.json();
        if (errorData.error?.includes('password')) {
          setError('Incorrect password for this session');
        } else {
          setError('This session requires a password');
        }
      } else if (response.status === 404) {
        setError('Session not found');
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to join session');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async (e) => {
    e.preventDefault();
    if (!createForm.title.trim()) {
      setError('Please enter a session title');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const token = localStorage.getItem('token') || user?.sessionToken;
      
      if (!token) {
        setError('Please login to create sessions');
        return;
      }

      const sessionData = {
        title: createForm.title.trim(),
        subject: createForm.subject,
        description: createForm.description.trim(),
        template_mode: true,
        settings: {
          max_participants: parseInt(createForm.maxParticipants),
          max_questions: parseInt(createForm.maxQuestions),
          allow_llm: true,
          allow_user_questions: true,
          question_numbering: true
        }
      };

      // Add password if provided
      if (createForm.password.trim()) {
        sessionData.password = createForm.password.trim();
      }

      const response = await fetch(`${apiUrl}/api/sessions/create`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(sessionData)
      });

      if (response.ok) {
        const data = await response.json();
        const newSessionCode = data.session.session_code;
        navigate(`/session/${newSessionCode}`);
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to create session');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="session-join-container">
      <div className="session-join-card">
        <h2>Session Management</h2>
        
        {/* Mode Toggle */}
        <div className="mode-toggle">
          <button 
            className={`mode-btn ${joinMode === 'join' ? 'active' : ''}`}
            onClick={() => {
              setJoinMode('join');
              setError('');
            }}
          >
            🔗 Join Session
          </button>
          <button 
            className={`mode-btn ${joinMode === 'create' ? 'active' : ''}`}
            onClick={() => {
              setJoinMode('create');
              setError('');
            }}
          >
            ➕ Create Session
          </button>
        </div>

        {error && <div className="error-message">{error}</div>}

        {joinMode === 'join' ? (
          <form onSubmit={handleJoinSession} className="session-form">
            <div className="form-group">
              <label htmlFor="sessionCode">Session Code</label>
              <input
                type="text"
                id="sessionCode"
                value={sessionCode}
                onChange={(e) => setSessionCode(e.target.value)}
                placeholder="Enter session code..."
                maxLength="20"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="joinPassword">
                Password <span className="optional">(if required)</span>
              </label>
              <div className="password-input-container">
                <span className="password-icon">🔒</span>
                <input
                  type="password"
                  id="joinPassword"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password if required..."
                  maxLength="50"
                />
              </div>
            </div>

            <button type="submit" disabled={loading} className="submit-btn">
              {loading ? 'Joining...' : '🔗 Join Session'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleCreateSession} className="session-form">
            <div className="form-group">
              <label htmlFor="title">Session Title</label>
              <input
                type="text"
                id="title"
                value={createForm.title}
                onChange={(e) => setCreateForm({...createForm, title: e.target.value})}
                placeholder="e.g., Technical Interview Practice"
                maxLength="100"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="subject">Subject</label>
              <select
                id="subject"
                value={createForm.subject}
                onChange={(e) => setCreateForm({...createForm, subject: e.target.value})}
              >
                <option value="general">General</option>
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="algorithms">Algorithms</option>
                <option value="system_design">System Design</option>
                <option value="behavioral">Behavioral</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                value={createForm.description}
                onChange={(e) => setCreateForm({...createForm, description: e.target.value})}
                placeholder="Optional description of the session..."
                maxLength="500"
                rows="3"
              />
            </div>

            <div className="form-group">
              <label htmlFor="createPassword">
                Password <span className="optional">(optional, for privacy)</span>
              </label>
              <div className="password-input-container">
                <span className="password-icon">🔒</span>
                <input
                  type="password"
                  id="createPassword"
                  value={createForm.password}
                  onChange={(e) => setCreateForm({...createForm, password: e.target.value})}
                  placeholder="Leave empty for public session..."
                  maxLength="50"
                />
              </div>
              <small className="password-help">
                Password protects your session from unauthorized access
              </small>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="maxParticipants">Max Participants</label>
                <select
                  id="maxParticipants"
                  value={createForm.maxParticipants}
                  onChange={(e) => setCreateForm({...createForm, maxParticipants: e.target.value})}
                >
                  <option value="5">5</option>
                  <option value="10">10</option>
                  <option value="15">15</option>
                  <option value="20">20</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="maxQuestions">Max Questions</label>
                <select
                  id="maxQuestions"
                  value={createForm.maxQuestions}
                  onChange={(e) => setCreateForm({...createForm, maxQuestions: e.target.value})}
                >
                  <option value="10">10</option>
                  <option value="15">15</option>
                  <option value="25">25</option>
                  <option value="50">50</option>
                </select>
              </div>
            </div>

            <button type="submit" disabled={loading} className="submit-btn">
              {loading ? 'Creating...' : '➕ Create Session'}
            </button>
          </form>
        )}

        <div className="back-link">
          <button onClick={() => navigate('/')} className="back-btn">
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
};

export default SessionJoinForm;