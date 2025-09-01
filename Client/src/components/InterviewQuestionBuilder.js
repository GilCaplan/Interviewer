import React, { useState, useEffect } from 'react';
import { fetchApi } from '../utils/api';
import './Questions.css';

function InterviewQuestionBuilder({ onQuestionSaved, initialQuestion = null, mode = 'create' }) {
  const [question, setQuestion] = useState({
    question_text: '',
    question_type: 'open_ended',
    options: ['', '', '', ''],
    correct_answer: '',
    hints: '',
    category: '',
    difficulty: 'medium',
    is_ai_generated: false
  });
  
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [generatingAI, setGeneratingAI] = useState(false);

  // Initialize with existing question data if editing
  useEffect(() => {
    if (initialQuestion && mode === 'edit') {
      setQuestion({
        question_text: initialQuestion.question_text || '',
        question_type: initialQuestion.question_type || 'open_ended',
        options: initialQuestion.options || ['', '', '', ''],
        correct_answer: initialQuestion.correct_answer || '',
        hints: initialQuestion.hints || '',
        category: initialQuestion.category || '',
        difficulty: initialQuestion.difficulty || 'medium',
        is_ai_generated: initialQuestion.is_ai_generated || false
      });
    }
  }, [initialQuestion, mode]);

  const handleInputChange = (field, value) => {
    setQuestion(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear success message when user starts editing
    if (saveSuccess) {
      setSaveSuccess(false);
    }
  };

  const handleOptionChange = (index, value) => {
    const newOptions = [...question.options];
    newOptions[index] = value;
    setQuestion(prev => ({
      ...prev,
      options: newOptions
    }));
  };

  const generateAIQuestion = async () => {
    if (!question.category) {
      setError('Please specify a category/subject to generate AI question');
      return;
    }

    setGeneratingAI(true);
    setError(null);

    try {
      const response = await fetchApi('/api/llm-questions', {
        method: 'POST',
        body: JSON.stringify({
          subject: question.category,
          question_type: question.question_type,
          count: 1,
          context: `Generate ${question.difficulty} level question`
        })
      });

      if (response.success && response.questions?.length > 0) {
        const aiQuestion = response.questions[0];
        
        setQuestion(prev => ({
          ...prev,
          question_text: aiQuestion.question_text || prev.question_text,
          options: aiQuestion.options || prev.options,
          correct_answer: aiQuestion.correct_answer || prev.correct_answer,
          hints: aiQuestion.hints ? (Array.isArray(aiQuestion.hints) ? aiQuestion.hints.join('; ') : aiQuestion.hints) : prev.hints,
          is_ai_generated: true
        }));
      } else {
        setError('Failed to generate AI question. Please try again.');
      }
    } catch (err) {
      setError(`AI generation failed: ${err.message}`);
    } finally {
      setGeneratingAI(false);
    }
  };

  const saveQuestion = async () => {
    if (!question.question_text.trim()) {
      setError('Question text is required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const endpoint = mode === 'edit' && initialQuestion?._id 
        ? `/api/interview/questions/${initialQuestion._id}`
        : '/api/interview/questions/save';
      
      const method = mode === 'edit' && initialQuestion?._id ? 'PUT' : 'POST';

      const response = await fetchApi(endpoint, {
        method,
        body: JSON.stringify(question)
      });

      setSaveSuccess(true);
      
      // Call callback if provided
      if (onQuestionSaved) {
        onQuestionSaved(response.question);
      }

      // Clear form for new questions
      if (mode === 'create') {
        setQuestion({
          question_text: '',
          question_type: 'open_ended',
          options: ['', '', '', ''],
          correct_answer: '',
          hints: '',
          category: question.category, // Keep category for easier bulk creation
          difficulty: question.difficulty, // Keep difficulty
          is_ai_generated: false
        });
      }

    } catch (err) {
      setError(`Failed to save question: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="question-builder-container">
      <div className="question-builder-header">
        <h3>{mode === 'edit' ? 'Edit Question' : 'Create New Interview Question'}</h3>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {saveSuccess && (
        <div className="success-message">
          ✅ Question {mode === 'edit' ? 'updated' : 'saved'} successfully!
        </div>
      )}

      <div className="question-form">
        <div className="form-row">
          <div className="form-group">
            <label>Category/Subject:</label>
            <input
              type="text"
              value={question.category}
              onChange={(e) => handleInputChange('category', e.target.value)}
              placeholder="e.g., JavaScript, Python, System Design..."
              className="form-input"
            />
          </div>
          
          <div className="form-group">
            <label>Question Type:</label>
            <select
              value={question.question_type}
              onChange={(e) => handleInputChange('question_type', e.target.value)}
              className="form-select"
            >
              <option value="open_ended">Open Ended</option>
              <option value="multiple_choice">Multiple Choice</option>
              <option value="true_false">True/False</option>
              <option value="coding">Coding</option>
              <option value="short_answer">Short Answer</option>
            </select>
          </div>

          <div className="form-group">
            <label>Difficulty:</label>
            <select
              value={question.difficulty}
              onChange={(e) => handleInputChange('difficulty', e.target.value)}
              className="form-select"
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Question Text:</label>
          <textarea
            value={question.question_text}
            onChange={(e) => handleInputChange('question_text', e.target.value)}
            placeholder="Enter your interview question here..."
            className="form-textarea large"
            rows={4}
          />
        </div>

        {question.question_type === 'multiple_choice' && (
          <div className="form-group">
            <label>Answer Options:</label>
            {question.options.map((option, index) => (
              <div key={index} className="option-input-container">
                <span className="option-label">{String.fromCharCode(65 + index)}.</span>
                <input
                  type="text"
                  value={option}
                  onChange={(e) => handleOptionChange(index, e.target.value)}
                  placeholder={`Option ${String.fromCharCode(65 + index)}`}
                  className="form-input option-input"
                />
              </div>
            ))}
          </div>
        )}

        {(question.question_type === 'multiple_choice' || question.question_type === 'true_false') && (
          <div className="form-group">
            <label>Correct Answer:</label>
            {question.question_type === 'true_false' ? (
              <select
                value={question.correct_answer}
                onChange={(e) => handleInputChange('correct_answer', e.target.value)}
                className="form-select"
              >
                <option value="">Select correct answer...</option>
                <option value="true">True</option>
                <option value="false">False</option>
              </select>
            ) : (
              <select
                value={question.correct_answer}
                onChange={(e) => handleInputChange('correct_answer', e.target.value)}
                className="form-select"
              >
                <option value="">Select correct option...</option>
                {question.options.map((option, index) => 
                  option.trim() && (
                    <option key={index} value={option}>
                      {String.fromCharCode(65 + index)}. {option}
                    </option>
                  )
                )}
              </select>
            )}
          </div>
        )}

        <div className="form-group">
          <label>Hints (Optional):</label>
          <textarea
            value={question.hints}
            onChange={(e) => handleInputChange('hints', e.target.value)}
            placeholder="Enter helpful hints for the question..."
            className="form-textarea"
            rows={2}
          />
        </div>

        <div className="form-actions">
          <button
            onClick={generateAIQuestion}
            disabled={generatingAI || !question.category}
            className="btn btn-secondary ai-generate-btn"
          >
            {generatingAI ? '🤖 Generating...' : '🤖 Generate with AI'}
          </button>

          <button
            onClick={saveQuestion}
            disabled={saving || !question.question_text.trim()}
            className="btn btn-primary save-btn"
          >
            {saving ? 'Saving...' : (mode === 'edit' ? 'Update Question' : 'Save Question')}
          </button>
        </div>
      </div>

      {question.is_ai_generated && (
        <div className="ai-generated-notice">
          🤖 This question was generated with AI assistance
        </div>
      )}
    </div>
  );
}

export default InterviewQuestionBuilder;