import React, { useState, useCallback, useRef, memo } from 'react';
import './TemplateEditor.css';

const TemplateEditor = ({ 
  session, 
  questions, 
  isHost, 
  user, 
  onStartQuestion, 
  onUpdateQuestion, 
  onFinalizeQuestion,
  viewingMode = 'edit'  // 'edit', 'view_only', 'suggestions_only'
}) => {
  const [selectedQuestionType, setSelectedQuestionType] = useState('open_ended');
  const [newQuestionNumber, setNewQuestionNumber] = useState(1);
  const [expandedQuestion, setExpandedQuestion] = useState(null);
  const [isCreatingQuestion, setIsCreatingQuestion] = useState(false);
  const [localQuestions, setLocalQuestions] = useState({});
  const [unsavedChanges, setUnsavedChanges] = useState({});
  const [savingQuestions, setSavingQuestions] = useState({});
  const [convertingTemplate, setConvertingTemplate] = useState(false);
  const [showNextSteps, setShowNextSteps] = useState(false);
  
  // Collaborative editing states
  const [showSuggestionModal, setShowSuggestionModal] = useState(false);
  const [suggestionField, setSuggestionField] = useState(null);
  const [suggestionText, setSuggestionText] = useState('');
  const [suggestionQuestionId, setSuggestionQuestionId] = useState(null);
  const [showNotesFor, setShowNotesFor] = useState({});
  const [fieldSuggestions, setFieldSuggestions] = useState({}); // Store pending suggestions by question ID
  const [showSuggestionHistory, setShowSuggestionHistory] = useState(false);
  const [suggestionHistory, setSuggestionHistory] = useState([]);

  const questionTypes = [
    { value: 'multiple_choice', label: 'Multiple Choice' },
    { value: 'open_ended', label: 'Open Ended' },
    { value: 'coding', label: 'Coding Challenge' },
    { value: 'true_false', label: 'True/False' },
    { value: 'short_answer', label: 'Short Answer' }
  ];

  // Permission helpers based on viewing mode
  const canEdit = isHost || viewingMode === 'edit';
  const canSuggest = isHost || viewingMode === 'suggestions_only';
  const canView = true; // Everyone can view
  const isViewOnly = !isHost && viewingMode === 'view_only';

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
    console.log('Local field update:', { questionId, field, value });
    
    // Update local state immediately for responsive UI
    setLocalQuestions(prev => ({
      ...prev,
      [`${questionId}-${field}`]: value
    }));
    
    // Mark as unsaved
    setUnsavedChanges(prev => ({
      ...prev,
      [questionId]: true
    }));
  };

  const saveQuestion = async (questionId) => {
    const questionData = questions.find(q => q.question_id === questionId);
    if (!questionData) return;

    setSavingQuestions(prev => ({ ...prev, [questionId]: true }));

    try {
      // Get all local changes for this question
      const localChanges = {};
      Object.keys(localQuestions).forEach(key => {
        if (key.startsWith(`${questionId}-`)) {
          const field = key.replace(`${questionId}-`, '');
          localChanges[field] = localQuestions[key];
        }
      });

      // Save each changed field
      for (const [field, value] of Object.entries(localChanges)) {
        console.log('Saving field:', { questionId, field, value });
        await onUpdateQuestion(questionId, field, value);
      }

      // Mark as saved
      setUnsavedChanges(prev => {
        const newState = { ...prev };
        delete newState[questionId];
        return newState;
      });

      console.log('Question saved successfully:', questionId);
    } catch (error) {
      console.error('Error saving question:', error);
      alert('Failed to save question: ' + error.message);
    } finally {
      setSavingQuestions(prev => {
        const newState = { ...prev };
        delete newState[questionId];
        return newState;
      });
    }
  };

  const removeQuestion = async (questionId) => {
    if (!window.confirm('Are you sure you want to remove this question?')) {
      return;
    }

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      let token = localStorage.getItem('token');
      if (!token) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          token = userData.sessionToken;
        }
      }

      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/${questionId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        alert('Question removed successfully');
        // The UI will update automatically via WebSocket
      } else {
        const errorData = await response.text();
        alert('Failed to remove question: ' + errorData);
      }
    } catch (error) {
      console.error('Error removing question:', error);
      alert('Failed to remove question: ' + error.message);
    }
  };

  // Collaborative editing functions
  const handleSuggestEdit = (questionId, fieldName, currentValue) => {
    setSuggestionQuestionId(questionId);
    setSuggestionField(fieldName);
    setSuggestionText(currentValue || '');
    setShowSuggestionModal(true);
  };

  const submitSuggestion = async () => {
    if (!suggestionText.trim() || !suggestionField || !suggestionQuestionId) return;

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      let token = localStorage.getItem('token');
      if (!token) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          token = userData.sessionToken;
        }
      }

      const currentValue = getFieldValue(suggestionField, suggestionQuestionId);

      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/${suggestionQuestionId}/suggest`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          field: suggestionField,
          suggested_value: suggestionText,
          current_value: currentValue
        })
      });

      if (response.ok) {
        setShowSuggestionModal(false);
        setSuggestionText('');
        setSuggestionField(null);
        setSuggestionQuestionId(null);
        alert('Suggestion submitted successfully!');
      } else {
        const errorData = await response.json();
        alert('Failed to submit suggestion: ' + (errorData.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error submitting suggestion:', error);
      alert('Failed to submit suggestion: ' + error.message);
    }
  };

  const toggleNotesDisplay = (questionId) => {
    setShowNotesFor(prev => ({
      ...prev,
      [questionId]: !prev[questionId]
    }));
  };

  const handleSuggestion = async (questionId, suggestionId, action) => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      let token = localStorage.getItem('token');
      if (!token) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          token = userData.sessionToken;
        }
      }

      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/${questionId}/suggestions/${suggestionId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action })
      });

      if (response.ok) {
        alert(`Suggestion ${action}ed successfully!`);
        // The UI will update automatically via WebSocket
      } else {
        const errorData = await response.json();
        alert(`Failed to ${action} suggestion: ` + (errorData.error || 'Unknown error'));
      }
    } catch (error) {
      console.error(`Error ${action}ing suggestion:`, error);
      alert(`Failed to ${action} suggestion: ` + error.message);
    }
  };

  // Helper function to get field value (local state takes precedence)
  const getFieldValue = (field, questionId) => {
    if (!questionId && suggestionQuestionId) {
      questionId = suggestionQuestionId;
    }
    if (!questionId) return '';
    
    const localKey = `${questionId}-${field}`;
    // Find the question data
    const question = questions.find(q => q.question_id === questionId);
    const userContent = question?.user_content || {};
    
    return localQuestions[localKey] !== undefined ? localQuestions[localKey] : (userContent[field] || '');
  };

  const clearAllQuestions = async () => {
    if (!window.confirm('Are you sure you want to clear ALL questions? This cannot be undone.')) {
      return;
    }

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      let token = localStorage.getItem('token');
      if (!token) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          token = userData.sessionToken;
        }
      }

      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/questions/clear`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        alert('All questions cleared successfully');
        // The UI will update automatically via WebSocket
      } else {
        const errorData = await response.text();
        alert('Failed to clear questions: ' + errorData);
      }
    } catch (error) {
      console.error('Error clearing questions:', error);
      alert('Failed to clear questions: ' + error.message);
    }
  };

  const resetSession = async () => {
    if (!window.confirm('Are you sure you want to reset this session to a fresh state? This will clear all questions and data.')) {
      return;
    }

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      let token = localStorage.getItem('token');
      if (!token) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          token = userData.sessionToken;
        }
      }

      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/reset`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        alert('Session reset successfully');
        // The UI will update automatically via WebSocket
      } else {
        const errorData = await response.text();
        alert('Failed to reset session: ' + errorData);
      }
    } catch (error) {
      console.error('Error resetting session:', error);
      alert('Failed to reset session: ' + error.message);
    }
  };

  const fetchSuggestionHistory = async () => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      let token = localStorage.getItem('token');
      if (!token) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          token = userData.sessionToken;
        }
      }

      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/suggestions/history`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setSuggestionHistory(data.suggestion_history || []);
        setShowSuggestionHistory(true);
      } else {
        const errorData = await response.text();
        alert('Failed to load suggestion history: ' + errorData);
      }
    } catch (error) {
      console.error('Error fetching suggestion history:', error);
      alert('Failed to load suggestion history: ' + error.message);
    }
  };

  const handleConvertToTemplate = async () => {
    const finalizedQuestions = questions.filter(q => q.status === 'finalized');
    
    if (finalizedQuestions.length === 0) {
      alert('No finalized questions available to convert to template.');
      return;
    }

    const confirmed = window.confirm(
      `Convert ${finalizedQuestions.length} finalized questions into a reusable template?\n\n` +
      'This will create a new template that can be used for future interview sessions.'
    );

    if (!confirmed) return;

    setConvertingTemplate(true);

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      let token = localStorage.getItem('token');
      if (!token) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          token = userData.sessionToken;
        }
      }

      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/convert-to-template`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          template_name: `${session.title} Template`,
          description: `Template created from session: ${session.title}`,
          subject: session.subject || 'general',
          difficulty: 'medium',
          is_public: false
        })
      });

      if (response.ok) {
        const result = await response.json();
        const templateId = result.template?.template_id;
        
        console.log('Template conversion successful:', result);
        
        // Show success message and next steps
        setShowNextSteps(true);
        
        // Scroll to the next steps section
        setTimeout(() => {
          const nextStepsElement = document.getElementById('next-steps-section');
          if (nextStepsElement) {
            nextStepsElement.scrollIntoView({ behavior: 'smooth' });
          }
        }, 100);
        
      } else {
        const errorData = await response.text();
        let errorMessage = 'Failed to convert to template';
        try {
          const errorJson = JSON.parse(errorData);
          errorMessage = errorJson.error || errorData;
        } catch (parseError) {
          errorMessage = errorData;
        }
        alert('Failed to convert to template: ' + errorMessage);
      }
    } catch (error) {
      console.error('Error converting to template:', error);
      alert('Failed to convert to template: ' + error.message);
    } finally {
      setConvertingTemplate(false);
    }
  };

  const renderQuestionFields = (question) => {
    const userContent = question.user_content || {};
    const isFinalized = question.status === 'finalized';
    const canEdit = isHost && !isFinalized;
    const canSuggest = !isHost && !isFinalized;
    
    // Helper function to get field value for this specific question
    const getFieldValueLocal = (field) => getFieldValue(field, question.question_id);

    // Helper function to render field with suggestion button for non-hosts
    const renderFieldGroup = (label, fieldName, inputElement) => {
      // Get pending suggestions for this field (only show pending ones in active display)
      const fieldSuggestions = (question.collaboration_notes || [])
        .filter(note => note.type === 'field_suggestion' && 
                       note.suggestion_data?.field === fieldName &&
                       note.suggestion_data?.status === 'pending');

      return (
        <div className="field-group">
          <div className="field-header">
            <label>{label}:</label>
            {canSuggest && (
              <button 
                className="suggest-btn"
                onClick={() => handleSuggestEdit(question.question_id, fieldName, getFieldValueLocal(fieldName))}
                title="Suggest an edit for this field"
              >
                💡 Suggest
              </button>
            )}
          </div>
          {inputElement}
          
          {/* Display pending suggestions for this field */}
          {fieldSuggestions.length > 0 && (
            <div className="field-suggestions">
              <h5>💡 Pending Suggestions ({fieldSuggestions.length}):</h5>
              {fieldSuggestions.map(note => (
                <div key={note.suggestion_data.suggestion_id} className="field-suggestion">
                  <div className="suggestion-header">
                    <span className="suggestion-author">{note.suggestion_data.author}</span>
                    <span className="suggestion-time">{new Date(note.suggestion_data.timestamp).toLocaleString()}</span>
                  </div>
                  <div className="suggestion-content">
                    <strong>Suggested value:</strong> {note.suggestion_data.suggested_value}
                  </div>
                  {isHost && (
                    <div className="suggestion-actions">
                      <button 
                        className="accept-btn"
                        onClick={() => handleSuggestion(question.question_id, note.suggestion_data.suggestion_id, 'accept')}
                        title="Accept this suggestion"
                      >
                        ✅ Accept
                      </button>
                      <button 
                        className="reject-btn"
                        onClick={() => handleSuggestion(question.question_id, note.suggestion_data.suggestion_id, 'reject')}
                        title="Reject this suggestion"
                      >
                        ❌ Reject
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      );
    };
    
    // Debug logging
    console.log('TemplateEditor render debug:', {
      questionId: question.question_id,
      isHost,
      isFinalized,
      canEdit,
      canSuggest,
      userContent
    });

    switch (question.type) {
      case 'multiple_choice':
        return (
          <div className="question-fields">
            {renderFieldGroup(
              "Question Text",
              "question_text",
              <textarea
                value={getFieldValueLocal('question_text')}
                onChange={(e) => handleFieldUpdate(question.question_id, 'question_text', e.target.value)}
                disabled={!canEdit}
                placeholder="Enter your multiple choice question..."
              />
            )}
            
            <div className="field-group">
              <div className="field-header">
                <label>Options:</label>
                {canSuggest && (
                  <button 
                    className="suggest-btn"
                    onClick={() => {
                      const currentOptions = getFieldValueLocal('options');
                      const optionsText = Array.isArray(currentOptions) ? currentOptions.join('\n') : '';
                      handleSuggestEdit(question.question_id, 'options', optionsText);
                    }}
                    title="Suggest changes to all options"
                  >
                    💡 Suggest
                  </button>
                )}
              </div>
              {['A', 'B', 'C', 'D'].map((letter, index) => (
                <div key={letter} className="option-input">
                  <span>{letter}.</span>
                  <input
                    type="text"
                    value={(() => {
                      const options = getFieldValueLocal('options');
                      return Array.isArray(options) ? (options[index] || '') : '';
                    })()}
                    onChange={(e) => {
                      const currentOptions = getFieldValueLocal('options');
                      const newOptions = Array.isArray(currentOptions) 
                        ? [...currentOptions] 
                        : ['', '', '', ''];
                      newOptions[index] = e.target.value;
                      handleFieldUpdate(question.question_id, 'options', newOptions);
                    }}
                    disabled={!canEdit}
                    placeholder={`Option ${letter}`}
                  />
                </div>
              ))}
            </div>

            {renderFieldGroup(
              "Correct Answer",
              "correct_answer",
              <select
                value={getFieldValueLocal('correct_answer')}
                onChange={(e) => handleFieldUpdate(question.question_id, 'correct_answer', e.target.value)}
                disabled={!canEdit}
              >
                <option value="">Select correct answer</option>
                {(() => {
                  const options = getFieldValueLocal('options');
                  return Array.isArray(options) ? options.map((option, index) => (
                    <option key={index} value={option}>{['A', 'B', 'C', 'D'][index]}. {option}</option>
                  )) : [];
                })()}
              </select>
            )}

            {renderFieldGroup(
              "Explanation",
              "explanation",
              <textarea
                value={getFieldValueLocal('explanation')}
                onChange={(e) => handleFieldUpdate(question.question_id, 'explanation', e.target.value)}
                disabled={!canEdit}
                placeholder="Explain why this is the correct answer..."
              />
            )}
          </div>
        );

      case 'coding':
        return (
          <div className="question-fields">
            {renderFieldGroup(
              "Problem Description",
              "question_text",
              <textarea
                value={getFieldValueLocal('question_text')}
                onChange={(e) => handleFieldUpdate(question.question_id, 'question_text', e.target.value)}
                disabled={!canEdit}
                placeholder="Describe the coding problem..."
                rows={4}
              />
            )}

            {renderFieldGroup(
              "Programming Language",
              "language",
              <select
                value={getFieldValueLocal('language') || 'python'}
                onChange={(e) => handleFieldUpdate(question.question_id, 'language', e.target.value)}
                disabled={!canEdit}
              >
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="java">Java</option>
                <option value="cpp">C++</option>
              </select>
            )}

            {renderFieldGroup(
              "Starter Code",
              "starter_code",
              <textarea
                value={getFieldValueLocal('starter_code')}
                onChange={(e) => handleFieldUpdate(question.question_id, 'starter_code', e.target.value)}
                disabled={!canEdit}
                placeholder="def solution():\n    # Write your code here\n    pass"
                rows={6}
                className="code-textarea"
              />
            )}

            {renderFieldGroup(
              "Solution (Optional)",
              "solution",
              <textarea
                value={getFieldValueLocal('solution')}
                onChange={(e) => handleFieldUpdate(question.question_id, 'solution', e.target.value)}
                disabled={!canEdit}
                placeholder="Complete solution code..."
                rows={6}
                className="code-textarea"
              />
            )}
          </div>
        );

      case 'true_false':
        return (
          <div className="question-fields">
            {renderFieldGroup(
              "Statement",
              "question_text",
              <textarea
                value={getFieldValueLocal('question_text')}
                onChange={(e) => handleFieldUpdate(question.question_id, 'question_text', e.target.value)}
                disabled={!canEdit}
                placeholder="Enter the true/false statement..."
              />
            )}

            {renderFieldGroup(
              "Correct Answer",
              "correct_answer",
              <select
                value={getFieldValueLocal('correct_answer') === true ? 'true' : getFieldValueLocal('correct_answer') === false ? 'false' : ''}
                onChange={(e) => handleFieldUpdate(question.question_id, 'correct_answer', e.target.value === 'true')}
                disabled={!canEdit}
              >
                <option value="">Select answer</option>
                <option value="true">True</option>
                <option value="false">False</option>
              </select>
            )}

            {renderFieldGroup(
              "Explanation",
              "explanation",
              <textarea
                value={getFieldValueLocal('explanation')}
                onChange={(e) => handleFieldUpdate(question.question_id, 'explanation', e.target.value)}
                disabled={!canEdit}
                placeholder="Explain why this statement is true or false..."
              />
            )}
          </div>
        );

      case 'short_answer':
        return (
          <div className="question-fields">
            {renderFieldGroup(
              "Question",
              "question_text",
              <textarea
                value={getFieldValueLocal('question_text')}
                onChange={(e) => handleFieldUpdate(question.question_id, 'question_text', e.target.value)}
                disabled={!canEdit}
                placeholder="Enter your short answer question..."
              />
            )}

            {renderFieldGroup(
              "Expected Keywords (one per line)",
              "expected_keywords",
              <textarea
                value={(() => {
                  const keywords = getFieldValueLocal('expected_keywords');
                  return Array.isArray(keywords) ? keywords.join('\n') : '';
                })()}
                onChange={(e) => handleFieldUpdate(question.question_id, 'expected_keywords', e.target.value.split('\n').filter(k => k.trim()))}
                disabled={!canEdit}
                placeholder="keyword1\nkeyword2\nkeyword3"
                rows={3}
              />
            )}

            {renderFieldGroup(
              "Max Words",
              "max_words",
              <input
                type="number"
                value={getFieldValueLocal('max_words') || 50}
                onChange={(e) => handleFieldUpdate(question.question_id, 'max_words', parseInt(e.target.value))}
                disabled={!canEdit}
                min="10"
                max="200"
              />
            )}
          </div>
        );

      default: // open_ended
        return (
          <div className="question-fields">
            {renderFieldGroup(
              "Question",
              "question_text",
              <textarea
                value={getFieldValueLocal('question_text')}
                onChange={(e) => handleFieldUpdate(question.question_id, 'question_text', e.target.value)}
                disabled={!canEdit}
                placeholder="Enter your open-ended question..."
                rows={3}
              />
            )}

            {renderFieldGroup(
              "Sample Answer",
              "sample_answer",
              <textarea
                value={getFieldValueLocal('sample_answer')}
                onChange={(e) => handleFieldUpdate(question.question_id, 'sample_answer', e.target.value)}
                disabled={!canEdit}
                placeholder="Provide a sample answer or key points..."
                rows={4}
              />
            )}

            {renderFieldGroup(
              "Grading Criteria (one per line)",
              "grading_criteria",
              <textarea
                value={(() => {
                  const criteria = getFieldValueLocal('grading_criteria');
                  return Array.isArray(criteria) ? criteria.join('\n') : '';
                })()}
                onChange={(e) => handleFieldUpdate(question.question_id, 'grading_criteria', e.target.value.split('\n').filter(c => c.trim()))}
                disabled={!canEdit}
                placeholder="Demonstrates understanding of concepts\nProvides practical examples\nShows analytical thinking"
                rows={3}
              />
            )}
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

      {/* Viewing Mode Indicator */}
      {!isHost && (
        <div className={`viewing-mode-notice ${viewingMode}`}>
          {viewingMode === 'edit' && (
            <div className="mode-info">
              <span className="mode-icon">✏️</span>
              <div className="mode-text">
                <strong>Full Edit Access</strong>
                <p>You can create and edit questions directly</p>
              </div>
            </div>
          )}
          {viewingMode === 'suggestions_only' && (
            <div className="mode-info">
              <span className="mode-icon">💡</span>
              <div className="mode-text">
                <strong>Suggestions Mode</strong>
                <p>You can suggest changes that the host can approve or reject</p>
              </div>
            </div>
          )}
          {viewingMode === 'view_only' && (
            <div className="mode-info">
              <span className="mode-icon">👁️</span>
              <div className="mode-text">
                <strong>View Only Mode</strong>
                <p>You can view questions but cannot make changes</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Add New Question Section */}
      {canEdit && (
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
                  {isHost && question.status !== 'finalized' && unsavedChanges[question.question_id] && (
                    <button
                      onClick={() => saveQuestion(question.question_id)}
                      className="save-btn"
                      disabled={savingQuestions[question.question_id]}
                      style={{ 
                        backgroundColor: '#4CAF50',
                        opacity: savingQuestions[question.question_id] ? 0.6 : 1 
                      }}
                    >
                      {savingQuestions[question.question_id] ? 'Saving...' : 'Save'}
                    </button>
                  )}
                  {isHost && question.status !== 'finalized' && (
                    <button
                      onClick={async () => {
                        // Save any unsaved changes first
                        if (unsavedChanges[question.question_id]) {
                          await saveQuestion(question.question_id);
                        }
                        // Then finalize
                        onFinalizeQuestion(question.question_id);
                      }}
                      className="finalize-btn"
                    >
                      Finalize
                    </button>
                  )}
                  {isHost && (
                    <button
                      onClick={() => removeQuestion(question.question_id)}
                      className="remove-btn"
                      style={{ 
                        backgroundColor: '#f44336',
                        color: 'white',
                        marginLeft: '5px' 
                      }}
                    >
                      Remove
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

      {/* Debug Section (Host Only) */}
      {isHost && (
        <div className="debug-section" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f0f0f0', borderRadius: '5px' }}>
          <h3>Debug Info</h3>
          <button 
            onClick={async () => {
              try {
                const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
                let token = localStorage.getItem('token');
                if (!token) {
                  const storedUser = localStorage.getItem('user');
                  if (storedUser) {
                    const userData = JSON.parse(storedUser);
                    token = userData.sessionToken;
                  }
                }
                
                const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/debug`, {
                  headers: { 'Authorization': `Bearer ${token}` }
                });
                
                if (response.ok) {
                  const data = await response.json();
                  console.log('=== BACKEND DEBUG INFO ===');
                  console.log('Backend questions in queue:', data.debug.queue_question_ids);  
                  console.log('Backend questions ready:', data.debug.ready_question_ids);
                  console.log('Full backend data:', data.debug);
                  
                  console.log('=== FRONTEND STATE ===');
                  console.log('Frontend questions:', questions.map(q => ({ id: q.question_id, number: q.question_number, status: q.status })));
                  
                  alert(`Backend has ${data.debug.questions_in_queue} in queue, ${data.debug.questions_ready} ready. Check console for details.`);
                } else {
                  alert('Failed to get debug info');
                }
              } catch (error) {
                console.error('Debug error:', error);
                alert('Debug failed: ' + error.message);
              }
            }}
            style={{ backgroundColor: '#2196F3', color: 'white', padding: '8px 15px', border: 'none', borderRadius: '4px' }}
          >
            🐛 Debug Backend State
          </button>
        </div>
      )}

      {/* Session Management (Host Only) */}
      {isHost && (
        <div className="session-management" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#fff3cd', borderRadius: '5px', border: '1px solid #ffeaa7' }}>
          <h3>Session Management</h3>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {questions.length > 0 && (
              <button 
                onClick={clearAllQuestions}
                style={{ 
                  backgroundColor: '#ffc107', 
                  color: 'black', 
                  padding: '8px 15px', 
                  border: 'none', 
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                🗑️ Clear All Questions
              </button>
            )}
            <button 
              onClick={resetSession}
              style={{ 
                backgroundColor: '#dc3545', 
                color: 'white', 
                padding: '8px 15px', 
                border: 'none', 
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              🔄 Reset Session
            </button>
            <button 
              onClick={fetchSuggestionHistory}
              style={{ 
                backgroundColor: '#17a2b8', 
                color: 'white', 
                padding: '8px 15px', 
                border: 'none', 
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              📜 View Suggestion History
            </button>
          </div>
          <p style={{ fontSize: '12px', color: '#856404', marginTop: '10px' }}>
            Use these options to start fresh or clean up unwanted questions.
          </p>
        </div>
      )}

      {/* Template Actions (Host Only) */}
      {isHost && questions.filter(q => q.status === 'finalized').length > 0 && !showNextSteps && (
        <div className="template-actions" style={{ marginTop: '20px', padding: '20px', backgroundColor: '#e8f5e8', borderRadius: '8px', border: '2px solid #4CAF50' }}>
          <h3 style={{ color: '#2e7d32', marginBottom: '15px' }}>🎯 Template Ready!</h3>
          <p style={{ color: '#2e7d32', marginBottom: '15px' }}>
            You have {questions.filter(q => q.status === 'finalized').length} finalized questions ready to convert into a reusable template.
          </p>
          <button 
            className="convert-btn"
            onClick={handleConvertToTemplate}
            disabled={convertingTemplate}
            style={{
              backgroundColor: convertingTemplate ? '#ccc' : '#4CAF50',
              color: 'white',
              padding: '12px 24px',
              border: 'none',
              borderRadius: '6px',
              fontSize: '16px',
              fontWeight: 'bold',
              cursor: convertingTemplate ? 'not-allowed' : 'pointer',
              opacity: convertingTemplate ? 0.6 : 1
            }}
          >
            {convertingTemplate ? '🔄 Converting...' : `🔄 Convert to Template (${questions.filter(q => q.status === 'finalized').length} questions)`}
          </button>
        </div>
      )}

      {/* Next Steps Section */}
      {showNextSteps && (
        <div id="next-steps-section" style={{ marginTop: '20px', padding: '25px', backgroundColor: '#f0f8ff', borderRadius: '10px', border: '3px solid #2196F3' }}>
          <h2 style={{ color: '#1976d2', marginBottom: '20px', textAlign: 'center' }}>🎉 Template Created Successfully!</h2>
          <p style={{ color: '#1976d2', marginBottom: '25px', textAlign: 'center', fontSize: '16px' }}>
            Your template has been saved and is now available for future interview sessions.
          </p>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', alignItems: 'center' }}>
            <h3 style={{ color: '#1976d2', marginBottom: '10px' }}>What would you like to do next?</h3>
            
            <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap', justifyContent: 'center' }}>
              <button 
                onClick={() => {
                  if (window.confirm('Close this session? You can always create new sessions from your templates.')) {
                    window.location.href = '/dashboard';
                  }
                }}
                style={{
                  backgroundColor: '#2196F3',
                  color: 'white',
                  padding: '12px 20px',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
              >
                🏠 Go to Dashboard
              </button>
              
              <button 
                onClick={() => {
                  window.location.href = '/templates';
                }}
                style={{
                  backgroundColor: '#FF9800',
                  color: 'white',
                  padding: '12px 20px',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
              >
                📚 View Templates Gallery
              </button>
              
              <button 
                onClick={resetSession}
                style={{
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  padding: '12px 20px',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
              >
                ➕ Create New Template
              </button>
              
              <button 
                onClick={() => {
                  window.location.href = '/sessions/simulate';
                }}
                style={{
                  backgroundColor: '#9C27B0',
                  color: 'white',
                  padding: '12px 20px',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
              >
                🎭 Start Mock Interview
              </button>
            </div>
            
            <button 
              onClick={() => setShowNextSteps(false)}
              style={{
                backgroundColor: '#757575',
                color: 'white',
                padding: '8px 16px',
                border: 'none',
                borderRadius: '4px',
                fontSize: '12px',
                cursor: 'pointer',
                marginTop: '10px'
              }}
            >
              ✕ Continue Working on Session
            </button>
          </div>
        </div>
      )}

      {/* Collaborative Suggestion Modal */}
      {showSuggestionModal && (
        <div className="modal-overlay" onClick={() => setShowSuggestionModal(false)}>
          <div className="suggestion-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>💡 Suggest Edit for {suggestionField}</h3>
              <button 
                className="close-btn"
                onClick={() => setShowSuggestionModal(false)}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <p>Current value:</p>
              <div className="current-value">
                {getFieldValue(suggestionField, suggestionQuestionId) || '<empty>'}
              </div>
              <p>Your suggestion:</p>
              <textarea
                value={suggestionText}
                onChange={(e) => setSuggestionText(e.target.value)}
                placeholder="Enter your suggested change..."
                rows={4}
                className="suggestion-textarea"
              />
            </div>
            <div className="modal-footer">
              <button 
                className="cancel-btn"
                onClick={() => setShowSuggestionModal(false)}
              >
                Cancel
              </button>
              <button 
                className="submit-suggestion-btn"
                onClick={submitSuggestion}
                disabled={!suggestionText.trim()}
              >
                Submit Suggestion
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Suggestion History Modal */}
      {showSuggestionHistory && (
        <div className="modal-overlay" onClick={() => setShowSuggestionHistory(false)}>
          <div className="suggestion-history-modal" onClick={(e) => e.stopPropagation()}>
            <div className="suggestion-history-header">
              <div className="modal-title-section">
                <h3>📜 Suggestion History</h3>
                <p className="modal-subtitle">Review all collaboration suggestions and their status</p>
              </div>
              <button 
                className="modal-close-btn"
                onClick={() => setShowSuggestionHistory(false)}
                title="Close modal"
              >
                ✕
              </button>
            </div>
            
            <div className="suggestion-history-content">
              {suggestionHistory.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">📝</div>
                  <h4>No suggestion history found</h4>
                  <p>Suggestions will appear here as team members collaborate on questions</p>
                </div>
              ) : (
                <>
                  <div className="suggestion-summary">
                    <div className="summary-card">
                      <div className="summary-number">{suggestionHistory.length}</div>
                      <div className="summary-label">Total Suggestions</div>
                    </div>
                    <div className="summary-card accepted">
                      <div className="summary-number">{suggestionHistory.filter(s => s.status === 'accept').length}</div>
                      <div className="summary-label">Accepted</div>
                    </div>
                    <div className="summary-card rejected">
                      <div className="summary-number">{suggestionHistory.filter(s => s.status === 'reject').length}</div>
                      <div className="summary-label">Rejected</div>
                    </div>
                  </div>
                  
                  <div className="suggestion-history-list">
                    {suggestionHistory.map((suggestion, index) => (
                      <div key={suggestion.suggestion_id} className="history-item">
                        <div className="history-item-header">
                          <div className="question-info">
                            <span className="question-number">Q{suggestion.question_number}</span>
                            <span className="field-name">{suggestion.field}</span>
                          </div>
                          <div className="status-and-date">
                            <span className={`status-badge ${suggestion.status === 'accept' ? 'accepted' : 'rejected'}`}>
                              {suggestion.status === 'accept' ? '✅ Accepted' : '❌ Rejected'}
                            </span>
                            <span className="history-date">
                              {new Date(suggestion.handled_at).toLocaleString()}
                            </span>
                          </div>
                        </div>
                        
                        <div className="history-item-content">
                          <div className="suggestion-details">
                            <div className="detail-row">
                              <span className="detail-label">Suggested by:</span>
                              <span className="detail-value">{suggestion.author}</span>
                            </div>
                            <div className="detail-row">
                              <span className="detail-label">Handled by:</span>
                              <span className="detail-value">{suggestion.handled_by}</span>
                            </div>
                          </div>
                          
                          <div className="value-comparison">
                            <div className="suggested-section">
                              <div className="value-label">Suggested Value:</div>
                              <div className="value-content suggested">{suggestion.suggested_value}</div>
                            </div>
                            {suggestion.current_value && (
                              <div className="previous-section">
                                <div className="value-label">Previous Value:</div>
                                <div className="value-content previous">{suggestion.current_value}</div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
            
            <div className="suggestion-history-footer">
              <button 
                className="footer-close-btn"
                onClick={() => setShowSuggestionHistory(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Display Notes and Suggestions for each question */}
      {questions.map(question => {
        const hasNotes = question.collaboration_notes && question.collaboration_notes.length > 0;
        const hasLLMSuggestions = question.llm_suggestions && question.llm_suggestions.length > 0;
        
        if (!hasNotes && !hasLLMSuggestions) return null;
        
        return (
          <div key={`notes-${question.question_id}`} className="question-collaboration">
            <div className="collaboration-header">
              <h4>Q{question.question_number} - Collaboration & Suggestions</h4>
              <button 
                className="toggle-notes-btn"
                onClick={() => toggleNotesDisplay(question.question_id)}
              >
                {showNotesFor[question.question_id] ? 'Hide' : 'Show'} ({hasNotes ? question.collaboration_notes.length : 0} notes, {hasLLMSuggestions ? question.llm_suggestions.length : 0} AI suggestions)
              </button>
            </div>
            
            {showNotesFor[question.question_id] && (
              <div className="collaboration-content">
                {hasNotes && (
                  <div className="collaboration-notes">
                    <h5>💬 User Suggestions & Notes</h5>
                    {question.collaboration_notes.map(note => (
                      <div key={note.note_id} className="collaboration-note">
                        <div className="note-header">
                          <span className="note-author">{note.author}</span>
                          <span className="note-time">{new Date(note.timestamp).toLocaleString()}</span>
                          {note.field_reference && (
                            <span className="note-field">Field: {note.field_reference}</span>
                          )}
                        </div>
                        <div className="note-content">{note.note}</div>
                      </div>
                    ))}
                  </div>
                )}
                
                {hasLLMSuggestions && (
                  <div className="llm-suggestions">
                    <h5>🤖 AI Suggestions</h5>
                    {question.llm_suggestions.map(suggestion => (
                      <div key={suggestion.suggestion_id} className="llm-suggestion">
                        <div className="suggestion-header">
                          <span className="suggestion-field">Field: {suggestion.field}</span>
                          <span className="suggestion-time">{new Date(suggestion.timestamp).toLocaleString()}</span>
                        </div>
                        <div className="suggestion-content">{suggestion.suggestion}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default memo(TemplateEditor);