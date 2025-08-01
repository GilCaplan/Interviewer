import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import './Questions.css';

function TemplateDetails() {
  const { templateId } = useParams();
  const [template, setTemplate] = useState(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setError("Please log in to view templates.");
      return;
    }

    fetch(`/api/templates/${templateId}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
      .then(res => {
        if (!res.ok) {
          // Provide more specific error information
          throw new Error(`Failed to fetch template details. Status: ${res.status}`);
        }
        return res.json();
      })
      .then(data => setTemplate(data.template))
      .catch(err => {
        console.error(err);
        setError(err.message);
      });
  }, [templateId]);

  const handleStartInterview = async () => {
    setError('');
    const token = localStorage.getItem('token');

    try {
      const response = await fetch('/api/interviews/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ template_id: templateId })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not start interview.');

      navigate(`/interview/${data.interview_session_id}`);
    } catch (err) {
      setError(err.message);
    }
  };

  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;

  if (!template) {
    return <p>Loading template details...</p>;
  }

  const hasQuestions = template.questions && template.questions.length > 0;

  return (
    <div className="template-details-container">
      <h2>{template.template_name}</h2>
      <p><strong>Difficulty:</strong> {template.difficulty}</p>
      <p><strong>Subject:</strong> {template.subject}</p>
      {template.sub_subject && <p><strong>Sub-subject:</strong> {template.sub_subject}</p>}
      <p><strong>Author:</strong> {template.created_by_username || 'Unknown'}</p>
      <p><strong>Created:</strong> {template.created_at ? new Date(template.created_at.$date || template.created_at).toLocaleString() : 'N/A'}</p>
      <p><strong>Number of Questions:</strong> {template.questions?.length || 0}</p>

      <button
        onClick={handleStartInterview}
        className="start-interview-btn"
        disabled={!hasQuestions}
        title={!hasQuestions ? "Add questions to this template to start a mock interview." : "Start Mock Interview"}
      >
        Start Mock Interview
      </button>

      <h3>Questions</h3>
      {hasQuestions ? (
        <ul className="questions-list">
          {template.questions.map((q, index) => (
            <li key={index}>
              <p><strong>Q{index + 1}:</strong> {q.question_text}</p>
              {q.choices && q.choices.length > 0 && (
                <ul>
                  {q.choices.map((choice, i) => (
                    <li key={i}>{choice}</li>
                  ))}
                </ul>
              )}
              <p><strong>Answer:</strong> {q.correct_answer}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p>This template does not have any questions yet.</p>
      )}

      <Link to="/templates" className="back-link">← Back to Templates</Link>
    </div>
  );
}

export default TemplateDetails;
