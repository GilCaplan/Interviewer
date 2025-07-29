import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';

function TemplateDetails() {
  const { templateId } = useParams();
  const [template, setTemplate] = useState(null);

  useEffect(() => {
    fetch(`http://localhost:5001/templates/${templateId}`)
      .then(res => res.json())
      .then(data => setTemplate(data.template))
      .catch(err => console.error(err));
  }, [templateId]);

  if (!template) {
    return <p>Loading template details...</p>;
  }

  return (
    <div style={{ padding: '20px 40px' }}>
      <h2>{template.template_name}</h2>
      <p><strong>Difficulty:</strong> {template.difficulty}</p>
      <p><strong>Subject:</strong> {template.subject}</p>
      <p><strong>Sub-subject:</strong> {template.sub_subject}</p>
      <p><strong>Author:</strong> {template.created_by}</p>
      <p><strong>Created:</strong> {new Date(template.metadata.created_at).toLocaleString()}</p>
      <p><strong>Number of Questions:</strong> {template.questions?.length || 0}</p>

      <h3>Questions</h3>
      <ul>
        {template.questions.map((q, index) => (
          <li key={index}>
            <p><strong>Q{index + 1}:</strong> {q.question_text}</p>
            <ul>
              {q.choices?.map((choice, i) => (
                <li key={i}>{choice}</li>
              ))}
            </ul>
            <p><strong>Answer:</strong> {q.correct_answer}</p>
          </li>
        ))}
      </ul>

      <Link to="/" style={{ display: 'block', marginTop: '20px' }}>← Back to Home</Link>
    </div>
  );
}

export default TemplateDetails;
