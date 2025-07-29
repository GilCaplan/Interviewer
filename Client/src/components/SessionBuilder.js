import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import io from 'socket.io-client';
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
  
  // Screen data
  const [questions, setQuestions] = useState([]);
  const [participants, setParticipants] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);

  // Initialize session and socket
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
        const token = localStorage.getItem('token');
        
        if (!token) {
          throw new Error('No authentication token found');
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

        // If joining failed, create new session and redirect to new session code
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
        setIsHost(data.session.host_username === user.username);
        
        // Set up questions from session data
        const templateData = data.session.template_data || {};
        setQuestions([
          ...(templateData.questions_queue || []),
          ...(templateData.ready_questions || [])
        ]);

        // Initialize WebSocket connection
        const newSocket = io(apiUrl, {
          auth: {
            token: user.sessionToken
          }
        });

        newSocket.emit('join_session', data.session.session_id);

        // Set up socket event listeners
        setupSocketListeners(newSocket);
        setSocket(newSocket);

        // Load participants
        loadParticipants(data.session.session_id);

      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (user && sessionCode) {
      initializeSession();
    }

    // Cleanup socket on unmount
    return () => {
      if (socket) {
        socket.disconnect();
      }
    };
  }, [sessionCode, user]);

  const setupSocketListeners = (socket) => {
    socket.on('question_building_started', (data) => {
      setQuestions(prev => [...prev, data.question_structure]);
    });

    socket.on('question_content_updated', (data) => {
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
      const response = await fetch(`${apiUrl}/api/sessions/${sessionId}/participants`, {
        headers: {
          'Authorization': `Bearer ${user.sessionToken}`
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
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/${questionNumber}/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.sessionToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ type: questionType }),
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to start question');
      }
    } catch (err) {
      console.error('Error starting question:', err);
      alert('Failed to start question: ' + err.message);
    }
  };

  const handleUpdateQuestion = async (questionId, field, value) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/${questionId}/update`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${user.sessionToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ field, value }),
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to update question');
      }
    } catch (err) {
      console.error('Error updating question:', err);
    }
  };

  const handleFinalizeQuestion = async (questionId) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/${questionId}/finalize`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.sessionToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({}),
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to finalize question');
      }
    } catch (err) {
      console.error('Error finalizing question:', err);
      alert('Failed to finalize question: ' + err.message);
    }
  };

  const handleLLMRequest = async (questionId, field, context) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/${questionId}/llm-suggest`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.sessionToken}`,
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

  if (loading) {
    return <div className="session-loading">Loading session...</div>;
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
          {isHost && <span className="host-badge">HOST</span>}
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