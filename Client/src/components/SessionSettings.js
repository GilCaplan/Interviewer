import React, { useState, useEffect } from 'react';
import { getApiUrl } from '../utils/authUtils';
import './SessionSettings.css';

const SessionSettings = ({ session, isHost, user, onClose, onSettingsUpdate }) => {
  const [settings, setSettings] = useState({
    viewing_mode: 'suggestions_only',
    max_participants: 10
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (session && session.settings) {
      setSettings({
        viewing_mode: session.settings.viewing_mode || 'suggestions_only',
        max_participants: session.settings.max_participants || 10
      });
    }
  }, [session]);

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSave = async () => {
    if (!isHost) {
      setError('Only the host can update session settings');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const apiUrl = getApiUrl()
      
      // Get token with fallback
      let authToken = localStorage.getItem('token');
      if (!authToken && user?.sessionToken) {
        authToken = user.sessionToken;
      }

      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/settings`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update settings');
      }

      // Notify parent component about settings update
      if (onSettingsUpdate) {
        onSettingsUpdate(settings);
      }

      // Close modal
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isHost) {
    return (
      <div className="session-settings-modal">
        <div className="session-settings-content">
          <div className="session-settings-header">
            <h2>Session Settings</h2>
            <button className="close-button" onClick={onClose}>×</button>
          </div>
          
          <div className="session-settings-body">
            <p className="access-denied">Only the session host can view and modify settings.</p>
            
            <div className="current-settings">
              <h3>Current Settings</h3>
              <div className="setting-display">
                <span className="setting-label">Viewing Mode:</span>
                <span className="setting-value">
                  {session?.settings?.viewing_mode === 'view_only' && '👁️ View Only'}
                  {(session?.settings?.viewing_mode === 'suggestions_only' || !session?.settings?.viewing_mode) && '💡 Allow Suggestions'}
                </span>
              </div>
              <div className="setting-display">
                <span className="setting-label">Max Participants:</span>
                <span className="setting-value">
                  {session?.settings?.max_participants || 10} users
                </span>
              </div>
            </div>
          </div>

          <div className="session-settings-footer">
            <button onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="session-settings-modal">
      <div className="session-settings-content">
        <div className="session-settings-header">
          <h2>Session Settings</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        
        {error && <div className="error-message">{error}</div>}
        
        <div className="session-settings-body">
          {/* Viewing Mode Setting */}
          <div className="setting-group">
            <label className="setting-label">
              <span className="label-text">Viewing Mode</span>
              <span className="label-description">
                Controls what non-host participants can do
              </span>
            </label>
            <div className="viewing-mode-options">
              <label className="radio-option">
                <input
                  type="radio"
                  name="viewing_mode"
                  value="suggestions_only"
                  checked={settings.viewing_mode === 'suggestions_only'}
                  onChange={(e) => handleSettingChange('viewing_mode', e.target.value)}
                />
                <div className="radio-content">
                  <div className="radio-title">💡 Allow Suggestions</div>
                  <div className="radio-description">
                    Other users can suggest changes that you can approve/reject
                  </div>
                </div>
              </label>
              
              <label className="radio-option">
                <input
                  type="radio"
                  name="viewing_mode"
                  value="view_only"
                  checked={settings.viewing_mode === 'view_only'}
                  onChange={(e) => handleSettingChange('viewing_mode', e.target.value)}
                />
                <div className="radio-content">
                  <div className="radio-title">👁️ View Only</div>
                  <div className="radio-description">
                    Other users can only view questions, no changes allowed
                  </div>
                </div>
              </label>
            </div>
          </div>


          {/* Max Participants */}
          <div className="setting-group">
            <label className="setting-label">
              <span className="label-text">Maximum Participants</span>
            </label>
            <div className="number-input-group">
              <input
                type="number"
                min="1"
                max="50"
                value={settings.max_participants}
                onChange={(e) => handleSettingChange('max_participants', parseInt(e.target.value) || 1)}
                className="number-input"
              />
              <span className="input-suffix">people</span>
            </div>
          </div>
        </div>

        <div className="session-settings-footer">
          <button onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button 
            onClick={handleSave} 
            className="save-button"
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SessionSettings;