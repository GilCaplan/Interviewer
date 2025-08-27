import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { fetchApi } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import './Questions.css';
import './Evaluation.css';

function EvaluationSession() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  
  const [sessionData, setSessionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [evaluation, setEvaluation] = useState({
    scores: [],
    total_score: 0,
    feedback: '',
    recommendations: [],
    evaluation_criteria: {}
  });

  // Check URL parameters
  const params = new URLSearchParams(location.search);
  const isAIEvaluation = params.get('ai') === 'true';
  const isViewOnly = params.get('view') === 'true';

  useEffect(() => {
    fetchSessionData();
  }, [sessionId]);

  useEffect(() => {
    // Calculate total score when individual scores change
    if (evaluation.scores.length > 0) {
      const total = evaluation.scores.reduce((sum, score) => sum + (score.score || 0), 0);
      const average = total / evaluation.scores.length;
      setEvaluation(prev => ({
        ...prev,
        total_score: Math.round(average * 100) / 100
      }));
    }
  }, [evaluation.scores]);

  const fetchSessionData = async () => {
    try {
      setLoading(true);
      setError('');

      const data = await fetchApi(`/api/evaluations/session/${sessionId}`);
      setSessionData(data);

      // Initialize evaluation scores for each question
      if (data.answers && data.answers.length > 0) {
        const initialScores = data.answers.map((answer, index) => ({
          question_index: index,
          score: answer.is_correct ? 100 : 0, // Start with auto-graded score
          feedback: answer.is_correct ? 'Correct answer' : 'Incorrect answer'
        }));
        
        setEvaluation(prev => ({
          ...prev,
          scores: initialScores
        }));
      }

      // If this is an AI evaluation request, trigger it automatically
      if (isAIEvaluation && !data.is_already_graded) {
        handleAIEvaluation();
      }

    } catch (err) {
      console.error('Error fetching session data:', err);
      setError('Failed to load session data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleScoreChange = (questionIndex, score) => {
    const numericScore = Math.max(0, Math.min(100, parseInt(score) || 0));
    setEvaluation(prev => ({
      ...prev,
      scores: prev.scores.map(s => 
        s.question_index === questionIndex 
          ? { ...s, score: numericScore }
          : s
      )
    }));
  };

  const handleFeedbackChange = (questionIndex, feedback) => {
    setEvaluation(prev => ({
      ...prev,
      scores: prev.scores.map(s => 
        s.question_index === questionIndex 
          ? { ...s, feedback }
          : s
      )
    }));
  };

  const addRecommendation = () => {
    setEvaluation(prev => ({
      ...prev,
      recommendations: [...prev.recommendations, '']
    }));
  };

  const updateRecommendation = (index, value) => {
    setEvaluation(prev => ({
      ...prev,
      recommendations: prev.recommendations.map((rec, i) => 
        i === index ? value : rec
      )
    }));
  };

  const removeRecommendation = (index) => {
    setEvaluation(prev => ({
      ...prev,
      recommendations: prev.recommendations.filter((_, i) => i !== index)
    }));
  };

  const handleSubmitEvaluation = async () => {
    if (submitting) return;

    try {
      setSubmitting(true);
      setError('');

      // Validate evaluation
      if (!evaluation.feedback.trim()) {
        setError('Please provide overall feedback before submitting.');
        return;
      }

      if (evaluation.scores.some(s => s.score == null || s.score < 0 || s.score > 100)) {
        setError('Please ensure all question scores are between 0 and 100.');
        return;
      }

      const evaluationData = {
        session_id: sessionId,
        scores: evaluation.scores.filter(s => s.feedback && s.feedback.trim()),
        total_score: evaluation.total_score,
        feedback: evaluation.feedback,
        evaluation_method: 'manual',
        recommendations: evaluation.recommendations.filter(r => r.trim()),
        evaluation_criteria: {
          evaluator: user.username,
          evaluation_date: new Date().toISOString(),
          ...evaluation.evaluation_criteria
        }
      };

      console.log('Submitting evaluation:', evaluationData);
      const result = await fetchApi('/api/evaluations/evaluate', {
        method: 'POST',
        body: JSON.stringify(evaluationData)
      });

      console.log('Evaluation submitted:', result);
      
      // Redirect to results page
      navigate(`/evaluations/results/${result.evaluation_id}`);
      
    } catch (err) {
      console.error('Error submitting evaluation:', err);
      setError(`Failed to submit evaluation: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleAIEvaluation = async () => {
    if (submitting) return;

    try {
      setSubmitting(true);
      setError('');

      console.log('Requesting AI evaluation for session:', sessionId);
      const result = await fetchApi('/api/evaluations/llm-evaluate', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId })
      });

      console.log('AI evaluation completed:', result);
      
      // Redirect to results page
      navigate(`/evaluations/results/${result.evaluation_id}`);
      
    } catch (err) {
      console.error('Error with AI evaluation:', err);
      if (err.message.includes('not available')) {
        setError('AI evaluation service is currently unavailable. Please use manual evaluation instead.');
      } else {
        setError(`Failed to complete AI evaluation: ${err.message}`);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const formatQuestionType = (type) => {
    return type?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Question';
  };

  if (loading) {
    return <div className="loading">Loading session data...</div>;
  }

  if (error && !sessionData) {
    return (
      <div className="mock-interview-container">
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
        <button onClick={fetchSessionData} className="retry-btn">Try Again</button>
      </div>
    );
  }

  if (!sessionData) {
    return <div className="loading">No session data available.</div>;
  }

  return (
    <div className="evaluation-session-container">
      <div className="session-header">
        <h1>📊 {isViewOnly ? 'Session Details' : isAIEvaluation ? 'AI Evaluation' : 'Manual Evaluation'}</h1>
        <div className="session-info">
          <h2>{sessionData.template_name}</h2>
          <div className="session-metadata">
            <span>Category: {sessionData.template_category}</span>
            <span>Difficulty: {sessionData.difficulty}</span>
            <span>Questions: {sessionData.answers?.length || 0}</span>
            <span>Completed: {new Date(sessionData.completed_at).toLocaleString()}</span>
          </div>
        </div>
        
        {sessionData.is_already_graded && (
          <div className="already-graded-notice">
            <strong>⚠️ This session has already been evaluated.</strong>
            <button 
              onClick={() => navigate(`/evaluations/results/${sessionData.existing_evaluation}`)}
              className="view-existing-btn"
            >
              View Existing Evaluation
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Question Evaluation */}
      <div className="questions-evaluation">
        <h3>Question-by-Question Evaluation</h3>
        
        {sessionData.answers?.map((answer, index) => {
          const currentScore = evaluation.scores.find(s => s.question_index === index);
          
          return (
            <div key={index} className="question-evaluation-card">
              <div className="question-header">
                <h4>Question {index + 1}</h4>
                <span className="question-type">
                  {formatQuestionType(answer.question_type)}
                </span>
              </div>

              <div className="question-content">
                <div className="question-text">
                  <strong>Question:</strong> {answer.question_text}
                </div>
                
                {answer.options && (
                  <div className="question-options">
                    <strong>Options:</strong>
                    <ul>
                      {answer.options.map((option, idx) => (
                        <li key={idx}>{option}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="answer-section">
                  <div className="student-answer">
                    <strong>Student Answer:</strong>
                    <div className="answer-text">{answer.user_answer || 'No answer provided'}</div>
                  </div>
                  
                  <div className="correct-answer">
                    <strong>Correct Answer:</strong>
                    <div className="answer-text expected">{answer.correct_answer}</div>
                  </div>

                  <div className="auto-grade">
                    <strong>Auto-graded:</strong>
                    <span className={answer.auto_marked_correct ? 'correct' : 'incorrect'}>
                      {answer.auto_marked_correct ? '✅ Correct' : '❌ Incorrect'}
                    </span>
                  </div>
                </div>

                {answer.hints && answer.hints.length > 0 && (
                  <div className="question-hints">
                    <strong>Available Hints:</strong>
                    <ul>
                      {answer.hints.map((hint, idx) => (
                        <li key={idx}>{hint}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {!isViewOnly && !sessionData.is_already_graded && (
                <div className="evaluation-inputs">
                  <div className="score-input">
                    <label htmlFor={`score-${index}`}>Score (0-100):</label>
                    <input
                      id={`score-${index}`}
                      type="number"
                      min="0"
                      max="100"
                      value={currentScore?.score || 0}
                      onChange={(e) => handleScoreChange(index, e.target.value)}
                    />
                  </div>
                  
                  <div className="feedback-input">
                    <label htmlFor={`feedback-${index}`}>Feedback:</label>
                    <textarea
                      id={`feedback-${index}`}
                      value={currentScore?.feedback || ''}
                      onChange={(e) => handleFeedbackChange(index, e.target.value)}
                      placeholder="Provide specific feedback for this answer..."
                      rows="3"
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Overall Evaluation */}
      {!isViewOnly && !sessionData.is_already_graded && (
        <div className="overall-evaluation">
          <h3>Overall Evaluation</h3>
          
          <div className="total-score-display">
            <label>Total Score:</label>
            <span className="score-value">{evaluation.total_score.toFixed(1)}%</span>
          </div>

          <div className="overall-feedback">
            <label htmlFor="overall-feedback">Overall Feedback:</label>
            <textarea
              id="overall-feedback"
              value={evaluation.feedback}
              onChange={(e) => setEvaluation(prev => ({ ...prev, feedback: e.target.value }))}
              placeholder="Provide comprehensive feedback about the overall performance..."
              rows="5"
              required
            />
          </div>

          <div className="recommendations-section">
            <label>Recommendations for Improvement:</label>
            {evaluation.recommendations.map((rec, index) => (
              <div key={index} className="recommendation-input">
                <input
                  type="text"
                  value={rec}
                  onChange={(e) => updateRecommendation(index, e.target.value)}
                  placeholder="Enter a recommendation..."
                />
                <button 
                  onClick={() => removeRecommendation(index)}
                  className="remove-rec-btn"
                >
                  ❌
                </button>
              </div>
            ))}
            <button onClick={addRecommendation} className="add-rec-btn">
              ➕ Add Recommendation
            </button>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="evaluation-actions">
        <button 
          onClick={() => navigate('/evaluations')}
          className="back-button"
        >
          ← Back to Dashboard
        </button>

        {!isViewOnly && !sessionData.is_already_graded && (
          <>
            {!isAIEvaluation && (
              <button 
                onClick={handleSubmitEvaluation}
                disabled={submitting || !evaluation.feedback.trim()}
                className="submit-evaluation-btn"
              >
                {submitting ? 'Submitting...' : 'Submit Evaluation'}
              </button>
            )}

            <button 
              onClick={handleAIEvaluation}
              disabled={submitting}
              className="ai-evaluation-btn"
            >
              {submitting ? 'Processing...' : '🤖 Use AI Evaluation'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default EvaluationSession;