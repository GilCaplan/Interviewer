import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom';
import { fetchApi } from '../utils/api';
import InterviewSummary from './InterviewSummary';
import './Questions.css';

function MockInterviewSession() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isCompleted, setIsCompleted] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [currentAnswer, setCurrentAnswer] = useState('');

  useEffect(() => {
    const initializeSession = async () => {
      try {
        setLoading(true);
        setError(null);

        if (sessionId === 'new') {
          const params = new URLSearchParams(location.search);
          const templateId = params.get('template');
          if (!templateId) {
            throw new Error("No template specified for the new interview.");
          }

          const data = await fetchApi('/api/sessions/create-from-template', {
            method: 'POST',
            body: JSON.stringify({ template_id: templateId }),
          });

          // Redirect to the newly created session's URL, which will trigger a re-render
          navigate(`/interview/${data.session.session_id}`, { replace: true });

        } else {
          // Load an existing session's data
          const data = await fetchApi(`/api/sessions/${sessionId}`);
          setSession(data.session);
          setCurrentQuestionIndex(data.session.current_question_index || 0);
          if (data.session.status === 'completed') {
            setIsCompleted(true);
          }
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (sessionId) {
      initializeSession();
    }
  }, [sessionId, navigate, location.search]);

  const handleAnswerChange = (e) => {
    setCurrentAnswer(e.target.value);
  };

  const completeInterview = async (finalAnswerPayload = null) => {
    try {
      const data = await fetchApi(`/api/sessions/${session.session_id}/complete`, {
        method: 'POST',
        body: finalAnswerPayload ? JSON.stringify(finalAnswerPayload) : null,
      });
      // Update session state with the final data from the server for the summary page
      setSession(data.session);
      setIsCompleted(true);
    } catch (err) {
      setError(`Failed to complete interview: ${err.message}`);
    }
  };

  const submitAnswer = async () => {
    try {
      const nextIndex = currentQuestionIndex + 1;
      if (nextIndex < session.questions.length) {
        // Not the last question, submit answer normally
        await fetchApi(`/api/sessions/${session.session_id}/answer`, {
          method: 'POST',
          body: JSON.stringify({
            question_index: currentQuestionIndex,
            answer: currentAnswer,
          }),
        });
        // Advance to the next question
        setCurrentQuestionIndex(nextIndex);
        setCurrentAnswer('');
      } else {
        // This IS the last question. Call completeInterview with the final answer.
        const finalAnswerPayload = {
          final_answer: {
            question_index: currentQuestionIndex,
            answer: currentAnswer,
          }
        };
        await completeInterview(finalAnswerPayload);
      }
    } catch (err) {
      setError(`Failed to submit answer: ${err.message}`);
    }
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
            <InterviewSummary session={session} />
            <Link to="/templates" className="back-button">Back to Templates</Link>
        </div>
    );
  }

  if (!session || !session.questions || session.questions.length === 0) {
    return (
      <div className="mock-interview-container">
        <h2>Interview Session</h2>
        <p>This interview template has no questions.</p>
        <Link to="/templates" className="back-button">Back to Templates</Link>
      </div>
    );
  }

  const currentQuestion = session.questions[currentQuestionIndex];

  return (
    <div className="mock-interview-container">
      <div className="interview-header">
        <h2>{session.template_name || session.title}</h2>
        <div className="interview-progress">
          Question {currentQuestionIndex + 1} of {session.questions.length}
        </div>
      </div>
      <hr />
      <div className="question-card-interview">
        <p className="question-text-interview">{currentQuestion.question_text}</p>
        
        {currentQuestion.type === 'multiple_choice' ? (
          <div className="question-options-container">
            {currentQuestion.options.map((option, index) => (
              <div key={index} className="radio-option">
                <input
                  type="radio"
                  id={`option-${index}`}
                  name="mcq-answer"
                  value={option}
                  checked={currentAnswer === option}
                  onChange={handleAnswerChange}
                />
                <label htmlFor={`option-${index}`}>{option}</label>
              </div>
            ))}
          </div>
        ) : (
          <textarea
            className="answer-textarea"
            value={currentAnswer}
            onChange={handleAnswerChange}
            placeholder="Type your answer here..."
          />
        )}
      </div>
      <div className="practice-controls" style={{ justifyContent: 'flex-end', marginTop: '20px' }}>
        <button onClick={submitAnswer} className="action-btn" disabled={!currentAnswer}>
          {currentQuestionIndex < session.questions.length - 1 ? 'Next Question' : 'Finish Interview'}
        </button>
      </div>
    </div>
  );
}

export default MockInterviewSession;