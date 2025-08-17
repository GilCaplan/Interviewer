import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// These are mock questions for demonstration until the LLM integration is complete
const mockQuestions = {
  'javascript': [
    "What's the difference between let, const and var?",
    "Explain closures in JavaScript.",
    "How does prototypal inheritance work?",
    "What is event delegation?",
    "Explain async/await and how it differs from promises.",
    "What are the different types of function declarations in JavaScript?",
    "How does the 'this' keyword work?",
    "Explain how the event loop works in JavaScript."
  ],
  'react': [
    "What are React hooks?",
    "Explain the component lifecycle.",
    "What is the virtual DOM?",
    "How does state differ from props?",
    "What is JSX?",
    "What are keys in React lists and why are they important?",
    "Explain context API and when would you use it.",
    "How would you optimize performance in a React application?"
  ],
  'system design': [
    "How would you design a URL shortening service?",
    "Design a distributed cache system.",
    "How would you approach designing Twitter's backend?",
    "Explain how you would design a notification system.",
    "Design a scalable photo-sharing application.",
    "How would you architect a real-time chat application?",
    "Design a system for ride-sharing service like Uber."
  ]
};

function LlmQuestions() {
  const { user } = useAuth();
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [generatedQuestions, setGeneratedQuestions] = useState([]);
  const [error, setError] = useState('');
  const [savedToUser, setSavedToUser] = useState(false);

  // This will be replaced with actual LLM API call later
  const generateQuestions = async () => {
    if (!prompt.trim()) {
      setError('Please enter a topic or skill to generate questions.');
      return;
    }

    setLoading(true);
    setError('');
    setSavedToUser(false);

    try {
      // Try to use the server API first
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/llm-questions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user?.sessionToken}`
        },
        body: JSON.stringify({ prompt }),
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.questions) {
          setGeneratedQuestions(data.questions);
          setLoading(false);
          return;
        }
      }

      // If API call fails, fallback to mockQuestions
      fallbackGenerateQuestions();
    } catch (error) {
      console.log('API error, using fallback:', error);
      fallbackGenerateQuestions();
    }
  };

  // Fallback mock generation function
  const fallbackGenerateQuestions = () => {
    // Simulate API call delay
    setTimeout(() => {
      // Check if we have mock questions for this topic
      const lowerPrompt = prompt.toLowerCase();
      let result = [];

      // Try to match with our mock data
      if (lowerPrompt.includes('javascript') || lowerPrompt.includes('js')) {
        result = mockQuestions.javascript;
      } else if (lowerPrompt.includes('react')) {
        result = mockQuestions.react;
      } else if (lowerPrompt.includes('system') || lowerPrompt.includes('design')) {
        result = mockQuestions['system design'];
      } else {
        // Generate generic questions based on the prompt
        result = [
          `Explain the key principles of ${prompt}.`,
          `What are the best practices when working with ${prompt}?`,
          `What are the common challenges in ${prompt} and how do you address them?`,
          `Describe your experience with ${prompt}.`,
          `How would you implement ${prompt} in a large-scale application?`,
          `What tools or frameworks do you prefer when working with ${prompt} and why?`,
          `How do you stay updated with the latest developments in ${prompt}?`,
          `How would you explain ${prompt} to someone new to the field?`
        ];
      }

      setGeneratedQuestions(result);
      setLoading(false);
    }, 1500);
  };

  const saveToUserQuestions = () => {
    if (generatedQuestions.length === 0) return;

    // Get existing questions from localStorage
    const existingQuestionsJson = localStorage.getItem(`user_questions_${user?.username}`);
    const existingQuestions = existingQuestionsJson ? JSON.parse(existingQuestionsJson) : [];

    // Convert generated questions to the user question format
    const newQuestions = generatedQuestions.map(question => ({
      question,
      answer: '',
      id: Date.now() + Math.random(),
      createdAt: new Date().toISOString(),
      category: getCategoryFromPrompt(prompt),
      source: 'AI Generated'
    }));

    // Combine and save
    const combinedQuestions = [...existingQuestions, ...newQuestions];
    localStorage.setItem(`user_questions_${user.username}`, JSON.stringify(combinedQuestions));

    setSavedToUser(true);
  };

  // Helper to determine a reasonable category based on prompt
  const getCategoryFromPrompt = (promptText) => {
    const p = promptText.toLowerCase();

    if (p.includes('javascript') || p.includes('python') || p.includes('java') ||
        p.includes('c++') || p.includes('coding') || p.includes('programming')) {
      return 'technical';
    } else if (p.includes('database') || p.includes('sql')) {
      return 'database';
    } else if (p.includes('system') || p.includes('design') || p.includes('architecture')) {
      return 'system-design';
    } else if (p.includes('web') || p.includes('frontend') || p.includes('backend')) {
      return 'web-dev';
    } else if (p.includes('behavioral') || p.includes('leadership') || p.includes('teamwork')) {
      return 'behavioral';
    } else {
      return 'general';
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    generateQuestions();
  };

  return (
    <div className="llm-questions-container">
      <h2>AI-Generated Interview Questions</h2>
      <p>Enter a topic, skill, or job role to generate relevant interview questions.</p>

      <form onSubmit={handleSubmit} className="prompt-form">
        <div className="form-group">
          <label htmlFor="prompt">What questions would you like to generate?</label>
          <input
            type="text"
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., JavaScript, System Design, React, Product Management"
            className="prompt-input"
          />
        </div>

        <button
          type="submit"
          className="generate-btn"
          disabled={loading || !prompt.trim()}
        >
          {loading ? 'Generating...' : 'Generate Questions'}
        </button>
      </form>

      {error && <div className="error-message">{error}</div>}

      {generatedQuestions.length > 0 && (
        <div className="generated-content">
          <div className="questions-header">
            <h3>Generated Questions for: {prompt}</h3>
            {!savedToUser && (
              <button
                onClick={saveToUserQuestions}
                className="save-btn"
              >
                Save to My Questions
              </button>
            )}
            {savedToUser && (
              <span className="saved-indicator">
                ✓ Saved to your questions!
              </span>
            )}
          </div>

          <ul className="generated-questions-list">
            {generatedQuestions.map((question, index) => (
              <li key={index} className="generated-question-item">
                <div className="question-number">{index + 1}</div>
                <div className="question-text">{question}</div>
              </li>
            ))}
          </ul>

          <div className="note-box">
            <p><strong>Note:</strong> These questions are for practice purposes. In an actual interview, questions may vary.</p>
          </div>
        </div>
      )}

      <div className="navigation-buttons">
        <Link to="/user-questions" className="back-button">My Questions</Link>
        <Link to="/" className="back-button">Back to Features</Link>
      </div>
    </div>
  );
}

export default LlmQuestions;