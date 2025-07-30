import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import io from 'socket.io-client';
import { getApiUrl, getAuthToken } from '../utils/authUtils';
import './SessionBuilder.css';

// Sub-components for the 3 screens
import TemplateEditor from './TemplateEditor';
import LLMChat from './LLMChat';
import ParticipantsList from './ParticipantsList';

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
  
  // Screen data
  const [questions, setQuestions] = useState([]);
  const [participants, setParticipants] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);

  // Use ref to track if component is mounted
  const isMountedRef = useRef(true);
  
  // Initialize session and socket
  useEffect(() => {
    isMountedRef.current = true;
    
    const initializeSession = async () => {
      try {
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
        
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
        setSession(data.session);
        
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
      if (socket) {
        console.log('Cleaning up socket connection');
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
    socket.on('question_building_started', (data) => {
      console.log('WebSocket: Question building started', data);
      setQuestions(prev => [...prev, data.question_structure]);
    });

    socket.on('question_content_updated', (data) => {
      console.log('WebSocket: Question content updated', data);
      setQuestions(prev => 
        prev.map(q => 
          q.question_id === data.question_id 
            ? { ...q, user_content: { ...q.user_content, [data.field]: data.value }}
            : q
        )
      );
    });

    socket.on('question_finalized', (data) => {
      setQuestions(prev => 
        prev.map(q => 
          q.question_id === data.question.question_id 
            ? { ...data.question, status: 'finalized' }
            : q
        )
      );
    });

    socket.on('llm_suggestion_generated', (data) => {
      setChatMessages(prev => [...prev, {
        id: data.suggestion.suggestion_id,
        type: 'llm_suggestion',
        content: data.suggestion.suggested_value,
        field: data.suggestion.field,
        question_id: data.question_id,
        timestamp: new Date(),
        username: 'LLM Assistant'
      }]);
    });

    socket.on('collaboration_note_added', (data) => {
      setChatMessages(prev => [...prev, {
        id: data.note.note_id,
        type: 'collaboration_note',
        content: data.note.note,
        question_id: data.question_id,
        timestamp: new Date(data.note.timestamp),
        username: data.note.author
      }]);
    });

    socket.on('user_joined', (data) => {
      setParticipants(prev => [...prev, data.user]);
    });

    socket.on('user_left', (data) => {
      setParticipants(prev => prev.filter(p => p.username !== data.username));
    });
  };

  const loadParticipants = async (sessionId) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      
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
        setParticipants(data.participants);
      }
    } catch (err) {
      console.error('Failed to load participants:', err);
    }
  };

  // Handler functions
  const handleStartQuestion = async (questionNumber, questionType) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      
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
      
      // Refresh session data to ensure UI is in sync
      try {
        const refreshResponse = await fetch(`${apiUrl}/api/sessions/${session.session_id}`, {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });
        
        if (refreshResponse.ok) {
          const refreshData = await refreshResponse.json();
          const templateData = refreshData.session.template_data || {};
          setQuestions([
            ...(templateData.questions_queue || []),
            ...(templateData.ready_questions || [])
          ]);
          console.log('Session state refreshed after question creation');
        }
      } catch (refreshError) {
        console.warn('Could not refresh session state:', refreshError);
      }
      
    } catch (err) {
      console.error('Error starting question:', err);
      alert('Failed to start question: ' + err.message);
    }
  };

  const handleUpdateQuestion = async (questionId, field, value) => {
    console.log('handleUpdateQuestion called:', { questionId, field, value, sessionId: session?.session_id });
    
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      
      // Get token with fallback
      let authToken = localStorage.getItem('token');
      if (!authToken && user?.sessionToken) {
        authToken = user.sessionToken;
      }
      
      console.log('Update request params:', { 
        sessionId: session?.session_id, 
        hasToken: !!authToken,
        apiUrl 
      });
      
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/${questionId}/update`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ field, value }),
        credentials: 'include'
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
          const errorData = await response.text();
          console.error('Update question failed:', response.status, errorData);
          
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
      
      console.log('Question update successful');
    } catch (err) {
      console.error('Error updating question:', err);
      alert('Failed to update question: ' + err.message);
    }
  };

  const handleFinalizeQuestion = async (questionId) => {
    console.log('Attempting to finalize question:', {
      questionId,
      sessionId: session?.session_id,
      availableQuestions: questions.map(q => ({ id: q.question_id, number: q.question_number, status: q.status }))
    });
    
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      
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
      alert('Failed to finalize question: ' + err.message);
    }
  };

  const handleLLMRequest = async (questionId, field, context) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      
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
        body: JSON.stringify({ field, context }),
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to get LLM suggestion');
      }
    } catch (err) {
      console.error('Error requesting LLM suggestion:', err);
      alert('Failed to get LLM suggestion: ' + err.message);
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
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
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
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      
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
        alert(`Successfully cleaned up ${data.deleted_sessions} sessions. Redirecting to home...`);
        navigate('/');
      } else {
        const errorData = await response.text();
        alert('Failed to cleanup sessions: ' + errorData);
      }
    } catch (err) {
      console.error('Error cleaning up sessions:', err);
      alert('Failed to cleanup sessions: ' + err.message);
    }
  };

  const deleteCurrentSession = async () => {
    if (!window.confirm('This will permanently delete this session and all its data. Are you sure?')) {
      return;
    }

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      
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
        alert('Session deleted successfully. Redirecting to home...');
        navigate('/');
      } else {
        const errorData = await response.text();
        alert('Failed to delete session: ' + errorData);
      }
    } catch (err) {
      console.error('Error deleting session:', err);
      alert('Failed to delete session: ' + err.message);
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
          <h1>{session.title}</h1>
          <p>Session Code: <strong>{session.session_code}</strong></p>
          <p>Subject: {session.subject}</p>
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
            Users ({participants.length})
          </button>
        </div>

        <div className="session-actions">
          <button onClick={() => navigate('/')}>Leave Session</button>
          {isHost && (
            <>
              <button 
                onClick={deleteCurrentSession}
                style={{ 
                  backgroundColor: '#dc3545', 
                  color: 'white',
                  marginLeft: '10px',
                  padding: '8px 12px',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                🗑️ Delete Session
              </button>
              <button 
                onClick={cleanupAllUserSessions}
                style={{ 
                  backgroundColor: '#6c757d', 
                  color: 'white',
                  marginLeft: '5px',
                  padding: '8px 12px',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                🧹 Cleanup All Sessions
              </button>
            </>
          )}
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
            user={user}
            isHost={isHost}
          />
        )}
      </div>
    </div>
  );
};

export default SessionBuilder;