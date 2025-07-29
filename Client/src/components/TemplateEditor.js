import React, { useState } from 'react';
import './TemplateEditor.css';

const TemplateEditor = ({ 
  session, 
  questions, 
  isHost, 
  user, 
  onStartQuestion, 
  onUpdateQuestion, 
  onFinalizeQuestion 
}) => {
  const [selectedQuestionType, setSelectedQuestionType] = useState('open_ended');
  const [newQuestionNumber, setNewQuestionNumber] = useState(1);
  const [expandedQuestion, setExpandedQuestion] = useState(null);
  const [isCreatingQuestion, setIsCreatingQuestion] = useState(false);

  const questionTypes = [
    { value: 'multiple_choice', label: 'Multiple Choice' },
    { value: 'open_ended', label: 'Open Ended' },
    { value: 'coding', label: 'Coding Challenge' },
    { value: 'true_false', label: 'True/False' },
    { value: 'short_answer', label: 'Short Answer' }
  ];

  const getNextQuestionNumber = () => {
    const existingNumbers = questions.map(q => q.question_number).sort((a, b) => a - b);
    for (let i = 1; i <= existingNumbers.length + 1; i++) {
      if (!existingNumbers.includes(i)) {
        return i;
      }
    }
    return existingNumbers.length + 1;
  };

  const handleStartNewQuestion = async () => {
    if (isCreatingQuestion) return; // Prevent double-clicks
    
    const questionNumber = getNextQuestionNumber();
    console.log('TemplateEditor: Starting question', { questionNumber, selectedQuestionType, existingQuestions: questions.length });
    
    setIsCreatingQuestion(true);
    setNewQuestionNumber(questionNumber);
    
    try {
      await onStartQuestion(questionNumber, selectedQuestionType);
    } finally {
      setIsCreatingQuestion(false);
    }
  };

  const handleFieldUpdate = (questionId, field, value) => {
    console.log('handleFieldUpdate called:', { questionId, field, value });
    onUpdateQuestion(questionId, field, value);
  };

  const renderQuestionFields = (question) => {
    const userContent = question.user_content || {};
    const isFinalized = question.status === 'finalized';
    // Temporarily allow editing for debugging
    const canEdit = !isFinalized; // TODO: Change back to: isHost && !isFinalized;
    
    // Debug logging
    console.log('TemplateEditor render debug:', {
      questionId: question.question_id,
      isHost,
      isFinalized,
      canEdit,
      userContent
    });

    switch (question.type) {
      case 'multiple_choice':
        return (
          <div className="question-fields">
            <div className="field-group">
              <label>Question Text:</label>
              <textarea
                value={userContent.question_text || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'question_text', e.target.value)}
                disabled={!canEdit}
                placeholder="Enter your multiple choice question..."
              />
            </div>
            
            <div className="field-group">
              <label>Options:</label>
              {['A', 'B', 'C', 'D'].map((letter, index) => (
                <div key={letter} className="option-input">
                  <span>{letter}.</span>
                  <input
                    type="text"
                    value={userContent.options?.[index] || ''}
                    onChange={(e) => {
                      const newOptions = [...(userContent.options || ['', '', '', ''])];
                      newOptions[index] = e.target.value;
                      handleFieldUpdate(question.question_id, 'options', newOptions);
                    }}
                    disabled={!canEdit}
                    placeholder={`Option ${letter}`}
                  />
                </div>
              ))}
            </div>

            <div className="field-group">
              <label>Correct Answer:</label>
              <select
                value={userContent.correct_answer || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'correct_answer', e.target.value)}
                disabled={!canEdit}
              >
                <option value="">Select correct answer</option>
                {(userContent.options || []).map((option, index) => (
                  <option key={index} value={option}>{['A', 'B', 'C', 'D'][index]}. {option}</option>
                ))}
              </select>
            </div>

            <div className="field-group">
              <label>Explanation:</label>
              <textarea
                value={userContent.explanation || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'explanation', e.target.value)}
                disabled={!canEdit}
                placeholder="Explain why this is the correct answer..."
              />
            </div>
          </div>
        );

      case 'coding':
        return (
          <div className="question-fields">
            <div className="field-group">
              <label>Problem Description:</label>
              <textarea
                value={userContent.question_text || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'question_text', e.target.value)}
                disabled={!canEdit}
                placeholder="Describe the coding problem..."
                rows={4}
              />
            </div>

            <div className="field-group">
              <label>Programming Language:</label>
              <select
                value={userContent.language || 'python'}
                onChange={(e) => handleFieldUpdate(question.question_id, 'language', e.target.value)}
                disabled={!canEdit}
              >
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="java">Java</option>
                <option value="cpp">C++</option>
              </select>
            </div>

            <div className="field-group">
              <label>Starter Code:</label>
              <textarea
                value={userContent.starter_code || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'starter_code', e.target.value)}
                disabled={!canEdit}
                placeholder="def solution():\n    # Write your code here\n    pass"
                rows={6}
                className="code-textarea"
              />
            </div>

            <div className="field-group">
              <label>Solution (Optional):</label>
              <textarea
                value={userContent.solution || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'solution', e.target.value)}
                disabled={!canEdit}
                placeholder="Complete solution code..."
                rows={6}
                className="code-textarea"
              />
            </div>
          </div>
        );

      case 'true_false':
        return (
          <div className="question-fields">
            <div className="field-group">
              <label>Statement:</label>
              <textarea
                value={userContent.question_text || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'question_text', e.target.value)}
                disabled={!canEdit}
                placeholder="Enter the true/false statement..."
              />
            </div>

            <div className="field-group">
              <label>Correct Answer:</label>
              <select
                value={userContent.correct_answer || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'correct_answer', e.target.value === 'true')}
                disabled={!canEdit}
              >
                <option value="">Select answer</option>
                <option value="true">True</option>
                <option value="false">False</option>
              </select>
            </div>

            <div className="field-group">
              <label>Explanation:</label>
              <textarea
                value={userContent.explanation || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'explanation', e.target.value)}
                disabled={!canEdit}
                placeholder="Explain why this statement is true or false..."
              />
            </div>
          </div>
        );

      case 'short_answer':
        return (
          <div className="question-fields">
            <div className="field-group">
              <label>Question:</label>
              <textarea
                value={userContent.question_text || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'question_text', e.target.value)}
                disabled={!canEdit}
                placeholder="Enter your short answer question..."
              />
            </div>

            <div className="field-group">
              <label>Expected Keywords (one per line):</label>
              <textarea
                value={Array.isArray(userContent.expected_keywords) ? userContent.expected_keywords.join('\n') : ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'expected_keywords', e.target.value.split('\n').filter(k => k.trim()))}
                disabled={!canEdit}
                placeholder="keyword1\nkeyword2\nkeyword3"
                rows={3}
              />
            </div>

            <div className="field-group">
              <label>Max Words:</label>
              <input
                type="number"
                value={userContent.max_words || 50}
                onChange={(e) => handleFieldUpdate(question.question_id, 'max_words', parseInt(e.target.value))}
                disabled={!canEdit}
                min="10"
                max="200"
              />
            </div>
          </div>
        );

      default: // open_ended
        return (
          <div className="question-fields">
            <div className="field-group">
              <label>Question:</label>
              <textarea
                value={userContent.question_text || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'question_text', e.target.value)}
                disabled={!canEdit}
                placeholder="Enter your open-ended question..."
                rows={3}
              />
            </div>

            <div className="field-group">
              <label>Sample Answer:</label>
              <textarea
                value={userContent.sample_answer || ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'sample_answer', e.target.value)}
                disabled={!canEdit}
                placeholder="Provide a sample answer or key points..."
                rows={4}
              />
            </div>

            <div className="field-group">
              <label>Grading Criteria (one per line):</label>
              <textarea
                value={Array.isArray(userContent.grading_criteria) ? userContent.grading_criteria.join('\n') : ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'grading_criteria', e.target.value.split('\n').filter(c => c.trim()))}
                disabled={!canEdit}
                placeholder="Demonstrates understanding of concepts\nProvides practical examples\nShows analytical thinking"
                rows={3}
              />
            </div>
          </div>
        );
    }
  };

  const sortedQuestions = [...questions].sort((a, b) => a.question_number - b.question_number);
  
  // Debug logging
  console.log('TemplateEditor render:', {
    questionsLength: questions.length,
    questions: questions.map(q => ({ id: q.question_id, number: q.question_number, status: q.status })),
    sortedQuestions: sortedQuestions.length,
    isHost,
    user: user?.username
  });

  return (
    <div className="template-editor">
      <div className="editor-header">
        <h2>Template Builder</h2>
        <div className="template-stats">
          <span>{questions.length} questions</span>
          <span>{questions.filter(q => q.status === 'finalized').length} finalized</span>
        </div>
      </div>

      {/* Add New Question Section (Host Only) */}
      {isHost && (
        <div className="add-question-section">
          <h3>Add New Question</h3>
          <div className="add-question-form">
            <select
              value={selectedQuestionType}
              onChange={(e) => setSelectedQuestionType(e.target.value)}
            >
              {questionTypes.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
            <button 
              onClick={handleStartNewQuestion}
              disabled={isCreatingQuestion}
              style={{ opacity: isCreatingQuestion ? 0.6 : 1 }}
            >
              {isCreatingQuestion ? 'Creating...' : `Start Question ${getNextQuestionNumber()}`}
            </button>
          </div>
        </div>
      )}

      {/* Questions List */}
      <div className="questions-list">
        {sortedQuestions.length === 0 ? (
          <div className="no-questions">
            <p>No questions yet. {isHost ? 'Start building your first question!' : 'Waiting for the host to add questions.'}</p>
          </div>
        ) : (
          sortedQuestions.map((question) => (
            <div 
              key={question.question_id} 
              className={`question-card ${question.status === 'finalized' ? 'finalized' : ''}`}
            >
              <div className="question-header">
                <div className="question-title">
                  <span className="question-number">Q{question.question_number}</span>
                  <span className="question-type">{question.type.replace('_', ' ')}</span>
                  <span className="question-status">{question.status || 'building'}</span>
                </div>
                <div className="question-actions">
                  <button
                    onClick={() => setExpandedQuestion(
                      expandedQuestion === question.question_id ? null : question.question_id
                    )}
                  >
                    {expandedQuestion === question.question_id ? 'Collapse' : 'Expand'}
                  </button>
                  {isHost && question.status !== 'finalized' && (
                    <button
                      onClick={() => onFinalizeQuestion(question.question_id)}
                      className="finalize-btn"
                    >
                      Finalize
                    </button>
                  )}
                </div>
              </div>

              {expandedQuestion === question.question_id && (
                <div className="question-content">
                  <div className="question-meta">
                    <p><strong>Created by:</strong> {question.created_by}</p>
                    <p><strong>Created:</strong> {new Date(question.created_at).toLocaleString()}</p>
                  </div>
                  {renderQuestionFields(question)}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Template Actions (Host Only) */}
      {isHost && questions.filter(q => q.status === 'finalized').length > 0 && (
        <div className="template-actions">
          <h3>Template Actions</h3>
          <button className="convert-btn">
            Convert to Template ({questions.filter(q => q.status === 'finalized').length} questions)
          </button>
        </div>
      )}
    </div>
  );
};

export default TemplateEditor;