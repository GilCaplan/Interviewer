import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { fetchApi } from '../utils/api';
import './Questions.css'; // Reusing styles for a consistent look

function TemplateDetails() {
  const { templateId } = useParams();
  const navigate = useNavigate();
  const [template, setTemplate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadTemplateDetails = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchApi(`/api/templates/${templateId}`);
        setTemplate(data.template);
      } catch (err) {
        // The fetchApi utility provides a detailed error message, including the 'reason'
        setError(err.message);
        console.error("Failed to fetch template details:", err);
      } finally {
        setLoading(false);
      }
    };

    if (templateId) {
      loadTemplateDetails();
    }
  }, [templateId]);

  const startInterview = async () => {
    console.log("Starting interview with template:", templateId);
    try {
      // Corrected API endpoint and response handling
      const response = await fetchApi('/api/interview/start', {
        method: 'POST',
        body: JSON.stringify({ template_id: templateId }),
      });

      if (response && response.interview_session_id) {
        // Navigate to the interview page for the newly created session
        navigate(`/interview/${response.interview_session_id}`);
      } else {
        setError('Failed to create a new interview session. No session ID was returned.');
      }
    } catch (err) {
      // Display any errors that occur during session creation
      setError(err.message);
      console.error("Failed to start interview:", err);
    }
  };

  if (loading) {
    return <div className="loading">Loading template details...</div>;
  }

  if (error) {
    // This will now display the detailed error message from the backend
    return (
      <div className="template-details-container">
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
        <Link to="/templates" className="back-link">← Back to Templates</Link>
      </div>
    );
  }

  if (!template) {
    return (
      <div className="template-details-container">
        <h2>Template Not Found</h2>
        <p>The template you are looking for does not exist or you may not have permission to view it.</p>
        <Link to="/templates" className="back-link">← Back to Templates</Link>
      </div>
    );
  }

  return (
    <div className="template-details-container">
      <h2>{template.template_name}</h2>
      <p>{template.description}</p>

      <p><strong>Subject:</strong> {template.subject} | <strong>Difficulty:</strong> {template.difficulty} | <strong>Questions:</strong> {template.metadata?.question_count || 0}</p>

      <button onClick={startInterview} className="start-interview-btn">
        Start Mock Interview
      </button>

      <h3>Questions in this Template</h3>
      {template.questions && template.questions.length > 0 ? (
        <ul className="questions-list">
          {template.questions.map((q, index) => <li key={q.question_id || index}><strong>Q{index + 1}:</strong> {q.question_text}</li>)}
        </ul>
      ) : (<p>This template does not have any questions yet.</p>)}

      <Link to="/templates" className="back-link">← Back to Templates</Link>
    </div>
  );
}

export default TemplateDetails;