import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { fetchApi } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import './TemplatesGallery.css'; // Reuse existing styles
import './Evaluation.css';

function EvaluationDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    subject: '',
    graded: 'all', // 'all', 'graded', 'ungraded'
    user: ''
  });
  const [availableSubjects] = useState(['algorithms', 'data_structures', 'system_design', 'python', 'javascript', 'java', 'react', 'databases', 'networking', 'general']);
  
  useEffect(() => {
    fetchSessions();
  }, [filters]);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      setError('');

      const params = new URLSearchParams();
      if (filters.subject) params.append('subject', filters.subject);
      if (filters.user) params.append('user', filters.user);
      if (filters.graded === 'graded') params.append('graded', 'true');
      if (filters.graded === 'ungraded') params.append('ungraded', 'true');

      const data = await fetchApi(`/api/evaluations/sessions?${params.toString()}`);
      setSessions(data.sessions || []);
    } catch (err) {
      console.error('Error fetching sessions:', err);
      setError('Failed to load evaluation sessions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const getDifficultyColor = (difficulty) => {
    const colors = {
      easy: '#4CAF50',
      medium: '#FF9800', 
      hard: '#F44336'
    };
    return colors[difficulty?.toLowerCase()] || '#757575';
  };

  const getStatusBadge = (session) => {
    if (session.is_graded) {
      return {
        text: `Evaluated (${session.score}%)`,
        className: 'status-badge evaluated',
        color: '#4CAF50'
      };
    }
    return {
      text: 'Needs Evaluation',
      className: 'status-badge pending',
      color: '#FF9800'
    };
  };

  if (loading) {
    return <div className="loading">Loading evaluation sessions...</div>;
  }

  return (
    <div className="templates-gallery-container">
      <div className="gallery-header">
        <h1>📊 Evaluation Dashboard</h1>
        <p>Review and grade completed interview sessions</p>
      </div>

      {/* Filters */}
      <div className="gallery-filters">
        <div className="filter-row">
          <div className="filter-group">
            <label htmlFor="subject-filter">Subject:</label>
            <select 
              id="subject-filter"
              value={filters.subject}
              onChange={(e) => handleFilterChange('subject', e.target.value)}
            >
              <option value="">All Subjects</option>
              {availableSubjects.map(subject => (
                <option key={subject} value={subject}>
                  {subject.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="graded-filter">Status:</label>
            <select 
              id="graded-filter"
              value={filters.graded}
              onChange={(e) => handleFilterChange('graded', e.target.value)}
            >
              <option value="all">All Sessions</option>
              <option value="ungraded">Needs Evaluation</option>
              <option value="graded">Already Evaluated</option>
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="user-filter">User ID:</label>
            <input
              id="user-filter"
              type="text"
              value={filters.user}
              onChange={(e) => handleFilterChange('user', e.target.value)}
              placeholder="Filter by user ID..."
            />
          </div>

          <button 
            onClick={() => setFilters({ subject: '', graded: 'all', user: '' })}
            className="clear-filters-btn"
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Sessions Grid */}
      <div className="templates-grid">
        {error && (
          <div className="error-message">
            <p>{error}</p>
            <button onClick={fetchSessions} className="retry-btn">
              Try Again
            </button>
          </div>
        )}

        {!error && sessions.length === 0 && (
          <div className="no-sessions-message">
            <h3>No evaluation sessions found</h3>
            <p>Try adjusting your filters or check back later for completed interview sessions.</p>
            <Link to="/templates" className="button primary">
              Browse Templates
            </Link>
          </div>
        )}

        {sessions.map((session) => {
          const statusBadge = getStatusBadge(session);
          
          return (
            <div key={session.session_id} className="template-card">
              <div className="template-card-header">
                <h3>{session.template_name}</h3>
                <div className="template-metadata">
                  <span 
                    className="difficulty-badge"
                    style={{ backgroundColor: getDifficultyColor(session.difficulty) }}
                  >
                    {session.difficulty}
                  </span>
                  <span 
                    className={statusBadge.className}
                    style={{ backgroundColor: statusBadge.color }}
                  >
                    {statusBadge.text}
                  </span>
                </div>
              </div>

              <div className="template-card-body">
                <div className="session-info">
                  <p><strong>Subject:</strong> {session.template_category || 'General'}</p>
                  <p><strong>Questions:</strong> {session.total_questions}</p>
                  <p><strong>Completed:</strong> {formatDate(session.completed_at)}</p>
                  <p><strong>User:</strong> {session.user_id}</p>
                </div>

                {session.is_graded && (
                  <div className="evaluation-preview">
                    <div className="score-display">
                      <span className="score-value">{session.score}%</span>
                      <span className="score-label">Final Score</span>
                    </div>
                  </div>
                )}
              </div>

              <div className="template-card-actions">
                {!session.is_graded ? (
                  <>
                    <button 
                      className="action-btn evaluate-btn"
                      onClick={() => navigate(`/evaluations/session/${session.session_id}`)}
                      title="Manually evaluate this session"
                      style={{ background: '#2196F3', color: 'white' }}
                    >
                      ✏️ Evaluate
                    </button>
                    <button 
                      className="action-btn ai-evaluate-btn"
                      onClick={() => navigate(`/evaluations/session/${session.session_id}?ai=true`)}
                      title="Use AI to evaluate this session"
                      style={{ background: '#9C27B0', color: 'white' }}
                    >
                      🤖 AI Evaluate
                    </button>
                  </>
                ) : (
                  <button 
                    className="action-btn view-evaluation-btn"
                    onClick={() => navigate(`/evaluations/results/${session.evaluation_id}`)}
                    title="View evaluation results"
                    style={{ background: '#4CAF50', color: 'white' }}
                  >
                    📊 View Results
                  </button>
                )}
                
                <button 
                  className="action-btn details-btn"
                  onClick={() => navigate(`/evaluations/session/${session.session_id}?view=true`)}
                  title="View session details"
                >
                  👁️ Details
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Statistics */}
      {sessions.length > 0 && (
        <div className="evaluation-stats">
          <h3>📈 Evaluation Statistics</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-value">{sessions.length}</span>
              <span className="stat-label">Total Sessions</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{sessions.filter(s => !s.is_graded).length}</span>
              <span className="stat-label">Pending Evaluation</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{sessions.filter(s => s.is_graded).length}</span>
              <span className="stat-label">Evaluated</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">
                {sessions.filter(s => s.is_graded).length > 0 
                  ? Math.round(sessions.filter(s => s.is_graded).reduce((sum, s) => sum + s.score, 0) / sessions.filter(s => s.is_graded).length)
                  : 0}%
              </span>
              <span className="stat-label">Average Score</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default EvaluationDashboard;