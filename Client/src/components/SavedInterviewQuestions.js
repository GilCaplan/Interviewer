import React, { useState, useEffect } from 'react';
import { fetchApi } from '../utils/api';
import InterviewQuestionBuilder from './InterviewQuestionBuilder';
import './Questions.css';

function SavedInterviewQuestions() {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showBuilder, setShowBuilder] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState(null);
  
  // Filter states
  const [filters, setFilters] = useState({
    category: '',
    difficulty: '',
    question_type: ''
  });

  // Pagination states
  const [pageInfo, setPageInfo] = useState({
    limit: 20,
    skip: 0,
    total_count: 0,
    has_more: false
  });

  const loadQuestions = async (resetPagination = false) => {
    try {
      setLoading(true);
      setError(null);

      const skip = resetPagination ? 0 : pageInfo.skip;
      const params = new URLSearchParams({
        limit: pageInfo.limit,
        skip: skip,
        ...Object.fromEntries(Object.entries(filters).filter(([_, value]) => value))
      });

      const response = await fetchApi(`/api/interview/questions/my?${params}`);
      
      if (resetPagination) {
        setQuestions(response.questions);
        setPageInfo(response.page_info);
      } else {
        setQuestions(prev => [...prev, ...response.questions]);
        setPageInfo(response.page_info);
      }

    } catch (err) {
      setError(`Failed to load questions: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuestions(true);
  }, [filters]);

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const loadMoreQuestions = () => {
    setPageInfo(prev => ({ ...prev, skip: prev.skip + prev.limit }));
    loadQuestions(false);
  };

  const handleQuestionSaved = (savedQuestion) => {
    if (editingQuestion) {
      // Update existing question in list
      setQuestions(prev => prev.map(q => 
        q._id === savedQuestion._id ? savedQuestion : q
      ));
      setEditingQuestion(null);
    } else {
      // Add new question to top of list
      setQuestions(prev => [savedQuestion, ...prev]);
    }
    setShowBuilder(false);
  };

  const handleEditQuestion = (question) => {
    setEditingQuestion(question);
    setShowBuilder(true);
  };

  const handleDeleteQuestion = async (questionId) => {
    if (!window.confirm('Are you sure you want to delete this question?')) {
      return;
    }

    try {
      await fetchApi(`/api/interview/questions/${questionId}`, {
        method: 'DELETE'
      });

      setQuestions(prev => prev.filter(q => q._id !== questionId));
    } catch (err) {
      setError(`Failed to delete question: ${err.message}`);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getQuestionTypeIcon = (type) => {
    const icons = {
      open_ended: '📝',
      multiple_choice: '☑️',
      true_false: '✅',
      coding: '💻',
      short_answer: '✏️'
    };
    return icons[type] || '❓';
  };

  const getDifficultyColor = (difficulty) => {
    const colors = {
      easy: '#4CAF50',
      medium: '#FF9800',
      hard: '#F44336'
    };
    return colors[difficulty] || '#757575';
  };

  if (showBuilder) {
    return (
      <div className="saved-questions-container">
        <div className="page-header">
          <button 
            onClick={() => {
              setShowBuilder(false);
              setEditingQuestion(null);
            }}
            className="btn btn-secondary back-btn"
          >
            ← Back to Saved Questions
          </button>
        </div>

        <InterviewQuestionBuilder
          mode={editingQuestion ? 'edit' : 'create'}
          initialQuestion={editingQuestion}
          onQuestionSaved={handleQuestionSaved}
        />
      </div>
    );
  }

  return (
    <div className="saved-questions-container">
      <div className="page-header">
        <h2>My Saved Interview Questions</h2>
        <button
          onClick={() => setShowBuilder(true)}
          className="btn btn-primary"
        >
          + Create New Question
        </button>
      </div>

      <div className="filters-section">
        <div className="filter-row">
          <div className="filter-group">
            <label>Category:</label>
            <input
              type="text"
              value={filters.category}
              onChange={(e) => handleFilterChange('category', e.target.value)}
              placeholder="Filter by category..."
              className="filter-input"
            />
          </div>

          <div className="filter-group">
            <label>Difficulty:</label>
            <select
              value={filters.difficulty}
              onChange={(e) => handleFilterChange('difficulty', e.target.value)}
              className="filter-select"
            >
              <option value="">All Difficulties</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>

          <div className="filter-group">
            <label>Type:</label>
            <select
              value={filters.question_type}
              onChange={(e) => handleFilterChange('question_type', e.target.value)}
              className="filter-select"
            >
              <option value="">All Types</option>
              <option value="open_ended">Open Ended</option>
              <option value="multiple_choice">Multiple Choice</option>
              <option value="true_false">True/False</option>
              <option value="coding">Coding</option>
              <option value="short_answer">Short Answer</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {loading && questions.length === 0 ? (
        <div className="loading-message">Loading your saved questions...</div>
      ) : (
        <>
          <div className="questions-count">
            {pageInfo.total_count} saved questions found
          </div>

          {questions.length === 0 ? (
            <div className="empty-state">
              <h3>No saved questions yet</h3>
              <p>Create your first interview question to get started!</p>
              <button
                onClick={() => setShowBuilder(true)}
                className="btn btn-primary"
              >
                Create Your First Question
              </button>
            </div>
          ) : (
            <div className="questions-list">
              {questions.map((question) => (
                <div key={question._id} className="question-card">
                  <div className="question-card-header">
                    <div className="question-metadata">
                      <span className="question-type-icon">
                        {getQuestionTypeIcon(question.question_type)}
                      </span>
                      <span className="question-category">{question.category || 'General'}</span>
                      <span 
                        className="question-difficulty"
                        style={{ color: getDifficultyColor(question.difficulty) }}
                      >
                        {question.difficulty}
                      </span>
                      {question.is_ai_generated && (
                        <span className="ai-badge">🤖 AI</span>
                      )}
                    </div>
                    <div className="question-actions">
                      <button
                        onClick={() => handleEditQuestion(question)}
                        className="btn btn-sm btn-secondary"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteQuestion(question._id)}
                        className="btn btn-sm btn-danger"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  <div className="question-content">
                    <p className="question-text">{question.question_text}</p>
                    
                    {question.options && question.options.length > 0 && (
                      <div className="question-options">
                        <strong>Options:</strong>
                        <ul>
                          {question.options.map((option, index) => (
                            <li key={index} className={option === question.correct_answer ? 'correct-option' : ''}>
                              {String.fromCharCode(65 + index)}. {option}
                              {option === question.correct_answer && <span className="correct-mark"> ✓</span>}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {question.hints && (
                      <div className="question-hints">
                        <strong>Hints:</strong> {question.hints}
                      </div>
                    )}
                  </div>

                  <div className="question-card-footer">
                    <span className="question-date">
                      Created: {formatDate(question.created_at)}
                    </span>
                    {question.updated_at && question.updated_at !== question.created_at && (
                      <span className="question-date">
                        Updated: {formatDate(question.updated_at)}
                      </span>
                    )}
                  </div>
                </div>
              ))}

              {pageInfo.has_more && (
                <div className="load-more-container">
                  <button
                    onClick={loadMoreQuestions}
                    disabled={loading}
                    className="btn btn-secondary load-more-btn"
                  >
                    {loading ? 'Loading...' : 'Load More Questions'}
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default SavedInterviewQuestions;