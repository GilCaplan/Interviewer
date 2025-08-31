import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom';
import { fetchApi } from '../utils/api';
import InterviewResults from './InterviewResults';
import './Questions.css';
import './Interview.css';

function InterviewSimulation() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isCompleted, setIsCompleted] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(null);
  // const [startTime] = useState(new Date());

  useEffect(() => {
    const initializeInterview = async () => {
      try {
        setLoading(true);
        setError(null);

        if (sessionId === 'new') {
          // Create new interview from template
          const params = new URLSearchParams(location.search);
          const templateId = params.get('template');
          if (!templateId) {
            throw new Error("No template specified for the interview.");
          }

          console.log('Starting interview with template:', templateId);
          const data = await fetchApi('/api/interview/start', {
            method: 'POST',
            body: JSON.stringify({ template_id: templateId }),
          });

          console.log('Interview started:', data);
          // Redirect to the newly created interview session
          navigate(`/interview/${data.interview_session_id}`, { replace: true });

        } else {
          // Load existing interview session
          console.log('Loading interview session:', sessionId);
          const data = await fetchApi(`/api/interview/${sessionId}`);
          console.log('Interview session loaded:', data);
          
          setSession(data.session);
          setCurrentQuestionIndex(data.session.current_question_index || 0);
          
          if (data.session.status === 'completed') {
            setIsCompleted(true);
          }
          
          // Set up timer if template has time limit
          if (data.session.questions && data.session.questions[0]?.time_limit) {
            setTimeRemaining(data.session.questions[0].time_limit * 60); // Convert minutes to seconds
          }
        }
      } catch (err) {
        console.error('Interview initialization error:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    initializeInterview();
  }, [sessionId, location.search, navigate]);

  const decodeHTMLEntities = (text) => {
    if (typeof text !== 'string' || !text) return '';
    const textArea = document.createElement('textarea');
    textArea.innerHTML = text;
    return textArea.value;
  };

  const handleSubmitAnswer = useCallback(async () => {
    if (submitting) return;

    setSubmitting(true);
    try {
      console.log('Submitting answer:', currentAnswer, 'for question index:', currentQuestionIndex);
      
      const response = await fetchApi(`/api/interview/${sessionId}/answer`, {
        method: 'POST',
        body: JSON.stringify({ answer: currentAnswer }),
      });

      console.log('Answer submitted:', response);
      
      const nextIndex = response.next_question_index;
      
      // Update session data
      const updatedSession = await fetchApi(`/api/interview/${sessionId}`);
      setSession(updatedSession.session);
      setCurrentQuestionIndex(nextIndex);
      setCurrentAnswer('');
      
      // Check if we've completed all questions
      if (nextIndex >= updatedSession.session.questions.length) {
        await finishInterview();
      }
      
    } catch (err) {
      console.error('Answer submission error:', err);
      setError(`Failed to submit answer: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  }, [submitting, currentAnswer, currentQuestionIndex, sessionId]);

  // Timer effect
  useEffect(() => {
    if (timeRemaining > 0 && !isCompleted) {
      const timer = setTimeout(() => {
        setTimeRemaining(timeRemaining - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else if (timeRemaining === 0) {
      // Auto-submit when time runs out
      handleSubmitAnswer();
    }
  }, [timeRemaining, isCompleted, handleSubmitAnswer]);

  const finishInterview = async () => {
    try {
      console.log('Finishing interview:', sessionId);
      await fetchApi(`/api/interview/${sessionId}/finish`, {
        method: 'POST',
      });

      // Reload session to get final results
      const finalSession = await fetchApi(`/api/interview/${sessionId}`);
      setSession(finalSession.session);
      setIsCompleted(true);
      console.log('Interview completed:', finalSession.session);
      
    } catch (err) {
      console.error('Interview completion error:', err);
      setError(`Failed to complete interview: ${err.message}`);
    }
  };

  const handleInputChange = (e) => {
    setCurrentAnswer(e.target.value);
  };

  const handleMultipleChoice = (option) => {
    setCurrentAnswer(option);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getCurrentQuestion = () => {
    if (!session || !session.questions || currentQuestionIndex >= session.questions.length) {
      return null;
    }
    return session.questions[currentQuestionIndex];
  };

  if (loading) {
    return <div className="loading">Setting up your interview...</div>;
  }

  if (error) {
    return (
      <div className="mock-interview-container">
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
        <Link to="/templates" className="back-button">Back to Templates</Link>
      </div>
    );
  }

  if (isCompleted && session) {
    return (
      <div className="mock-interview-container">
        <InterviewResults session={session} />
        <div className="interview-actions">
          <Link to="/templates" className="back-button">Back to Templates</Link>
        </div>
      </div>
    );
  }

  if (!session) {
    return <div className="loading">Loading interview data...</div>;
  }

  const currentQuestion = getCurrentQuestion();
  
  if (!currentQuestion) {
    return (
      <div className="mock-interview-container">
        <div className="error-message">No questions available for this interview.</div>
        <Link to="/templates" className="back-button">Back to Templates</Link>
      </div>
    );
  }

  const progress = ((currentQuestionIndex + 1) / session.questions.length) * 100;

  return (
    <div className="mock-interview-container">
      <div className="interview-header">
        <h1>{decodeHTMLEntities(session.template_name)}</h1>
        <div className="interview-progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <span className="progress-text">
            Question {currentQuestionIndex + 1} of {session.questions.length}
          </span>
          {timeRemaining !== null && (
            <div className={`timer ${timeRemaining < 60 ? 'urgent' : ''}`}>
              Time: {formatTime(timeRemaining)}
            </div>
          )}
        </div>
      </div>

      <div className="question-container">
        <div className="question-header">
          <h2>Question {currentQuestionIndex + 1}</h2>
          {currentQuestion.question_type && (
            <span className="question-type">{currentQuestion.question_type.replace('_', ' ')}</span>
          )}
        </div>
        
        <div className="question-text">
          {decodeHTMLEntities(currentQuestion.question_text)}
        </div>

        {currentQuestion.hints && typeof currentQuestion.hints === 'string' && currentQuestion.hints.trim() !== '' && (
          <div className="hints-container">
            <details>
              <summary>💡 Hints</summary>
              <pre className="hint-text">
                {decodeHTMLEntities(currentQuestion.hints)}
              </pre>
            </details>
          </div>
        )}

        <div className="answer-container">
          {currentQuestion.question_type === 'multiple_choice' && currentQuestion.options ? (
            <div className="multiple-choice-options">
              {currentQuestion.options.map((option, index) => (
                <label key={index} className="option-label">
                  <input
                    type="radio"
                    name="multiple-choice"
                    value={option}
                    checked={currentAnswer === option}
                    onChange={() => handleMultipleChoice(option)}
                  />
                  <span className="option-text">{decodeHTMLEntities(option)}</span>
                </label>
              ))}
            </div>
          ) : currentQuestion.question_type === 'true_false' ? (
            <div className="true-false-options">
              <label className="option-label">
                <input
                  type="radio"
                  name="true-false"
                  value="true"
                  checked={currentAnswer === 'true'}
                  onChange={() => handleMultipleChoice('true')}
                />
                <span className="option-text">True</span>
              </label>
              <label className="option-label">
                <input
                  type="radio"
                  name="true-false"
                  value="false"
                  checked={currentAnswer === 'false'}
                  onChange={() => handleMultipleChoice('false')}
                />
                <span className="option-text">False</span>
              </label>
            </div>
          ) : (
            <textarea
              className="answer-input"
              value={currentAnswer}
              onChange={handleInputChange}
              placeholder={
                currentQuestion.question_type === 'coding' 
                  ? 'Enter your code here...' 
                  : 'Enter your answer here...'
              }
              rows={currentQuestion.question_type === 'coding' ? 10 : 4}
            />
          )}
        </div>

        <div className="question-actions">
          <button
            onClick={handleSubmitAnswer}
            disabled={!currentAnswer.trim() || submitting}
            className="submit-button"
          >
            {submitting ? 'Submitting...' : 
             currentQuestionIndex === session.questions.length - 1 ? 'Finish Interview' : 'Next Question'}
          </button>
          
          {currentQuestionIndex < session.questions.length - 1 && (
            <button
              onClick={() => {
                setCurrentAnswer('');
                handleSubmitAnswer();
              }}
              disabled={submitting}
              className="skip-button"
            >
              Skip Question
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default InterviewSimulation;