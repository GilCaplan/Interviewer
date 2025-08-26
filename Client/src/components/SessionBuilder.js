import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import io from 'socket.io-client';
import { getApiUrl, getAuthToken } from '../utils/authUtils';
import { fetchApi } from '../utils/api'; // Import the new utility
import './SessionBuilder.css';

// Sub-components for the 3 screens
import TemplateEditor from './TemplateEditor';
import LLMChat from './LLMChat';
import ParticipantsList from './ParticipantsList';
import SessionSettings from './SessionSettings';

const SessionBuilder = () => {
  const { sessionCode } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  // Main state
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [socket, setSocket] = useState(null);
  
  // UI state
  const [activeScreen, setActiveScreen] = useState('template'); // 'template', 'llm', 'participants'
  const [isHost, setIsHost] = useState(false);
  const [showPasswordPrompt, setShowPasswordPrompt] = useState(false);
  const [passwordInput, setPasswordInput] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionStatus, setConversionStatus] = useState('');
  
  // Screen data
  const [questions, setQuestions] = useState([]);
  const [participants, setParticipants] = useState([]);
  const [templateMetadata, setTemplateMetadata] = useState({
    template_name: '',
    description: '',
    subject: 'general',
    difficulty: 'medium'
  });
  const [onlineUsers, setOnlineUsers] = useState(new Set()); // Track online status
  const [chatMessages, setChatMessages] = useState([]);

  // Use ref to track if component is mounted
  const isMountedRef = useRef(true);
  
  // Initialize session and socket
  useEffect(() => {
    isMountedRef.current = true;
    
    const initializeSession = async () => {
      try {
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
        
        // Get token from localStorage with better error handling
        let token = localStorage.getItem('token');
        
        // If no direct token, try to get from user object
        if (!token) {
          const storedUser = localStorage.getItem('user');
          if (storedUser) {
            try {
              const userData = JSON.parse(storedUser);
              token = userData.sessionToken;
            } catch (e) {
              console.error('Failed to parse stored user data:', e);
            }
          }
        }
        
        console.log('Token check:', {
          directToken: !!localStorage.getItem('token'),
          userObject: !!localStorage.getItem('user'),
          userFromContext: !!user,
          finalToken: !!token
        });
        
        if (!token) {
          setError('Please login to access sessions');
          setLoading(false);
          navigate('/login');
          return;
        }

        // First try to join existing session
        let response = await fetch(`${apiUrl}/api/sessions/join/${sessionCode}`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({})
        });

        // If joining failed due to password requirement, show password prompt
        if (response.status === 401) {
          const errorData = await response.json();
          if (errorData.error?.includes('password')) {
            setShowPasswordPrompt(true);
            setLoading(false);
            return;
          }
        }

        // If joining failed for other reasons, create new session and redirect to new session code
        if (!response.ok) {
          const createResponse = await fetch(`${apiUrl}/api/sessions/create`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              title: `Collaborative Template Building`,
              subject: 'general',
              description: 'Building interview templates together',
              template_mode: true,
              settings: {
                max_participants: 10,
                max_questions: 15,
                allow_llm: true,
                allow_user_questions: true,
                question_numbering: true
              }
            })
          });

          if (!createResponse.ok) {
            throw new Error('Failed to create new session');
          }

          const createData = await createResponse.json();
          const newSessionCode = createData.session.session_code;
          
          // Redirect to the new session code
          console.log('Created new session, redirecting to:', newSessionCode);
          navigate(`/session/${newSessionCode}`, { replace: true });
          return;
        }

        const data = await response.json();
        const sessionData = data.session;
        setSession(sessionData);
        
        // Populate metadata from session
        setTemplateMetadata({
          template_name: sessionData.title || `Collaborative Template`,
          description: sessionData.description || 'Building interview templates together',
          difficulty: sessionData.difficulty || 'medium',
          subject: sessionData.subject || 'general'
        });
        
        // Get username from multiple sources for reliability
        let username = user?.username;
        if (!username) {
          const storedUser = localStorage.getItem('user');
          if (storedUser) {
            try {
              const userData = JSON.parse(storedUser);
              username = userData.username;
            } catch (e) {
              console.error('Failed to parse user data for host check:', e);
            }
          }
        }
        
        const isHostUser = data.session.host_username === username;
        setIsHost(isHostUser);
        
        console.log('Host check:', {
          sessionHost: data.session.host_username,
          currentUsername: username,
          isHost: isHostUser
        });
        
        // Set up questions from session data
        const templateData = data.session.template_data || {};
        setQuestions([
          ...(templateData.questions_queue || []),
          ...(templateData.ready_questions || [])
        ]);

        // Initialize WebSocket connection with error handling
        if (isMountedRef.current) {
          const socketToken = token || getAuthToken();
          if (socketToken) {
            try {
              const newSocket = io(apiUrl, {
                auth: { token: socketToken },
                transports: ['websocket', 'polling'],
                timeout: 10000,
                reconnection: true,
                reconnectionAttempts: 3
              });
              
              // Set up error handling
              newSocket.on('connect_error', (error) => {
                console.warn('Socket connection error:', error);
              });
              
              newSocket.on('connect', () => {
                console.log('Socket connected successfully');
                newSocket.emit('join_session', data.session.session_id);
              });
              
              // Set up socket event listeners
              setupSocketListeners(newSocket);
              setSocket(newSocket);
            } catch (socketError) {
              console.warn('Failed to initialize socket:', socketError);
            }
          }
          
          // Load participants
          loadParticipants(data.session.session_id);
        }

      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (sessionCode) {
      initializeSession();
    }

    // Cleanup function
    return () => {
      isMountedRef.current = false;
      
      // Clear pending participant loads
      if (loadParticipantsTimeoutRef.current) {
        clearTimeout(loadParticipantsTimeoutRef.current);
      }
      
      if (socket) {
        console.log('Cleaning up socket connection');
        // Tell the server we are leaving the room for proper cleanup
        if (session?.session_id) {
          socket.emit('leave_session', session.session_id);
        }
        socket.off(); // Remove all listeners
        socket.disconnect();
        setSocket(null);
      }
    };
  }, [sessionCode, navigate]);
  
  // Additional cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const setupSocketListeners = (socket) => {
    // This single, unified handler is the ONLY source of truth for session and question state.
    // It replaces all previous, specific handlers like 'question_finalized', 'field_suggestion_added', etc.
    // This prevents race conditions and ensures the client UI always matches the server state.
    socket.on('session_updated', (updatedSession) => {
      console.log('WebSocket: Received full session update', updatedSession);
      if (isMountedRef.current && updatedSession) {
        // Update the main session state object
        setSession(updatedSession);

        // Also update the metadata state to reflect changes
        setTemplateMetadata({
          template_name: updatedSession.title || '',
          description: updatedSession.description || '',
          difficulty: updatedSession.difficulty || 'medium',
          subject: updatedSession.subject || ''
        });

        // Update the derived questions state from the new, authoritative session data
        const templateData = updatedSession.template_data || {};
        const allQuestions = [
          ...(templateData.questions_queue || []),
          ...(templateData.ready_questions || [])
        ];
        setQuestions(allQuestions);

        // The `participants` and `chatMessages` are handled by separate API calls/events
        // to keep this main update focused and efficient.
      }
    });

    // Listen for the correct WebSocket events from backend
    socket.on('user_joined_room', (data) => {
      console.log('WebSocket: User joined room', data);
      // For now, just reload participants to avoid duplicates
      if (session?.session_id) {
        loadParticipants(session.session_id);
      }
    });

    socket.on('user_left_room', (data) => {
      console.log('WebSocket: User left room', data);
      setParticipants(prev => prev.filter(p => p.username !== data.username));
      
      // Mark user as offline
      setOnlineUsers(prev => {
        const newSet = new Set(prev);
        newSet.delete(data.username);
        return newSet;
      });
    });

    socket.on('session_settings_updated', (data) => {
      console.log('WebSocket: Session settings updated', data);
      // Update session settings in state
      setSession(prev => ({
        ...prev,
        settings: {
          ...prev.settings,
          ...data.settings
        }
      }));
    });
  };

  // Add debounce ref to prevent multiple rapid calls
  const loadParticipantsTimeoutRef = useRef(null);

  const loadParticipants = async (sessionId) => {
    // Clear any pending load
    if (loadParticipantsTimeoutRef.current) {
      clearTimeout(loadParticipantsTimeoutRef.current);
    }

    // Debounce the load to prevent multiple rapid calls
    loadParticipantsTimeoutRef.current = setTimeout(async () => {
      try {
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
        
        // Get token with fallback
        let authToken = localStorage.getItem('token');
        if (!authToken && user?.sessionToken) {
          authToken = user.sessionToken;
        }
        
        const response = await fetch(`${apiUrl}/api/sessions/${sessionId}/participants`, {
          headers: {
            'Authorization': `Bearer ${authToken}`
          },
          credentials: 'include'
        });

        if (response.ok) {
          const data = await response.json();
          
          // Deduplicate participants by username to prevent duplicates
          const uniqueParticipants = data.participants.filter((participant, index, self) => 
            index === self.findIndex(p => p.username === participant.username)
          );
          
          setParticipants(uniqueParticipants);
          
          // Initialize all current participants as online
          const usernames = uniqueParticipants.map(p => p.username);
          setOnlineUsers(new Set(usernames));
        }
      } catch (err) {
        console.error('Failed to load participants:', err);
      }
    }, 100); // 100ms debounce
  };

  // Handler functions
  const handleStartQuestion = async (questionNumber, questionType) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      
      // Get token with fallback
      let authToken = localStorage.getItem('token');
      if (!authToken && user?.sessionToken) {
        authToken = user.sessionToken;
      }
      
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/${questionNumber}/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ type: questionType }),
        credentials: 'include'
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
          const errorData = await response.text();
          console.error('Start question failed:', response.status, errorData);
          
          if (errorData) {
            try {
              const errorJson = JSON.parse(errorData);
              errorMessage = errorJson.error || errorData;
            } catch (parseError) {
              errorMessage = errorData;
            }
          }
        } catch (readError) {
          console.error('Could not read error response:', readError);
        }
        
        throw new Error(errorMessage);
      }
      
      console.log('Question start successful');
      // The UI will be updated via the 'session_updated' WebSocket event.
    } catch (err) {
      console.error('Error starting question:', err);
    }
  };

  const handleMetadataChange = (e) => {
    const { name, value } = e.target;
    setTemplateMetadata(prev => ({ ...prev, [name]: value }));
  };

  const saveMetadata = () => {
    if (socket && isHost) {
      // Emit an event to the backend to update the session's metadata
      socket.emit('update_session_metadata', {
        session_id: session.session_id,
        // Send all metadata fields to be updated on the session document
        metadata: templateMetadata
      });
    }
  };

  const handleUpdateQuestion = async (questionId, field, value) => {
    console.log('handleUpdateQuestion called:', { questionId, field, value, sessionId: session?.session_id });
    try {
      await fetchApi(`/api/sessions/${session.session_id}/questions/${questionId}/update`, {
        method: 'PUT',
        body: JSON.stringify({ field, value }),
      });
      console.log('Question update successful');
    } catch (err) {
      console.error('Error updating question:', err);
    }
  };

  const handleFinalizeQuestion = async (questionId) => {
    console.log('Attempting to finalize question:', {
      questionId,
      sessionId: session?.session_id,
      availableQuestions: questions.map(q => ({ id: q.question_id, number: q.question_number, status: q.status }))
    });
    
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      
      // Get token with fallback
      let authToken = localStorage.getItem('token');
      if (!authToken && user?.sessionToken) {
        authToken = user.sessionToken;
      }
      
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/${questionId}/finalize`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({}),
        credentials: 'include'
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
          const errorData = await response.text();
          console.error('Finalize question failed:', response.status, errorData);
          
          if (errorData) {
            try {
              const errorJson = JSON.parse(errorData);
              errorMessage = errorJson.error || errorData;
            } catch (parseError) {
              errorMessage = errorData;
            }
          }
        } catch (readError) {
          console.error('Could not read error response:', readError);
        }
        
        throw new Error(errorMessage);
      }
      
      console.log('Question finalized successfully');
    } catch (err) {
      console.error('Error finalizing question:', err);
    }
  };

  const handleConvertToTemplate = async () => {
    if (!window.confirm('This will create a permanent, reusable template from the current session. This action cannot be undone. Continue?')) {
      return;
    }

    setIsConverting(true);
    setConversionStatus('Converting to template...');

    try {
      const response = await fetchApi(`/api/sessions/${session.session_id}/convert-to-template`, {
        method: 'POST',
        // The backend will use the session title as the template name by default.
        body: JSON.stringify({ template_name: session.title || 'Converted Template' })
      });
      
      setConversionStatus('Template created successfully! You will be redirected shortly.');
      
      setTimeout(() => {
        navigate(`/template/${response.template.template_id}`);
      }, 2500);
    } catch (err) {
      setConversionStatus(`Error: ${err.message}`);
      setIsConverting(false);
    }
  };

  const handleLLMRequest = async (questionId, field, context, numResponses = 1) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      
      // Get token with fallback
      let authToken = localStorage.getItem('token');
      if (!authToken && user?.sessionToken) {
        authToken = user.sessionToken;
      }
      
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/${questionId}/llm-suggest`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ field, context, num_responses: numResponses }),
        credentials: 'include'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get LLM suggestion');
      }
      
      const data = await response.json();
      console.log('LLM suggestion response:', data);
    } catch (err) {
      console.error('Error requesting LLM suggestion:', err);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    if (!passwordInput.trim()) {
      setError('Please enter a password');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const token = localStorage.getItem('token') || user?.sessionToken;

      const response = await fetch(`${apiUrl}/api/sessions/join/${sessionCode}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ password: passwordInput.trim() })
      });

      if (response.ok) {
        // Password correct, continue with session setup
        const data = await response.json();
        setSession(data.session);
        
        const username = user?.username || JSON.parse(localStorage.getItem('user') || '{}').username;
        const isHostUser = data.session.host_username === username;
        setIsHost(isHostUser);
        
        const templateData = data.session.template_data || {};
        setQuestions([
          ...(templateData.questions_queue || []),
          ...(templateData.ready_questions || [])
        ]);

        // Initialize WebSocket
        const socketToken = token || user?.sessionToken;
        const newSocket = io(apiUrl, {
          auth: { token: socketToken }
        });
        newSocket.emit('join_session', data.session.session_id);
        setupSocketListeners(newSocket);
        setSocket(newSocket);

        loadParticipants(data.session.session_id);
        setShowPasswordPrompt(false);
        setPasswordInput('');
      } else if (response.status === 401) {
        setError('Incorrect password');
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

  const cleanupAllUserSessions = async () => {
    if (!window.confirm('This will delete ALL your sessions permanently. Are you sure you want to proceed?')) {
      return;
    }

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      
      // Get token with fallback
      let authToken = localStorage.getItem('token');
      if (!authToken && user?.sessionToken) {
        authToken = user.sessionToken;
      }
      
      const response = await fetch(`${apiUrl}/api/sessions/cleanup-user`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        console.log(`Successfully cleaned up ${data.deleted_sessions} sessions.`);
        navigate('/');
      } else {
        const errorData = await response.text();
        console.error('Failed to cleanup sessions: ' + errorData);
      }
    } catch (err) {
      console.error('Error cleaning up sessions:', err);
    }
  };

  const deleteCurrentSession = async () => {
    if (!window.confirm('This will permanently delete this session and all its data. Are you sure?')) {
      return;
    }

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      
      // Get token with fallback
      let authToken = localStorage.getItem('token');
      if (!authToken && user?.sessionToken) {
        authToken = user.sessionToken;
      }
      
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (response.ok) {
        console.log('Session deleted successfully.');
        navigate('/');
      } else {
        const errorData = await response.text();
        console.error('Failed to delete session: ' + errorData);
      }
    } catch (err) {
      console.error('Error deleting session:', err);
    }
  };

  const removeUserFromSession = async (username) => {
    if (!window.confirm(`Remove ${username} from this session?`)) {
      return;
    }

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      
      // Get token with fallback
      let authToken = localStorage.getItem('token');
      if (!authToken && user?.sessionToken) {
        authToken = user.sessionToken;
      }
      
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/remove-user`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username })
      });

      if (response.ok) {
        // Remove from local state immediately
        setParticipants(prev => prev.filter(p => p.username !== username));
        setOnlineUsers(prev => {
          const newSet = new Set(prev);
          newSet.delete(username);
          return newSet;
        });
        
        console.log(`${username} has been removed from the session.`);
      } else {
        const errorData = await response.json();
        console.error('Failed to remove user: ' + (errorData.error || 'Unknown error'));
      }
    } catch (err) {
      console.error('Error removing user from session:', err);
    }
  };

  if (loading) {
    return <div className="session-loading">Loading session...</div>;
  }

  if (showPasswordPrompt) {
    return (
      <div className="session-password-prompt">
        <div className="password-prompt-container">
          <h2>🔒 Password Required</h2>
          <p>This session is password-protected. Please enter the password to join.</p>
          
          {error && <div className="error-message">{error}</div>}
          
          <form onSubmit={handlePasswordSubmit} className="password-form">
            <div className="password-input-group">
              <input
                type="password"
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                placeholder="Enter session password..."
                maxLength="50"
                required
                autoFocus
              />
              <button type="submit" disabled={loading}>
                {loading ? 'Joining...' : 'Join Session'}
              </button>
            </div>
          </form>
          
          <div className="password-prompt-actions">
            <button onClick={() => navigate('/sessions')} className="back-button">
              ← Back to Session Management
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="session-error">
        <h2>Error joining session</h2>
        <p>{error}</p>
        <button onClick={() => navigate('/')}>Back to Home</button>
      </div>
    );
  }

  if (!session) {
    return <div className="session-error">Session not found</div>;
  }

  return (
    <div className="session-builder">
      {/* Header */}
      <div className="session-header">
        <div className="session-info">
          {isHost ? (
            <div className="template-metadata-form">
              <input
                type="text"
                name="template_name"
                value={templateMetadata.template_name}
                onChange={handleMetadataChange}
                onBlur={saveMetadata}
                placeholder="Enter Template Name"
                className="metadata-input-title"
              />
              <textarea
                name="description"
                value={templateMetadata.description}
                onChange={handleMetadataChange}
                onBlur={saveMetadata}
                placeholder="Enter a short description..."
                className="metadata-input-description"
                rows={2}
              />
              <div className="metadata-row">
                <div className="metadata-group">
                  <label>Subject:</label>
                  <input type="text" name="subject" value={templateMetadata.subject} onChange={handleMetadataChange} onBlur={saveMetadata} placeholder="e.g., Frontend" />
                </div>
                <div className="metadata-group">
                  <label>Difficulty:</label>
                  <select name="difficulty" value={templateMetadata.difficulty} onChange={handleMetadataChange} onBlur={saveMetadata}>
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
              </div>
            </div>
          ) : (
            <h1>{session.title}</h1>
          )}
          <p>Session Code: <strong className="session-code-strong">{session.session_code}</strong></p>
          <div className="session-badges">
            {isHost && <span className="host-badge">HOST</span>}
            {session.is_password_protected && <span className="password-badge">🔒 Protected</span>}
          </div>
        </div>
        
        {/* Screen Navigation */}
        <div className="screen-navigation">
          <button 
            className={`nav-btn ${activeScreen === 'template' ? 'active' : ''}`}
            onClick={() => setActiveScreen('template')}
          >
            Template ({questions.length})
          </button>
          <button 
            className={`nav-btn ${activeScreen === 'llm' ? 'active' : ''}`}
            onClick={() => setActiveScreen('llm')}
          >
            LLM Chat ({chatMessages.length})
          </button>
          <button 
            className={`nav-btn ${activeScreen === 'participants' ? 'active' : ''}`}
            onClick={() => setActiveScreen('participants')}
          >
            Settings & Users ({participants.length})
          </button>
        </div>

        <div className="session-actions">
          <button onClick={() => navigate('/')}>← Leave Session</button>
        </div>
      </div>

      {/* Screen Content */}
      <div className="screen-content">
        {activeScreen === 'template' && (
          <TemplateEditor
            session={session}
            questions={questions}
            isHost={isHost}
            user={user}
            onStartQuestion={handleStartQuestion}
            onUpdateQuestion={handleUpdateQuestion}
            onFinalizeQuestion={handleFinalizeQuestion}
            viewingMode={session?.settings?.viewing_mode || 'suggestions_only'}
            onConvertToTemplate={handleConvertToTemplate}
            isConverting={isConverting}
            conversionStatus={conversionStatus}
          />
        )}
        
        {activeScreen === 'llm' && (
          <LLMChat
            session={session}
            questions={questions}
            messages={chatMessages}
            user={user}
            onLLMRequest={handleLLMRequest}
          />
        )}
        
        {activeScreen === 'participants' && (
          <ParticipantsList
            session={session}
            participants={participants}
            onlineUsers={onlineUsers}
            user={user}
            isHost={isHost}
            onShowSettings={() => setShowSettings(true)}
            onDeleteSession={deleteCurrentSession}
            onCleanupAllSessions={cleanupAllUserSessions}
            onRemoveUser={removeUserFromSession}
          />
        )}
      </div>

      {/* Session Settings Modal */}
      {showSettings && (
        <SessionSettings
          session={session}
          isHost={isHost}
          user={user}
          onClose={() => setShowSettings(false)}
          onSettingsUpdate={(newSettings) => {
            setSession(prev => ({
              ...prev,
              settings: {
                ...prev.settings,
                ...newSettings
              }
            }));
          }}
        />
      )}
    </div>
  );
};

export default SessionBuilder;