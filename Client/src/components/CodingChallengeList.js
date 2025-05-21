import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './CodingChallengeList.css';

function CodingChallengeList() {
  const { user } = useAuth();
  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({
    search: '',
    difficulty: 'all',
    tags: []
  });
  const [showCreateForm, setShowCreateForm] = useState(false);

  useEffect(() => {
    const fetchChallenges = async () => {
      try {
        // For development, use mock data
        if (process.env.NODE_ENV === 'development' && !process.env.REACT_APP_USE_API) {
          setChallenges(getMockChallenges());
          setLoading(false);
          return;
        }

        // For production, fetch from API
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
        const response = await fetch(`${apiUrl}/api/coding-challenges`, {
          headers: {
            'Authorization': `Bearer ${user?.sessionToken}`
          },
          credentials: 'include'
        });

        if (!response.ok) {
          throw new Error('Failed to fetch challenges');
        }

        const data = await response.json();
        setChallenges(data.challenges);
      } catch (error) {
        console.error('Error fetching challenges:', error);
        // Fallback to mock data
        setChallenges(getMockChallenges());
      } finally {
        setLoading(false);
      }
    };

    fetchChallenges();
  }, [user]);

  const filteredChallenges = challenges.filter(challenge => {
    // Apply search filter
    const matchesSearch = challenge.title.toLowerCase().includes(filter.search.toLowerCase());

    // Apply difficulty filter
    const matchesDifficulty = filter.difficulty === 'all' ||
      challenge.difficulty.toLowerCase() === filter.difficulty.toLowerCase();

    // Apply tags filter (if any tags are selected)
    const matchesTags = filter.tags.length === 0 ||
      filter.tags.some(tag => challenge.tags.includes(tag));

    return matchesSearch && matchesDifficulty && matchesTags;
  });

  const handleSearchChange = (e) => {
    setFilter({ ...filter, search: e.target.value });
  };

  const handleDifficultyChange = (e) => {
    setFilter({ ...filter, difficulty: e.target.value });
  };

  const handleTagClick = (tag) => {
    if (filter.tags.includes(tag)) {
      setFilter({ ...filter, tags: filter.tags.filter(t => t !== tag) });
    } else {
      setFilter({ ...filter, tags: [...filter.tags, tag] });
    }
  };

  if (loading) {
    return <div className="loading">Loading challenges...</div>;
  }

  // Extract all unique tags from challenges
  const allTags = [...new Set(challenges.flatMap(challenge => challenge.tags))];

  return (
    <div className="coding-challenges-container">
      <div className="challenges-header">
        <h2>Programming Challenges</h2>
        <p>Sharpen your coding skills with these programming challenges. Practice algorithms, data structures, and problem-solving.</p>
      </div>

      <div className="challenges-controls">
        <div className="filter-section">
          <div className="search-box">
            <input
              type="text"
              placeholder="Search challenges..."
              value={filter.search}
              onChange={handleSearchChange}
              className="search-input"
            />
          </div>

          <div className="filter-options">
            <select
              value={filter.difficulty}
              onChange={handleDifficultyChange}
              className="difficulty-filter"
            >
              <option value="all">All Difficulties</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>

        <button
          className="create-button"
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          {showCreateForm ? 'Cancel' : 'Create Challenge'}
        </button>
      </div>

      {filter.tags.length > 0 && (
        <div className="active-filters">
          <span>Active filters:</span>
          {filter.tags.map(tag => (
            <button
              key={tag}
              className="filter-tag active"
              onClick={() => handleTagClick(tag)}
            >
              {tag} ×
            </button>
          ))}
          <button
            className="clear-filters"
            onClick={() => setFilter({ ...filter, tags: [] })}
          >
            Clear all
          </button>
        </div>
      )}

      <div className="tags-section">
        <h3>Filter by Tags:</h3>
        <div className="tags-container">
          {allTags.map(tag => (
            <button
              key={tag}
              className={`filter-tag ${filter.tags.includes(tag) ? 'active' : ''}`}
              onClick={() => handleTagClick(tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {showCreateForm && (
        <CreateChallengeForm
          onClose={() => setShowCreateForm(false)}
          onSuccess={(newChallenge) => {
            setChallenges([...challenges, newChallenge]);
            setShowCreateForm(false);
          }}
          user={user}
        />
      )}

      <div className="challenges-list">
        {filteredChallenges.length === 0 ? (
          <div className="no-challenges">
            <p>No challenges match your current filters.</p>
          </div>
        ) : (
          filteredChallenges.map(challenge => (
            <Link to={`/coding-challenges/${challenge.id}`} key={challenge.id} className="challenge-card-link">
              <div className="challenge-card">
                <div className="challenge-card-header">
                  <h3>{challenge.title}</h3>
                  <span className={`difficulty difficulty-${challenge.difficulty.toLowerCase()}`}>
                    {challenge.difficulty}
                  </span>
                </div>

                <div className="challenge-card-tags">
                  {challenge.tags.map((tag, index) => (
                    <span key={index} className="challenge-tag">{tag}</span>
                  ))}
                </div>

                <div className="challenge-card-completion">
                  {challenge.completion ? (
                    <div className="completion-badge completed">
                      <span className="check-icon">✓</span> Completed
                    </div>
                  ) : (
                    <div className="completion-badge">Not attempted</div>
                  )}
                </div>
              </div>
            </Link>
          ))
        )}
      </div>

      <div className="navigation-buttons">
        <Link to="/" className="back-button">Back to Features</Link>
      </div>
    </div>
  );
}

// Create Challenge Form Component
function CreateChallengeForm({ onClose, onSuccess, user }) {
  const [formData, setFormData] = useState({
    title: '',
    difficulty: 'easy',
    tags: [],
    description: '',
    starterCode: `def solution(input):\n    # Your solution here\n    pass\n`,
    examples: [{ input: '', output: '', explanation: '' }],
    constraints: [''],
    testCases: [{ functionName: 'solution', input: '', expectedOutput: '' }]
  });
  const [tagInput, setTagInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  const handleTagInputChange = (e) => {
    setTagInput(e.target.value);
  };

  const handleTagInputKeyDown = (e) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault();
      if (!formData.tags.includes(tagInput.trim())) {
        setFormData({
          ...formData,
          tags: [...formData.tags, tagInput.trim()]
        });
      }
      setTagInput('');
    }
  };

  const removeTag = (tagToRemove) => {
    setFormData({
      ...formData,
      tags: formData.tags.filter(tag => tag !== tagToRemove)
    });
  };

  const addExample = () => {
    setFormData({
      ...formData,
      examples: [...formData.examples, { input: '', output: '', explanation: '' }]
    });
  };

  const updateExample = (index, field, value) => {
    const updatedExamples = [...formData.examples];
    updatedExamples[index] = { ...updatedExamples[index], [field]: value };
    setFormData({
      ...formData,
      examples: updatedExamples
    });
  };

  const removeExample = (index) => {
    if (formData.examples.length <= 1) return;
    setFormData({
      ...formData,
      examples: formData.examples.filter((_, i) => i !== index)
    });
  };

  const addConstraint = () => {
    setFormData({
      ...formData,
      constraints: [...formData.constraints, '']
    });
  };

  const updateConstraint = (index, value) => {
    const updatedConstraints = [...formData.constraints];
    updatedConstraints[index] = value;
    setFormData({
      ...formData,
      constraints: updatedConstraints
    });
  };

  const removeConstraint = (index) => {
    if (formData.constraints.length <= 1) return;
    setFormData({
      ...formData,
      constraints: formData.constraints.filter((_, i) => i !== index)
    });
  };

  const addTestCase = () => {
    setFormData({
      ...formData,
      testCases: [...formData.testCases, { functionName: 'solution', input: '', expectedOutput: '' }]
    });
  };

  const updateTestCase = (index, field, value) => {
    const updatedTestCases = [...formData.testCases];
    updatedTestCases[index] = { ...updatedTestCases[index], [field]: value };
    setFormData({
      ...formData,
      testCases: updatedTestCases
    });
  };

  const removeTestCase = (index) => {
    if (formData.testCases.length <= 1) return;
    setFormData({
      ...formData,
      testCases: formData.testCases.filter((_, i) => i !== index)
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      // Validation
      if (!formData.title.trim()) {
        throw new Error('Title is required');
      }
      if (!formData.description.trim()) {
        throw new Error('Description is required');
      }
      if (formData.testCases.some(tc => !tc.input || !tc.expectedOutput)) {
        throw new Error('All test cases must have input and expected output');
      }

      // In development mode without API
      if (process.env.NODE_ENV === 'development' && !process.env.REACT_APP_USE_API) {
        // Create a mock challenge
        const newChallenge = {
          ...formData,
          id: Date.now().toString(),
          author: user?.username || 'Anonymous',
          createdAt: new Date().toISOString(),
          tags: formData.tags.length > 0 ? formData.tags : ['General'],
          completion: false
        };

        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        onSuccess(newChallenge);
        return;
      }

      // For production with API
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/coding-challenges`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user?.sessionToken}`
        },
        body: JSON.stringify(formData),
        credentials: 'include'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to create challenge');
      }

      const data = await response.json();
      onSuccess(data.challenge);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="create-challenge-form">
      <h3>Create a New Challenge</h3>

      {error && <div className="error-message">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="title">Title</label>
          <input
            type="text"
            id="title"
            name="title"
            value={formData.title}
            onChange={handleChange}
            placeholder="Challenge title"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="difficulty">Difficulty</label>
          <select
            id="difficulty"
            name="difficulty"
            value={formData.difficulty}
            onChange={handleChange}
          >
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="tags">Tags</label>
          <div className="tag-input-container">
            <input
              type="text"
              id="tags"
              value={tagInput}
              onChange={handleTagInputChange}
              onKeyDown={handleTagInputKeyDown}
              placeholder="Add tags and press Enter"
            />
          </div>

          {formData.tags.length > 0 && (
            <div className="tags-display">
              {formData.tags.map(tag => (
                <span key={tag} className="tag-item">
                  {tag}
                  <button type="button" onClick={() => removeTag(tag)} className="remove-tag">×</button>
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={5}
            placeholder="Describe the challenge in detail. You can use markdown."
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="starterCode">Starter Code</label>
          <textarea
            id="starterCode"
            name="starterCode"
            value={formData.starterCode}
            onChange={handleChange}
            rows={8}
            placeholder="Provide starter code for the challenge"
          />
        </div>

        <div className="form-group">
          <label>Examples</label>
          {formData.examples.map((example, index) => (
            <div key={index} className="example-item">
              <div className="example-header">
                <span>Example {index + 1}</span>
                <button
                  type="button"
                  onClick={() => removeExample(index)}
                  className="remove-btn"
                  disabled={formData.examples.length <= 1}
                >
                  Remove
                </button>
              </div>

              <div className="example-fields">
                <div className="form-group">
                  <label htmlFor={`example-input-${index}`}>Input</label>
                  <textarea
                    id={`example-input-${index}`}
                    value={example.input}
                    onChange={(e) => updateExample(index, 'input', e.target.value)}
                    rows={2}
                    placeholder="Example input"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor={`example-output-${index}`}>Output</label>
                  <textarea
                    id={`example-output-${index}`}
                    value={example.output}
                    onChange={(e) => updateExample(index, 'output', e.target.value)}
                    rows={2}
                    placeholder="Expected output"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor={`example-explanation-${index}`}>Explanation (optional)</label>
                  <textarea
                    id={`example-explanation-${index}`}
                    value={example.explanation}
                    onChange={(e) => updateExample(index, 'explanation', e.target.value)}
                    rows={2}
                    placeholder="Explanation of the example"
                  />
                </div>
              </div>
            </div>
          ))}

          <button type="button" onClick={addExample} className="add-btn">
            Add Example
          </button>
        </div>

        <div className="form-group">
          <label>Constraints</label>
          {formData.constraints.map((constraint, index) => (
            <div key={index} className="constraint-item">
              <input
                type="text"
                value={constraint}
                onChange={(e) => updateConstraint(index, e.target.value)}
                placeholder="Add a constraint (e.g., 1 <= n <= 10^5)"
              />
              <button
                type="button"
                onClick={() => removeConstraint(index)}
                className="remove-btn"
                disabled={formData.constraints.length <= 1}
              >
                Remove
              </button>
            </div>
          ))}

          <button type="button" onClick={addConstraint} className="add-btn">
            Add Constraint
          </button>
        </div>

        <div className="form-group">
          <label>Test Cases</label>
          {formData.testCases.map((testCase, index) => (
            <div key={index} className="test-case-item">
              <div className="test-case-header">
                <span>Test Case {index + 1}</span>
                <button
                  type="button"
                  onClick={() => removeTestCase(index)}
                  className="remove-btn"
                  disabled={formData.testCases.length <= 1}
                >
                  Remove
                </button>
              </div>

              <div className="test-case-fields">
                <div className="form-group">
                  <label htmlFor={`test-function-${index}`}>Function Name</label>
                  <input
                    type="text"
                    id={`test-function-${index}`}
                    value={testCase.functionName}
                    onChange={(e) => updateTestCase(index, 'functionName', e.target.value)}
                    placeholder="Function name to test"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor={`test-input-${index}`}>Input</label>
                  <textarea
                    id={`test-input-${index}`}
                    value={testCase.input}
                    onChange={(e) => updateTestCase(index, 'input', e.target.value)}
                    rows={2}
                    placeholder="Test input"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor={`test-output-${index}`}>Expected Output</label>
                  <textarea
                    id={`test-output-${index}`}
                    value={testCase.expectedOutput}
                    onChange={(e) => updateTestCase(index, 'expectedOutput', e.target.value)}
                    rows={2}
                    placeholder="Expected output"
                    required
                  />
                </div>
              </div>
            </div>
          ))}

          <button type="button" onClick={addTestCase} className="add-btn">
            Add Test Case
          </button>
        </div>

        <div className="form-actions">
          <button type="button" onClick={onClose} className="cancel-btn">
            Cancel
          </button>
          <button type="submit" className="submit-btn" disabled={submitting}>
            {submitting ? 'Creating...' : 'Create Challenge'}
          </button>
        </div>
      </form>
    </div>
  );
}

// Mock data for development
function getMockChallenges() {
  return [
    {
      id: '1',
      title: 'Two Sum',
      difficulty: 'easy',
      description: 'Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.',
      tags: ['Arrays', 'Hash Table'],
      completion: false,
      starterCode: `def two_sum(nums, target):\n    # Your code here\n    pass`
    },
    {
      id: '2',
      title: 'Palindrome Number',
      difficulty: 'easy',
      description: 'Given an integer x, return true if x is a palindrome, and false otherwise.',
      tags: ['Math'],
      completion: true,
      starterCode: `def is_palindrome(x):\n    # Your code here\n    pass`
    },
    {
      id: '3',
      title: 'Valid Parentheses',
      difficulty: 'medium',
      description: 'Given a string s containing just the characters \'(\', \')\', \'{\', \'}\', \'[\' and \']\', determine if the input string is valid.',
      tags: ['Stack', 'String'],
      completion: false,
      starterCode: `def is_valid(s):\n    # Your code here\n    pass`
    },
    {
      id: '4',
      title: 'Merge K Sorted Lists',
      difficulty: 'hard',
      description: 'You are given an array of k linked-lists lists, each linked-list is sorted in ascending order.',
      tags: ['Linked List', 'Divide and Conquer', 'Heap'],
      completion: false,
      starterCode: `def merge_k_lists(lists):\n    # Your code here\n    pass`
    }
  ];
}

export default CodingChallengeList;