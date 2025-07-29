import React, { useState } from 'react';
import './ParticipantsList.css';

const ParticipantsList = ({ session, participants, user, isHost }) => {
  const [sessionSettings, setSessionSettings] = useState({
    viewing_mode: session.settings?.viewing_mode || 'edit',
    allow_llm: session.settings?.allow_llm || true,
    allow_user_questions: session.settings?.allow_user_questions || true,
    max_participants: session.settings?.max_participants || 10
  });

  const viewingModeOptions = [
    { value: 'edit', label: 'Full Edit Access', description: 'All users can edit questions' },
    { value: 'suggestions_only', label: 'Suggestions Only', description: 'Users can only suggest, host edits' },
    { value: 'view_only', label: 'View Only', description: 'Users can only view, no editing' }
  ];

  const handleSettingsUpdate = async (newSettings) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/settings`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${user.sessionToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newSettings),
        credentials: 'include'
      });

      if (response.ok) {
        setSessionSettings({ ...sessionSettings, ...newSettings });
      } else {
        throw new Error('Failed to update settings');
      }
    } catch (err) {
      console.error('Error updating settings:', err);
      alert('Failed to update session settings: ' + err.message);
    }
  };

  const getActivityStatus = (participant) => {
    // This would be based on real-time data in a full implementation
    return 'online'; // Mock status
  };

  const getParticipantRole = (participant) => {
    if (participant.is_host) return 'Host';
    if (participant.is_guest) return 'Guest';
    return 'Member';
  };

  const getParticipantContributions = (participant) => {
    // In a real implementation, this would track actual contributions
    return {
      questions_started: Math.floor(Math.random() * 5),
      suggestions_made: Math.floor(Math.random() * 10),
      messages_sent: Math.floor(Math.random() * 20)
    };
  };

  const copySessionCode = () => {
    navigator.clipboard.writeText(session.session_code);
    alert('Session code copied to clipboard!');
  };

  const copySessionLink = () => {
    const link = `${window.location.origin}/session/${session.session_code}`;
    navigator.clipboard.writeText(link);
    alert('Session link copied to clipboard!');
  };

  return (
    <div className="participants-list">
      <div className="participants-header">
        <h2>Session Participants</h2>
        <div className="session-info">
          <div className="session-details">
            <p><strong>Session:</strong> {session.title}</p>
            <p><strong>Subject:</strong> {session.subject}</p>
            <p><strong>Code:</strong> 
              <span className="session-code" onClick={copySessionCode}>
                {session.session_code} 📋
              </span>
            </p>
          </div>
          <div className="session-actions">
            <button onClick={copySessionLink} className="share-btn">
              Share Session Link
            </button>
          </div>
        </div>
      </div>

      {/* Session Settings (Host Only) */}
      {isHost && (
        <div className="session-settings">
          <h3>🔧 Session Settings</h3>
          <div className="settings-grid">
            <div className="setting-group">
              <label>Viewing Mode:</label>
              <select
                value={sessionSettings.viewing_mode}
                onChange={(e) => handleSettingsUpdate({ viewing_mode: e.target.value })}
              >
                {viewingModeOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <small>{viewingModeOptions.find(o => o.value === sessionSettings.viewing_mode)?.description}</small>
            </div>

            <div className="setting-group">
              <label>
                <input
                  type="checkbox"
                  checked={sessionSettings.allow_llm}
                  onChange={(e) => handleSettingsUpdate({ allow_llm: e.target.checked })}
                />
                Allow LLM Assistance
              </label>
              <small>Enable AI suggestions and chat</small>
            </div>

            <div className="setting-group">
              <label>
                <input
                  type="checkbox"
                  checked={sessionSettings.allow_user_questions}
                  onChange={(e) => handleSettingsUpdate({ allow_user_questions: e.target.checked })}
                />
                Allow User Questions
              </label>
              <small>Let participants add their own questions</small>
            </div>

            <div className="setting-group">
              <label>Max Participants:</label>
              <input
                type="number"
                value={sessionSettings.max_participants}
                onChange={(e) => handleSettingsUpdate({ max_participants: parseInt(e.target.value) })}
                min="2"
                max="50"
              />
            </div>
          </div>
        </div>
      )}

      {/* Participants List */}
      <div className="participants-section">
        <h3>👥 Participants ({participants.length})</h3>
        
        {participants.length === 0 ? (
          <div className="no-participants">
            <p>No participants yet. Share the session code to invite others!</p>
          </div>
        ) : (
          <div className="participants-grid">
            {participants.map((participant) => {
              const contributions = getParticipantContributions(participant);
              const isCurrentUser = participant.username === user.username;
              
              return (
                <div 
                  key={participant.username} 
                  className={`participant-card ${isCurrentUser ? 'current-user' : ''}`}
                >
                  <div className="participant-header">
                    <div className="participant-info">
                      <h4>{participant.username}</h4>
                      <div className="participant-badges">
                        <span className={`role-badge ${participant.is_host ? 'host' : 'member'}`}>
                          {getParticipantRole(participant)}
                        </span>
                        <span className={`status-badge ${getActivityStatus(participant)}`}>
                          {getActivityStatus(participant)}
                        </span>
                        {isCurrentUser && <span className="current-user-badge">You</span>}
                      </div>
                    </div>
                    
                    <div className="participant-avatar">
                      {participant.username.charAt(0).toUpperCase()}
                    </div>
                  </div>

                  <div className="participant-stats">
                    <div className="stat">
                      <span className="stat-value">{contributions.questions_started}</span>
                      <span className="stat-label">Questions Started</span>
                    </div>
                    <div className="stat">
                      <span className="stat-value">{contributions.suggestions_made}</span>
                      <span className="stat-label">Suggestions</span>
                    </div>
                    <div className="stat">
                      <span className="stat-value">{contributions.messages_sent}</span>
                      <span className="stat-label">Messages</span>
                    </div>
                  </div>

                  <div className="participant-details">
                    <p><strong>Joined:</strong> {new Date(participant.created_at).toLocaleDateString()}</p>
                    {participant.is_guest && <p>🎭 Guest User</p>}
                  </div>

                  {/* Host Actions */}
                  {isHost && !participant.is_host && (
                    <div className="participant-actions">
                      <button className="action-btn warning">
                        Remove from Session
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Session Stats */}
      <div className="session-stats">
        <h3>📊 Session Statistics</h3>
        <div className="stats-grid">
          <div className="stat-card">
            <h4>Questions</h4>
            <div className="stat-details">
              <p>Total: {session.template_data?.questions_queue?.length || 0}</p>
              <p>Finalized: {session.template_data?.ready_questions?.length || 0}</p>
            </div>
          </div>
          
          <div className="stat-card">
            <h4>Participants</h4>
            <div className="stat-details">
              <p>Current: {participants.length}</p>
              <p>Max: {sessionSettings.max_participants}</p>
            </div>
          </div>
          
          <div className="stat-card">
            <h4>Session Time</h4>
            <div className="stat-details">
              <p>Started: {new Date(session.created_at).toLocaleTimeString()}</p>
              <p>Duration: {Math.floor((new Date() - new Date(session.created_at)) / (1000 * 60))} min</p>
            </div>
          </div>
          
          <div className="stat-card">
            <h4>Settings</h4>
            <div className="stat-details">
              <p>Mode: {sessionSettings.viewing_mode}</p>
              <p>LLM: {sessionSettings.allow_llm ? 'Enabled' : 'Disabled'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Help Section */}
      <div className="help-section">
        <h3>ℹ️ How to Use</h3>
        <div className="help-content">
          <div className="help-item">
            <h4>For Participants:</h4>
            <ul>
              <li>Switch between Template, LLM Chat, and Users screens using the top navigation</li>
              <li>Collaborate on questions in real-time based on the current viewing mode</li>
              <li>Use the LLM chat for AI assistance and suggestions</li>
              <li>View other participants and session statistics here</li>
            </ul>
          </div>
          
          {isHost && (
            <div className="help-item">
              <h4>As Host, you can:</h4>
              <ul>
                <li>Start new questions and finalize completed ones</li>
                <li>Adjust session settings to control participant access</li>
                <li>Convert finalized questions into a reusable template</li>
                <li>Manage participants and remove users if needed</li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ParticipantsList;