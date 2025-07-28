import React, { useEffect, useState } from 'react';
import './TemplatesGallery.css';
import { Link } from 'react-router-dom';

function TemplatesGallery() {
  const [templates, setTemplates] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('');
  const [availableDifficulties, setAvailableDifficulties] = useState([]);
  const [availableSubjects, setAvailableSubjects] = useState([]);

  useEffect(() => {
    fetch('http://localhost:5000/templates')
      .then(res => res.json())
      .then(data => {
        const templates = data.templates || [];
        setTemplates(templates);

        // Dynamically extract difficulties and subjects (case-insensitive uniqueness)
        const difficulties = [
          ...new Set(templates.map(t => t.difficulty?.toLowerCase()).filter(Boolean)),
        ];
        const subjects = [
          ...new Set(templates.map(t => t.subject?.toLowerCase()).filter(Boolean)),
        ];
        setAvailableDifficulties(difficulties);
        setAvailableSubjects(subjects);
      })
      .catch(err => console.error(err));
  }, []);

  const filteredTemplates = templates.filter(template => {
    const nameMatch = template.template_name?.toLowerCase().includes(searchQuery.toLowerCase());
    const difficultyMatch =
      !difficultyFilter || template.difficulty?.toLowerCase() === difficultyFilter;
    const subjectMatch =
      !subjectFilter || template.subject?.toLowerCase() === subjectFilter;
    return nameMatch && difficultyMatch && subjectMatch;
  });

  return (
    <div className="template-gallery">
      <h2>Templates Gallery</h2>
      <div className="template-controls">
        <input
          type="text"
          placeholder="Search by name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />

        <select
          value={difficultyFilter}
          onChange={(e) => setDifficultyFilter(e.target.value)}
        >
          <option value="">All Difficulties</option>
          {availableDifficulties.map((diff, idx) => (
            <option key={idx} value={diff}>{diff.charAt(0).toUpperCase() + diff.slice(1)}</option>
          ))}
        </select>

        <select
          value={subjectFilter}
          onChange={(e) => setSubjectFilter(e.target.value)}
        >
          <option value="">All Subjects</option>
          {availableSubjects.map((subject, idx) => (
            <option key={idx} value={subject}>{subject.charAt(0).toUpperCase() + subject.slice(1)}</option>
          ))}
        </select>
      </div>

      <div className="template-grid">
        {filteredTemplates.map((template, index) => (
           <Link to={`/template/${template._id}`} key={template._id} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div className="template-card" key={template._id || index}>
                <h3>{template.template_name || 'Untitled Template'}</h3>
                <p><strong>Difficulty:</strong> {template.difficulty || 'N/A'}</p>
                <p><strong>Subject:</strong> {template.subject || 'N/A'}</p>
                <p><strong>Sub-subject:</strong> {template.sub_subject || 'N/A'}</p>
                <p><strong>Created:</strong> {template.metadata?.created_at ? new Date(template.metadata.created_at).toLocaleString() : 'Unknown'}</p>
                <p><strong># Questions:</strong> {template.questions?.length || 0}</p>
                <p><strong>Author:</strong> {template.created_by || 'Anonymous'}</p>
              </div>
           </Link>
        ))}
      </div>
    </div>
  );
}

export default TemplatesGallery;