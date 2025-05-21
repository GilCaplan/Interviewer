import React, { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import MonacoEditor from 'react-monaco-editor';
import './CodingChallenge.css';
import { useAuth } from '../context/AuthContext';

function CodingChallenge() {
  const { challengeId } = useParams();
  const { user } = useAuth();
  const [challenge, setChallenge] = useState(null);
  const [code, setCode] = useState('');
  const [output, setOutput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [testResults, setTestResults] = useState([]);
  const [editorOptions, setEditorOptions] = useState({
    selectOnLineNumbers: true,
    roundedSelection: false,
    readOnly: false,
    cursorStyle: 'line',
    automaticLayout: true,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    lineNumbers: 'on',
    fontSize: 14,
  });

  useEffect(() => {
    // Fetch challenge details
    const fetchChallenge = async () => {
      try {
        // For development, use mock data
        if (process.env.NODE_ENV === 'development' && !process.env.REACT_APP_USE_API) {
          const mockChallenge = getMockChallenge(challengeId);
          setChallenge(mockChallenge);
          setCode(mockChallenge.starterCode);
          return;
        }

        // For production, fetch from API
        const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
        const response = await fetch(`${apiUrl}/api/coding-challenges/${challengeId}`, {
          headers: {
            'Authorization': `Bearer ${user?.sessionToken}`
          },
          credentials: 'include'
        });

        if (!response.ok) {
          throw new Error('Failed to fetch challenge');
        }

        const data = await response.json();
        setChallenge(data.challenge);
        setCode(data.challenge.starterCode);
      } catch (error) {
        console.error('Error fetching challenge:', error);
        // If API fails, fall back to mock data
        const mockChallenge = getMockChallenge(challengeId);
        setChallenge(mockChallenge);
        setCode(mockChallenge.starterCode);
      }
    };

    fetchChallenge();
  }, [challengeId, user]);

  const runCode = async () => {
    setIsRunning(true);
    setOutput('Running your code...');
    setTestResults([]);

    try {
      // For development without API, use mock execution
      if (process.env.NODE_ENV === 'development' && !process.env.REACT_APP_USE_API) {
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Simple evaluation for demo purposes (NEVER do this in production)
        // This is just for demonstration and will be replaced by proper backend execution
        const testFunction = new Function(
          'userCode',
          `
          try {
            ${code}
            
            // Run test cases
            const results = [];
            ${challenge.testCases.map((test, index) => `
              try {
                const result = ${test.functionName}(${test.input});
                const passed = JSON.stringify(result) === JSON.stringify(${test.expectedOutput});
                results.push({
                  id: ${index},
                  name: 'Test Case ${index + 1}',
                  input: '${test.input}',
                  expected: '${test.expectedOutput}',
                  actual: JSON.stringify(result),
                  passed: passed
                });
              } catch (e) {
                results.push({
                  id: ${index},
                  name: 'Test Case ${index + 1}',
                  input: '${test.input}',
                  expected: '${test.expectedOutput}',
                  actual: 'Error: ' + e.message,
                  passed: false
                });
              }
            `).join('\n')}
            
            return { success: true, output: 'Code ran successfully', results };
          } catch (error) {
            return { success: false, output: 'Error: ' + error.message, results: [] };
          }
          `
        );

        const result = testFunction();
        setOutput(result.output);
        setTestResults(result.results);

        return;
      }

      // For production, use API
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/run-code`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user?.sessionToken}`
        },
        body: JSON.stringify({
          code,
          challengeId,
          language: 'python'
        }),
        credentials: 'include'
      });

      const data = await response.json();
      setOutput(data.output);
      setTestResults(data.testResults || []);
    } catch (error) {
      setOutput(`Error: ${error.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleEditorChange = (newValue) => {
    setCode(newValue);
  };

  const editorDidMount = (editor, monaco) => {
    editor.focus();
  };

  if (!challenge) {
    return <div className="loading">Loading challenge...</div>;
  }

  return (
    <div className="coding-challenge-container">
      <div className="challenge-header">
        <h2>{challenge.title}</h2>
        <div className="challenge-tags">
          <span className="difficulty-tag" data-difficulty={challenge.difficulty.toLowerCase()}>
            {challenge.difficulty}
          </span>
          {challenge.tags.map((tag, index) => (
            <span key={index} className="tag">{tag}</span>
          ))}
        </div>
      </div>

      <div className="challenge-layout">
        <div className="description-panel">
          <div className="description-content">
            <h3>Problem Description</h3>
            <div dangerouslySetInnerHTML={{ __html: challenge.description }} />

            <h3>Examples</h3>
            <div className="examples">
              {challenge.examples.map((example, index) => (
                <div key={index} className="example-item">
                  <div className="example-header">Example {index + 1}:</div>
                  <pre className="example-code">
                    <strong>Input:</strong> {example.input}
                    <br />
                    <strong>Output:</strong> {example.output}
                    {example.explanation && (
                      <>
                        <br />
                        <strong>Explanation:</strong> {example.explanation}
                      </>
                    )}
                  </pre>
                </div>
              ))}
            </div>

            {challenge.constraints && (
              <>
                <h3>Constraints</h3>
                <ul className="constraints-list">
                  {challenge.constraints.map((constraint, index) => (
                    <li key={index}>{constraint}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </div>

        <div className="editor-panel">
          <div className="editor-header">
            <span>Solution</span>
            <select className="language-selector">
              <option value="python">Python</option>
              <option value="javascript" disabled>JavaScript (Coming Soon)</option>
              <option value="java" disabled>Java (Coming Soon)</option>
              <option value="cpp" disabled>C++ (Coming Soon)</option>
            </select>
          </div>

          <div className="editor-container">
            <MonacoEditor
              width="100%"
              height="400"
              language="python"
              theme="vs-dark"
              value={code}
              options={editorOptions}
              onChange={handleEditorChange}
              editorDidMount={editorDidMount}
            />
          </div>

          <div className="editor-controls">
            <button
              onClick={runCode}
              disabled={isRunning}
              className="run-button"
            >
              {isRunning ? 'Running...' : 'Run Tests'}
            </button>
            <button className="reset-button">Reset Code</button>
          </div>

          <div className="output-panel">
            <h3>Console Output</h3>
            <pre className="output-content">{output}</pre>
          </div>

          <div className="test-results">
            <h3>Test Results</h3>
            {testResults.length === 0 ? (
              <p className="no-tests">Run your code to see test results</p>
            ) : (
              <div className="test-cases">
                {testResults.map((test) => (
                  <div key={test.id} className={`test-case ${test.passed ? 'passed' : 'failed'}`}>
                    <div className="test-header">
                      <span className="test-name">{test.name}</span>
                      <span className="test-status">{test.passed ? 'Passed' : 'Failed'}</span>
                    </div>
                    <div className="test-details">
                      <div><strong>Input:</strong> {test.input}</div>
                      <div><strong>Expected:</strong> {test.expected}</div>
                      <div><strong>Actual:</strong> {test.actual}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="challenge-footer">
        <Link to="/coding-challenges" className="back-button">Back to Challenges</Link>
      </div>
    </div>
  );
}

// Mock data for development
function getMockChallenge(id) {
  const challenges = {
    '1': {
      id: '1',
      title: 'Two Sum',
      difficulty: 'Easy',
      tags: ['Arrays', 'Hash Table'],
      description: `<p>Given an array of integers <code>nums</code> and an integer <code>target</code>, return indices of the two numbers such that they add up to <code>target</code>.</p>
                   <p>You may assume that each input would have <strong>exactly one solution</strong>, and you may not use the same element twice.</p>
                   <p>You can return the answer in any order.</p>`,
      examples: [
        {
          input: 'nums = [2, 7, 11, 15], target = 9',
          output: '[0, 1]',
          explanation: 'Because nums[0] + nums[1] == 9, we return [0, 1].'
        },
        {
          input: 'nums = [3, 2, 4], target = 6',
          output: '[1, 2]'
        }
      ],
      constraints: [
        '2 <= nums.length <= 104',
        '-109 <= nums[i] <= 109',
        '-109 <= target <= 109',
        'Only one valid answer exists.'
      ],
      starterCode: `def two_sum(nums, target):
    """
    :type nums: List[int]
    :type target: int
    :rtype: List[int]
    """
    # Your code here
    
`,
      testCases: [
        {
          functionName: 'two_sum',
          input: '[2, 7, 11, 15], 9',
          expectedOutput: '[0, 1]'
        },
        {
          functionName: 'two_sum',
          input: '[3, 2, 4], 6',
          expectedOutput: '[1, 2]'
        },
        {
          functionName: 'two_sum',
          input: '[3, 3], 6',
          expectedOutput: '[0, 1]'
        }
      ]
    },
    '2': {
      id: '2',
      title: 'Palindrome Number',
      difficulty: 'Easy',
      tags: ['Math'],
      description: `<p>Given an integer <code>x</code>, return <code>true</code> if <code>x</code> is palindrome integer.</p>
                   <p>An integer is a <strong>palindrome</strong> when it reads the same backward as forward.</p>
                   <p>For example, <code>121</code> is a palindrome while <code>123</code> is not.</p>`,
      examples: [
        {
          input: 'x = 121',
          output: 'true',
          explanation: '121 reads as 121 from left to right and from right to left.'
        },
        {
          input: 'x = -121',
          output: 'false',
          explanation: 'From left to right, it reads -121. From right to left, it becomes 121-. Therefore it is not a palindrome.'
        }
      ],
      constraints: [
        '-231 <= x <= 231 - 1'
      ],
      starterCode: `def is_palindrome(x):
    """
    :type x: int
    :rtype: bool
    """
    # Your code here
    
`,
      testCases: [
        {
          functionName: 'is_palindrome',
          input: '121',
          expectedOutput: 'true'
        },
        {
          functionName: 'is_palindrome',
          input: '-121',
          expectedOutput: 'false'
        },
        {
          functionName: 'is_palindrome',
          input: '10',
          expectedOutput: 'false'
        }
      ]
    }
  };

  return challenges[id] || challenges['1'];
}

export default CodingChallenge;