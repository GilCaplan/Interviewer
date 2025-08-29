import React, { useState, useEffect, useRef, memo } from 'react';
import { getApiUrl } from '../utils/authUtils';
import './LLMChat.css';

const LLMChat = ({ session, questions, messages, user, onLLMRequest }) => {
  const [selectedQuestion, setSelectedQuestion] = useState('');
  const [selectedField, setSelectedField] = useState('all');
  const [context, setContext] = useState('');
  const [numResponses, setNumResponses] = useState(1);
  const [loading, setLoading] = useState(false);
  const [llmStatus, setLlmStatus] = useState(null);
  const chatEndRef = useRef(null);

  // Field options for different question types
  const getFieldOptions = (questionType) => {
    const baseFields = [
      { value: 'all', label: 'All Fields' },
      { value: 'question_text', label: 'Question Text' },
      { value: 'hints', label: 'Hints' }
    ];

    switch (questionType) {
      case 'multiple_choice':
        return [
          { value: 'all', label: 'All Fields' },
          { value: 'question_text', label: 'Question Text' },
          { value: 'hints', label: 'Hints' },
          { value: 'options', label: 'Answer Options' },
          { value: 'explanation', label: 'Explanation' }
        ];
      case 'coding':
        return [
          { value: 'all', label: 'All Fields' },
          { value: 'question_text', label: 'Question Text' },
          { value: 'hints', label: 'Hints' },
          { value: 'starter_code', label: 'Starter Code' },
          { value: 'solution', label: 'Solution' },
          { value: 'test_cases', label: 'Test Cases' }
        ];
      case 'true_false':
        return [
          { value: 'all', label: 'All Fields' },
          { value: 'question_text', label: 'Question Text' },
          { value: 'hints', label: 'Hints' },
          { value: 'explanation', label: 'Explanation' }
        ];
      case 'short_answer':
        return [
          { value: 'all', label: 'All Fields' },
          { value: 'question_text', label: 'Question Text' },
          { value: 'hints', label: 'Hints' },
          { value: 'expected_keywords', label: 'Expected Keywords' },
          { value: 'sample_answers', label: 'Sample Answers' }
        ];
      case 'open_ended':
        return [
          { value: 'all', label: 'All Fields' },
          { value: 'question_text', label: 'Question Text' },
          { value: 'hints', label: 'Hints' },
          { value: 'sample_answer', label: 'Sample Answer' },
          { value: 'grading_criteria', label: 'Grading Criteria' }
        ];
      default:
        return baseFields;
    }
  };

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch LLM status on component mount
  useEffect(() => {
    const fetchLLMStatus = async () => {
      try {
        const apiUrl = getApiUrl()
        const response = await fetch(`${apiUrl}/api/llm/status`);
        if (response.ok) {
          const status = await response.json();
          setLlmStatus(status);
        }
      } catch (error) {
        console.error('Failed to fetch LLM status:', error);
      }
    };

    fetchLLMStatus();
    // Refresh status every 30 seconds
    const interval = setInterval(fetchLLMStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleQuestionSpecificSuggestion = async () => {
    if (!selectedQuestion) {
      alert('Please select a question first');
      return;
    }

    setLoading(true);

    try {
      await onLLMRequest(selectedQuestion, selectedField, context, numResponses);
      setContext('');
    } catch (err) {
      console.error('Error requesting LLM suggestion:', err);
    } finally {
      setLoading(false);
    }
  };

  const selectedQuestionObj = questions.find(q => q.question_id === selectedQuestion);
  const availableFields = selectedQuestionObj ? getFieldOptions(selectedQuestionObj.type) : [];

  // Only show LLM suggestions and collaboration notes (no general chat)
  const suggestionMessages = messages.filter(m => m.type === 'llm_suggestion' || m.type === 'collaboration_note')
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  return (
    <div className="llm-chat">
      <div className="chat-header">
        <h2>🤖 AI Question Assistant</h2>
        <p>Get AI-powered suggestions to improve your interview questions</p>
        {llmStatus && (
          <div className={`llm-status ${llmStatus.gemini?.available ? 'gemini-active' : 'mock-active'}`}>
            {llmStatus.gemini?.available ? (
              <span>✅ Gemini AI Active</span>
            ) : (
              <span>⚠️ Using Mock Responses (Gemini API quota exceeded)</span>
            )}
          </div>
        )}
      </div>

      <div className="chat-container">
        {/* Suggestion Messages */}
        <div className="chat-messages">
          {suggestionMessages.length === 0 ? (
            <div className="no-messages">
              <p>🎯 Generate AI suggestions for your questions!</p>
              <p>Select a question below and get specific improvements from the AI assistant.</p>
            </div>
          ) : (
            suggestionMessages.map((message, index) => (
              <div key={message.message_id || index} className="message-group">
                {/* LLM Suggestion for specific question */}
                {message.type === 'llm_suggestion' && (
                  <div className="message llm-suggestion">
                    <div className="message-header">
                      <strong>🎯 AI Suggestion</strong>
                      <span className="suggestion-info">
                        Q{questions.find(q => q.question_id === message.question_id)?.question_number} - {message.field}
                      </span>
                      <span className="timestamp">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="message-content">
                      {message.content}
                    </div>
                  </div>
                )}

                {/* Collaboration Note */}
                {message.type === 'collaboration_note' && (
                  <div className="message collaboration-note">
                    <div className="message-header">
                      <strong>📝 {message.username}</strong>
                      <span className="timestamp">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="message-content">
                      {message.content}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Question-Specific Suggestions */}
        <div className="chat-inputs">
          <div className="chat-section">
            <h3>🎯 Generate AI Suggestions</h3>
            <div className="suggestion-form">
              <div className="form-row">
                <select
                  value={selectedQuestion}
                  onChange={(e) => {
                    setSelectedQuestion(e.target.value);
                    setSelectedField('all'); // Reset field when question changes
                  }}
                >
                  <option value="">Select a question...</option>
                  {questions.map(q => (
                    <option key={q.question_id} value={q.question_id}>
                      Q{q.question_number}: {q.type.replace('_', ' ')} 
                      {q.user_content?.question_text ? ` - ${q.user_content.question_text.slice(0, 50)}...` : ''}
                    </option>
                  ))}
                </select>

                {selectedQuestion && (
                  <select
                    value={selectedField}
                    onChange={(e) => setSelectedField(e.target.value)}
                  >
                    {availableFields.map(field => (
                      <option key={field.value} value={field.value}>
                        {field.label}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <textarea
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="Provide context for the suggestion (e.g., 'make it more challenging', 'focus on practical applications', 'suitable for beginners')..."
                rows={2}
              />

              <div className="form-row">
                <label htmlFor="numResponses">Number of responses:</label>
                <select
                  id="numResponses"
                  value={numResponses}
                  onChange={(e) => setNumResponses(parseInt(e.target.value))}
                >
                  <option value={1}>1 response</option>
                  <option value={2}>2 responses</option>
                  <option value={3}>3 responses</option>
                  <option value={4}>4 responses</option>
                  <option value={5}>5 responses</option>
                </select>
              </div>

              <button
                onClick={handleQuestionSpecificSuggestion}
                disabled={loading || !selectedQuestion}
              >
                {loading ? `Getting ${numResponses} Suggestion${numResponses > 1 ? 's' : ''}...` : `Get ${numResponses} AI Suggestion${numResponses > 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default memo(LLMChat);
