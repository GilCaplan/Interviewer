import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function UserQuestions() {
  const { user } = useAuth();
  const [questions, setQuestions] = useState([]);
  const [newQuestion, setNewQuestion] = useState({ question: '', answer: '' });
  const [isAddingQuestion, setIsAddingQuestion] = useState(false);
  const [editingIndex, setEditingIndex] = useState(null);
  const [practiceMode, setPracticeMode] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [filter, setFilter] = useState('');
  const [category, setCategory] = useState('all');

  // Load questions from localStorage or API on component mount
  useEffect(() => {
    const loadQuestions = async () => {
      // First check localStorage for quick loading
      const storedQuestions = localStorage.getItem(`user_questions_${user?.username}`);
      if (storedQuestions) {
        setQuestions(JSON.parse(storedQuestions));
      }

      // Then try to fetch from API for most up-to-date data
      try {
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
        const response = await fetch(`${apiUrl}/api/questions`, {
          headers: {
            'Authorization': `Bearer ${user?.sessionToken}`
          },
          credentials: 'include'
        });

        // If API call succeeds, update with server data
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.questions) {
            setQuestions(data.questions);
            // Also update localStorage
            localStorage.setItem(`user_questions_${user.username}`, JSON.stringify(data.questions));
          }
        }
      } catch (error) {
        console.log('Using local storage data only. API fetch error:', error);
        // Silently fail - we'll just use localStorage data
      }
    };

    if (user?.username) {
      loadQuestions();
    }
  }, [user]);

  // Save questions to localStorage whenever they change
  useEffect(() => {
    if (user && questions.length > 0) {
      localStorage.setItem(`user_questions_${user.username}`, JSON.stringify(questions));
    }
  }, [questions, user]);

  const addQuestion = () => {
    if (newQuestion.question.trim() === '') return;

    const questionToAdd = {
      ...newQuestion,
      id: Date.now(),
      createdAt: new Date().toISOString(),
      category: category === 'all' ? 'general' : category
    };

    setQuestions([...questions, questionToAdd]);
    setNewQuestion({ question: '', answer: '' });
    setIsAddingQuestion(false);
  };

  const updateQuestion = (index) => {
    const updatedQuestions = [...questions];
    updatedQuestions[index] = {
      ...updatedQuestions[index],
      question: newQuestion.question,
      answer: newQuestion.answer,
      lastUpdated: new Date().toISOString()
    };
    setQuestions(updatedQuestions);
    setEditingIndex(null);
    setNewQuestion({ question: '', answer: '' });
  };

  const deleteQuestion = (index) => {
    if (window.confirm('Are you sure you want to delete this question?')) {
      const updatedQuestions = questions.filter((_, i) => i !== index);
      setQuestions(updatedQuestions);
    }
  };

  const startEditing = (index) => {
    setNewQuestion({
      question: questions[index].question,
      answer: questions[index].answer
    });
    setEditingIndex(index);
    setIsAddingQuestion(false);
  };

  const startPractice = () => {
    setPracticeMode(true);
    setCurrentQuestionIndex(0);
    setShowAnswer(false);
  };

  const nextQuestion = () => {
    if (currentQuestionIndex < filteredQuestions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setShowAnswer(false);
    } else {
      // End of practice
      setPracticeMode(false);
    }
  };

  const previousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
      setShowAnswer(false);
    }
  };

  const toggleAnswer = () => {
    setShowAnswer(!showAnswer);
  };

  const cancelAction = () => {
    setIsAddingQuestion(false);
    setEditingIndex(null);
    setNewQuestion({ question: '', answer: '' });
  };

  // Filter questions based on search and category
  const filteredQuestions = questions.filter(q => {
    const matchesFilter = q.question.toLowerCase().includes(filter.toLowerCase()) ||
                           (q.answer && q.answer.toLowerCase().includes(filter.toLowerCase()));
    const matchesCategory = category === 'all' || q.category === category;
    return matchesFilter && matchesCategory;
  });

  const categories = [
    { value: 'all', label: 'All Categories' },
    { value: 'general', label: 'General' },
    { value: 'technical', label: 'Technical' },
    { value: 'behavioral', label: 'Behavioral' },
    { value: 'system-design', label: 'System Design' },
    { value: 'database', label: 'Database & SQL' },
    { value: 'web-dev', label: 'Web Development' }
  ];

  // Practice mode UI
  if (practiceMode && filteredQuestions.length > 0) {
    const currentQuestion = filteredQuestions[currentQuestionIndex];
    return (
      <div className="practice-container">
        <h2>Practice Mode</h2>
        <div className="practice-progress">
          Question {currentQuestionIndex + 1} of {filteredQuestions.length}
        </div>

        <div className="practice-card">
          <h3 className="practice-question">{currentQuestion.question}</h3>

          {showAnswer ? (
            <div className="practice-answer">
              {currentQuestion.answer ? (
                <div className="answer-content">{currentQuestion.answer}</div>
              ) : (
                <div className="no-answer">No answer provided for this question.</div>
              )}
            </div>
          ) : (
            <button className="show-answer-btn" onClick={toggleAnswer}>
              Reveal Answer
            </button>
          )}
        </div>

        <div className="practice-controls">
          <button
            onClick={previousQuestion}
            disabled={currentQuestionIndex === 0}
            className="practice-btn"
          >
            Previous
          </button>

          <button
            onClick={() => setPracticeMode(false)}
            className="practice-btn exit-btn"
          >
            Exit Practice
          </button>

          <button
            onClick={nextQuestion}
            className="practice-btn"
          >
            {currentQuestionIndex < filteredQuestions.length - 1 ? 'Next' : 'Finish'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="questions-container">
      <h2>Your Interview Questions</h2>
      <p>Create and practice with your own customized interview questions.</p>

      <div className="questions-controls">
        <div className="filter-container">
          <input
            type="text"
            placeholder="Search questions..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="search-input"
          />

          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="category-select"
          >
            {categories.map(cat => (
              <option key={cat.value} value={cat.value}>{cat.label}</option>
            ))}
          </select>
        </div>

        <div className="action-buttons">
          {!isAddingQuestion && editingIndex === null && (
            <button
              onClick={() => setIsAddingQuestion(true)}
              className="action-btn add-btn"
            >
              Add Question
            </button>
          )}

          {questions.length > 0 && !isAddingQuestion && editingIndex === null && (
            <button
              onClick={startPractice}
              className="action-btn practice-btn"
              disabled={filteredQuestions.length === 0}
            >
              Practice Mode
            </button>
          )}
        </div>
      </div>

      {isAddingQuestion && (
        <div className="question-form">
          <h3>Add New Question</h3>

          <div className="form-group">
            <label>Category:</label>
            <select
              value={category === 'all' ? 'general' : category}
              onChange={(e) => setCategory(e.target.value)}
              className="form-select"
            >
              {categories.filter(c => c.value !== 'all').map(cat => (
                <option key={cat.value} value={cat.value}>{cat.label}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Question:</label>
            <textarea
              value={newQuestion.question}
              onChange={(e) => setNewQuestion({ ...newQuestion, question: e.target.value })}
              placeholder="Enter your interview question"
              rows={3}
              className="form-textarea"
            />
          </div>

          <div className="form-group">
            <label>Answer (optional):</label>
            <textarea
              value={newQuestion.answer}
              onChange={(e) => setNewQuestion({ ...newQuestion, answer: e.target.value })}
              placeholder="Enter the answer or leave blank"
              rows={5}
              className="form-textarea"
            />
          </div>

          <div className="form-buttons">
            <button onClick={cancelAction} className="cancel-btn">
              Cancel
            </button>
            <button onClick={addQuestion} className="submit-btn">
              Add Question
            </button>
          </div>
        </div>
      )}

      {editingIndex !== null && (
        <div className="question-form">
          <h3>Edit Question</h3>

          <div className="form-group">
            <label>Question:</label>
            <textarea
              value={newQuestion.question}
              onChange={(e) => setNewQuestion({ ...newQuestion, question: e.target.value })}
              placeholder="Enter your interview question"
              rows={3}
              className="form-textarea"
            />
          </div>

          <div className="form-group">
            <label>Answer:</label>
            <textarea
              value={newQuestion.answer}
              onChange={(e) => setNewQuestion({ ...newQuestion, answer: e.target.value })}
              placeholder="Enter the answer or leave blank"
              rows={5}
              className="form-textarea"
            />
          </div>

          <div className="form-buttons">
            <button onClick={cancelAction} className="cancel-btn">
              Cancel
            </button>
            <button onClick={() => updateQuestion(editingIndex)} className="submit-btn">
              Update Question
            </button>
          </div>
        </div>
      )}

      {!isAddingQuestion && editingIndex === null && (
        <div className="questions-list">
          {filteredQuestions.length === 0 ? (
            <div className="no-questions">
              {questions.length === 0 ? (
                <p>You haven't added any questions yet. Click "Add Question" to get started.</p>
              ) : (
                <p>No questions match your current filters.</p>
              )}
            </div>
          ) : (
            filteredQuestions.map((question, index) => (
              <div key={question.id || index} className="question-card">
                <div className="question-header">
                  <span className="question-category">{question.category || 'General'}</span>
                  <div className="question-actions">
                    <button
                      onClick={() => startEditing(questions.indexOf(question))}
                      className="edit-btn"
                      aria-label="Edit question"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => deleteQuestion(questions.indexOf(question))}
                      className="delete-btn"
                      aria-label="Delete question"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                <h3 className="question-text">{question.question}</h3>

                {question.answer && (
                  <details className="question-answer">
                    <summary>View Answer</summary>
                    <div className="answer-content">{question.answer}</div>
                  </details>
                )}
              </div>
            ))
          )}
        </div>
      )}

      <div className="navigation-buttons">
        <Link to="/" className="back-button">Back to Features</Link>
        <Link to="/llm-questions" className="llm-button">Generate AI Questions</Link>
      </div>
    </div>
  );
}

export default UserQuestions;