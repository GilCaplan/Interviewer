import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchApi } from '../utils/api';
import './Questions.css';
import './Evaluation.css';

function EvaluationResults() {
  const { evaluationId } = useParams();
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [exportLoading, setExportLoading] = useState(false);

  useEffect(() => {
    fetchEvaluationDetails();
  }, [evaluationId]);

  const fetchEvaluationDetails = async () => {
    try {
      setLoading(true);
      setError('');

      const data = await fetchApi(`/api/evaluations/${evaluationId}`);
      setEvaluation(data);
    } catch (err) {
      console.error('Error fetching evaluation:', err);
      setError('Failed to load evaluation results. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleExportResults = async () => {
    try {
      setExportLoading(true);
      
      const data = await fetchApi(`/api/evaluations/export/${evaluation.session_id}?format=json`);
      
      // Create and download JSON file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `evaluation-results-${evaluation.evaluation_id}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
    } catch (err) {
      console.error('Export error:', err);
      setError('Failed to export results. Please try again.');
    } finally {
      setExportLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return '#4CAF50';
    if (score >= 80) return '#8BC34A';
    if (score >= 70) return '#FFC107';
    if (score >= 60) return '#FF9800';
    return '#F44336';
  };

  const getPerformanceLevel = (score) => {
    if (score >= 90) return 'Excellent';
    if (score >= 80) return 'Good';
    if (score >= 70) return 'Satisfactory';
    if (score >= 60) return 'Needs Improvement';
    return 'Poor';
  };

  const getMethodBadge = (method) => {
    const badges = {
      manual: { text: '👤 Manual', color: '#2196F3' },
      llm: { text: '🤖 AI Generated', color: '#9C27B0' },
      self: { text: '🔄 Self Assessment', color: '#FF9800' }
    };
    return badges[method] || badges.manual;
  };

  if (loading) {
    return <div className="loading">Loading evaluation results...</div>;
  }

  if (error || !evaluation) {
    return (
      <div className="mock-interview-container">
        <div className="error-message">
          <strong>Error:</strong> {error || 'Evaluation not found'}
        </div>
        <Link to="/evaluation" className="back-button">Back to Dashboard</Link>
      </div>
    );
  }

  const methodBadge = getMethodBadge(evaluation.evaluation_method);
  const scoreColor = getScoreColor(evaluation.total_score);
  const performanceLevel = getPerformanceLevel(evaluation.total_score);

  return (
    <div className="evaluation-results-container">
      <div className="results-header">
        <h1>📊 Evaluation Results</h1>
        <div className="evaluation-metadata">
          <div className="template-info">
            <h2>{evaluation.template_name}</h2>
            <span className="template-category">{evaluation.template_category}</span>
          </div>
          <div className="evaluation-info">
            <span 
              className="method-badge"
              style={{ backgroundColor: methodBadge.color }}
            >
              {methodBadge.text}
            </span>
            <span className="evaluation-date">
              {new Date(evaluation.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Score Summary */}
      <div className="score-summary">
        <div className="score-display">
          <div className="main-score" style={{ color: scoreColor }}>
            <span className="score-number">{evaluation.total_score}%</span>
            <span className="score-label">{performanceLevel}</span>
          </div>
          
          <div className="score-breakdown">
            <div className="score-stats">
              <div className="stat">
                <span className="stat-label">Total Questions:</span>
                <span className="stat-value">{evaluation.scores?.length || 0}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Evaluator:</span>
                <span className="stat-value">
                  {evaluation.evaluator_user_id === 'llm_service' ? 'AI System' : evaluation.evaluator_user_id}
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">Student:</span>
                <span className="stat-value">{evaluation.evaluated_user_id}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="performance-visualization">
          <div className="circular-progress">
            <svg width="120" height="120" viewBox="0 0 120 120">
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                stroke="#e0e0e0"
                strokeWidth="10"
              />
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="none"
                stroke={scoreColor}
                strokeWidth="10"
                strokeLinecap="round"
                strokeDasharray={`${evaluation.total_score * 3.14} 314`}
                strokeDashoffset="78.5"
                transform="rotate(-90 60 60)"
              />
              <text x="60" y="65" textAnchor="middle" fontSize="20" fontWeight="bold" fill={scoreColor}>
                {Math.round(evaluation.total_score)}%
              </text>
            </svg>
          </div>
        </div>
      </div>

      {/* Overall Feedback */}
      <div className="overall-feedback-section">
        <h3>📝 Overall Feedback</h3>
        <div className="feedback-content">
          <p>{evaluation.feedback}</p>
        </div>
      </div>

      {/* Question-by-Question Scores */}
      {evaluation.scores && evaluation.scores.length > 0 && (
        <div className="detailed-scores">
          <h3>📋 Question-by-Question Breakdown</h3>
          <div className="scores-list">
            {evaluation.scores.map((score, index) => (
              <div key={index} className="score-item">
                <div className="score-header">
                  <span className="question-number">Q{score.question_index + 1}</span>
                  <span 
                    className="individual-score"
                    style={{ color: getScoreColor(score.score) }}
                  >
                    {score.score}/100
                  </span>
                </div>
                {score.feedback && (
                  <div className="score-feedback">
                    <p>{score.feedback}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {evaluation.recommendations && evaluation.recommendations.length > 0 && (
        <div className="recommendations-section">
          <h3>💡 Recommendations for Improvement</h3>
          <ul className="recommendations-list">
            {evaluation.recommendations.map((recommendation, index) => (
              <li key={index} className="recommendation-item">
                {recommendation}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Performance Insights */}
      <div className="performance-insights">
        <h3>📈 Performance Analysis</h3>
        <div className="insights-grid">
          {evaluation.total_score >= 90 && (
            <div className="insight-card excellent">
              <span className="insight-icon">🏆</span>
              <div className="insight-content">
                <h4>Outstanding Performance!</h4>
                <p>Excellent understanding of the subject matter with consistent high-quality responses.</p>
              </div>
            </div>
          )}

          {evaluation.total_score >= 70 && evaluation.total_score < 90 && (
            <div className="insight-card good">
              <span className="insight-icon">👍</span>
              <div className="insight-content">
                <h4>Good Performance</h4>
                <p>Solid understanding with room for minor improvements in specific areas.</p>
              </div>
            </div>
          )}

          {evaluation.total_score < 70 && (
            <div className="insight-card needs-improvement">
              <span className="insight-icon">📚</span>
              <div className="insight-content">
                <h4>Areas for Improvement</h4>
                <p>Focus on studying the recommended topics and practice more questions.</p>
              </div>
            </div>
          )}

          {evaluation.evaluation_method === 'llm' && (
            <div className="insight-card ai-generated">
              <span className="insight-icon">🤖</span>
              <div className="insight-content">
                <h4>AI-Powered Evaluation</h4>
                <p>This evaluation was generated using advanced AI to provide objective, consistent feedback.</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="results-actions">
        <Link to="/evaluation" className="button secondary">
          ← Back to Dashboard
        </Link>
        
        <Link to="/templates" className="button primary">
          Practice More
        </Link>
        
        <button 
          onClick={handleExportResults}
          disabled={exportLoading}
          className="button tertiary"
        >
          {exportLoading ? 'Exporting...' : '📄 Export Results'}
        </button>
        
        <button 
          onClick={() => window.print()}
          className="button tertiary"
        >
          🖨️ Print
        </button>
      </div>
    </div>
  );
}

export default EvaluationResults;