import React, { useState, useEffect, useRef, memo } from 'react';
import './LLMChat.css';

const LLMChat = ({ session, questions, messages, user, onLLMRequest }) => {
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [selectedQuestion, setSelectedQuestion] = useState('');
  const [selectedField, setSelectedField] = useState('question_text');
  const [context, setContext] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  // Field options for different question types
  const getFieldOptions = (questionType) => {
    const baseFields = [
      { value: 'question_text', label: 'Question Text' },
      { value: 'hints', label: 'Hints' }
    ];

    switch (questionType) {
      case 'multiple_choice':
        return [
          ...baseFields,
          { value: 'options', label: 'Answer Options' },
          { value: 'explanation', label: 'Explanation' }
        ];
      case 'coding':
        return [
          ...baseFields,
          { value: 'starter_code', label: 'Starter Code' },
          { value: 'solution', label: 'Solution' },
          { value: 'test_cases', label: 'Test Cases' }
        ];
      case 'true_false':
        return [
          ...baseFields,
          { value: 'explanation', label: 'Explanation' }
        ];
      case 'short_answer':
        return [
          ...baseFields,
          { value: 'expected_keywords', label: 'Expected Keywords' },
          { value: 'sample_answers', label: 'Sample Answers' }
        ];
      case 'open_ended':
        return [
          ...baseFields,
          { value: 'sample_answer', label: 'Sample Answer' },
          { value: 'grading_criteria', label: 'Grading Criteria' }
        ];
      default:
        return baseFields;
    }
  };

  // Load chat history on component mount
  useEffect(() => {
    loadChatHistory();
  }, [session.session_id]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [chatHistory, messages]);

  const loadChatHistory = async () => {
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/chat-history`, {
        headers: {
          'Authorization': `Bearer ${user.sessionToken}`
        },
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setChatHistory(data.messages || []);
      }
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  };

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleGeneralChat = async () => {
    if (!chatMessage.trim()) return;

    setLoading(true);
    const messageToSend = chatMessage.trim();
    setChatMessage('');

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/sessions/${session.session_id}/llm-chat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.sessionToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: messageToSend }),
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const data = await response.json();
      
      // Add to local chat history
      const newMessage = {
        message_id: data.message_id,
        user_message: messageToSend,
        llm_response: data.response,
        username: user.username,
        timestamp: new Date().toISOString(),
        generated_by: 'gemini'
      };

      setChatHistory(prev => [...prev, newMessage]);

    } catch (err) {
      console.error('Error sending chat message:', err);
      alert('Failed to send message: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleQuestionSpecificSuggestion = async () => {
    if (!selectedQuestion) {
      alert('Please select a question first');
      return;
    }

    setLoading(true);

    try {
      await onLLMRequest(selectedQuestion, selectedField, context);
      setContext('');
    } catch (err) {
      console.error('Error requesting LLM suggestion:', err);
    } finally {
      setLoading(false);
    }
  };

  const selectedQuestionObj = questions.find(q => q.question_id === selectedQuestion);
  const availableFields = selectedQuestionObj ? getFieldOptions(selectedQuestionObj.type) : [];

  const allMessages = [
    ...chatHistory,
    ...messages.filter(m => m.type === 'llm_suggestion' || m.type === 'collaboration_note')
  ].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  return (
    <div className="llm-chat">
      <div className="chat-header">
        <h2>LLM Assistant</h2>
        <p>Get AI-powered suggestions for your interview questions</p>
      </div>

      <div className="chat-container">
        {/* Chat Messages */}
        <div className="chat-messages">
          {allMessages.length === 0 ? (
            <div className="no-messages">
              <p>💬 Start a conversation with the AI assistant!</p>
              <p>Ask for help with question ideas, improvements, or general interview advice.</p>
            </div>
          ) : (
            allMessages.map((message, index) => (
              <div key={message.message_id || index} className="message-group">
                {/* User Message */}
                {message.user_message && (
                  <div className="message user-message">
                    <div className="message-header">
                      <strong>{message.username}</strong>
                      <span className="timestamp">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="message-content">
                      {message.user_message}
                    </div>
                  </div>
                )}

                {/* LLM Response */}
                {message.llm_response && (
                  <div className="message llm-message">
                    <div className="message-header">
                      <strong>🤖 AI Assistant</strong>
                      <span className="timestamp">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="message-content">
                      {message.llm_response}
                    </div>
                  </div>
                )}

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

        {/* Chat Input Sections */}
        <div className="chat-inputs">
          {/* General Chat */}
          <div className="chat-section">
            <h3>💬 General Chat</h3>
            <div className="chat-input-group">
              <textarea
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                placeholder="Ask the AI assistant anything about interview questions, best practices, or get general advice..."
                rows={3}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleGeneralChat();
                  }
                }}
              />
              <button 
                onClick={handleGeneralChat}
                disabled={loading || !chatMessage.trim()}
              >
                {loading ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>

          {/* Question-Specific Suggestions */}
          <div className="chat-section">
            <h3>🎯 Question-Specific Suggestions</h3>
            <div className="suggestion-form">
              <div className="form-row">
                <select
                  value={selectedQuestion}
                  onChange={(e) => {
                    setSelectedQuestion(e.target.value);
                    setSelectedField('question_text'); // Reset field when question changes
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

              <button
                onClick={handleQuestionSpecificSuggestion}
                disabled={loading || !selectedQuestion}
              >
                {loading ? 'Getting Suggestion...' : 'Get AI Suggestion'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default memo(LLMChat);