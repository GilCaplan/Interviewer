import React, { useEffect, useState } from 'react';
import './TemplatesGallery.css';
import { Link, useNavigate } from 'react-router-dom';
import { getApiUrl, makeAuthenticatedRequest } from '../utils/authUtils';
import { useAuth } from '../context/AuthContext';

function TemplatesGallery() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('');
  const [availableDifficulties, setAvailableDifficulties] = useState([]);
  const [availableSubjects, setAvailableSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCleanupModal, setShowCleanupModal] = useState(false);
  const [cleanupPreview, setCleanupPreview] = useState(null);
  const [cleanupLoading, setCleanupLoading] = useState(false);

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        setLoading(true);
        setError('');
        
        console.log('Loading templates from:', `${getApiUrl()}/api/templates`);
        console.log('User authenticated:', isAuthenticated);
        console.log('User info:', user);
        
        // Check if user has auth token
        const token = localStorage.getItem('token') || 
                     (localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')).sessionToken : null);
        console.log('Auth token available:', !!token);
        
        if (!isAuthenticated) {
          setError('Please login to view templates.');
          setLoading(false);
          return;
        }
        
        const response = await makeAuthenticatedRequest(`${getApiUrl()}/api/templates`, {
          method: 'GET'
        });

        console.log('Templates response status:', response.status);

        if (response.ok) {
          const data = await response.json();
          console.log('Templates data received:', data);
          const templates = data.templates || [];
          console.log('Number of templates:', templates.length);
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
        } else {
          const errorData = await response.json();
          setError(errorData.error || 'Failed to load templates');
        }
      } catch (err) {
        console.error('Error loading templates:', err);
        if (err.message.includes('Authentication expired')) {
          setError('Please login again to view templates.');
        } else if (err.message.includes('No authentication token')) {
          setError('Please login to view templates.');
        } else {
          setError(`Error: ${err.message}`);
        }
      } finally {
        setLoading(false);
      }
    };

    loadTemplates();
  }, []);

  const loadCleanupPreview = async () => {
    setCleanupLoading(true);
    try {
      const response = await makeAuthenticatedRequest(`${getApiUrl()}/api/templates/cleanup-preview?user_only=true`, {
        method: 'GET'
      });

      if (response.ok) {
        const data = await response.json();
        setCleanupPreview(data);
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to load cleanup preview');
      }
    } catch (err) {
      console.error('Error loading cleanup preview:', err);
      setError('Failed to load cleanup preview');
    } finally {
      setCleanupLoading(false);
    }
  };

  const performCleanup = async (dryRun = true) => {
    setCleanupLoading(true);
    try {
      const response = await makeAuthenticatedRequest(`${getApiUrl()}/api/templates/cleanup-duplicates`, {
        method: 'POST',
        body: JSON.stringify({
          dry_run: dryRun,
          user_only: true
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        if (!dryRun) {
          // Refresh templates after actual cleanup
          window.location.reload();
        } else {
          setCleanupPreview(data);
        }
        
        return data;
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to cleanup templates');
      }
    } catch (err) {
      console.error('Error during cleanup:', err);
      setError(err.message);
      throw err;
    } finally {
      setCleanupLoading(false);
    }
  };

  const handleShowCleanup = () => {
    setShowCleanupModal(true);
    loadCleanupPreview();
  };

  // Group templates by template_key and show only latest version of each
  const groupedTemplates = templates.reduce((acc, template) => {
    const key = template.template_key || `legacy_${template.template_id}`;
    
    if (!acc[key] || template.metadata?.version > (acc[key].metadata?.version || 1)) {
      acc[key] = template;
    }
    
    return acc;
  }, {});

  const uniqueTemplates = Object.values(groupedTemplates);

  const filteredTemplates = uniqueTemplates.filter(template => {
    const nameMatch = template.template_name?.toLowerCase().includes(searchQuery.toLowerCase());
    const difficultyMatch =
      !difficultyFilter || template.difficulty?.toLowerCase() === difficultyFilter;
    const subjectMatch =
      !subjectFilter || template.subject?.toLowerCase() === subjectFilter;
    return nameMatch && difficultyMatch && subjectMatch;
  });

  return (
    <div className="template-gallery">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ margin: 0 }}>Templates Gallery</h2>
        <button 
          onClick={handleShowCleanup}
          style={{
            backgroundColor: '#ff9800',
            color: 'white',
            padding: '10px 16px',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            cursor: 'pointer',
            fontWeight: '600'
          }}
        >
          🧹 Cleanup Duplicates
        </button>
      </div>
      
      {loading && <div className="loading">Loading templates...</div>}
      {error && (
        <div className="error-message">
          {error}
          {!isAuthenticated && (
            <div style={{ marginTop: '15px' }}>
              <button 
                onClick={() => navigate('/login')}
                style={{
                  backgroundColor: '#2196F3',
                  color: 'white',
                  padding: '10px 20px',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                Go to Login
              </button>
            </div>
          )}
        </div>
      )}
      
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

      <div className="template-stats" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <p>Found {filteredTemplates.length} template{filteredTemplates.length !== 1 ? 's' : ''}</p>
        <button 
          onClick={() => window.location.reload()}
          style={{
            backgroundColor: '#4CAF50',
            color: 'white',
            padding: '8px 16px',
            border: 'none',
            borderRadius: '4px',
            fontSize: '12px',
            cursor: 'pointer'
          }}
        >
          🔄 Refresh
        </button>
      </div>

      <div className="template-grid">
        {filteredTemplates.length === 0 && !loading ? (
          <div className="no-templates">
            <p>No templates found.</p>
            <p>Create a new template using collaborative sessions!</p>
          </div>
        ) : (
          filteredTemplates.map((template, index) => (
             <Link to={`/template/${template.template_id}`} key={template.template_id} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="template-card">
                  <h3>{template.template_name || 'Untitled Template'}</h3>
                  {template.metadata?.version > 1 && (
                    <p style={{ color: '#2196F3', fontSize: '0.85rem', fontWeight: '600', margin: '5px 0' }}>
                      📝 Version {template.metadata.version}
                    </p>
                  )}
                  <p><strong>Difficulty:</strong> {template.difficulty || 'N/A'}</p>
                  <p><strong>Subject:</strong> {template.subject || 'N/A'}</p>
                  {template.sub_subject && <p><strong>Sub-subject:</strong> {template.sub_subject}</p>}
                  <p><strong>Created:</strong> {template.metadata?.created_at ? new Date(template.metadata.created_at).toLocaleString() : 'Unknown'}</p>
                  {template.metadata?.updated_at && template.metadata.updated_at !== template.metadata.created_at && (
                    <p><strong>Updated:</strong> {new Date(template.metadata.updated_at).toLocaleString()}</p>
                  )}
                  <p><strong># Questions:</strong> {template.questions?.length || template.metadata?.question_count || 0}</p>
                  <p><strong>Author:</strong> {template.created_by || 'Anonymous'}</p>
                  {template.description && <p className="template-description">{template.description}</p>}
                  {template.is_public && <span className="public-badge">PUBLIC</span>}
                </div>
             </Link>
          ))
        )}
      </div>

      {/* Cleanup Modal */}
      {showCleanupModal && (
        <div className="modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10000
        }}>
          <div className="modal-content" style={{
            background: 'white',
            padding: '30px',
            borderRadius: '12px',
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.3)',
            minWidth: '500px',
            maxWidth: '700px',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <h3 style={{ marginBottom: '20px', color: '#333', textAlign: 'center' }}>
              🧹 Template Cleanup
            </h3>
            
            {cleanupLoading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <p>🔍 Scanning for duplicate templates...</p>
              </div>
            ) : cleanupPreview ? (
              <div>
                <div style={{ 
                  backgroundColor: '#f0f8ff', 
                  padding: '15px', 
                  borderRadius: '8px', 
                  marginBottom: '20px',
                  border: '1px solid #2196F3'
                }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#1976d2' }}>📊 Cleanup Summary</h4>
                  <p style={{ margin: '5px 0', fontSize: '14px' }}>
                    <strong>Total Templates:</strong> {cleanupPreview.total_templates}
                  </p>
                  <p style={{ margin: '5px 0', fontSize: '14px' }}>
                    <strong>Unique Templates:</strong> {cleanupPreview.unique_templates}
                  </p>
                  <p style={{ margin: '5px 0', fontSize: '14px' }}>
                    <strong>Duplicate Groups:</strong> {cleanupPreview.duplicate_groups}
                  </p>
                  <p style={{ margin: '5px 0', fontSize: '14px', color: '#ff5722' }}>
                    <strong>Templates to Remove:</strong> {cleanupPreview.duplicates_found}
                  </p>
                </div>

                {cleanupPreview.duplicates_found > 0 ? (
                  <div>
                    <h4 style={{ color: '#333', marginBottom: '15px' }}>🗂️ Duplicate Groups Found:</h4>
                    <div style={{ maxHeight: '300px', overflowY: 'auto', marginBottom: '20px' }}>
                      {Object.entries(cleanupPreview.groups).map(([groupKey, templates]) => (
                        <div key={groupKey} style={{
                          border: '1px solid #ddd',
                          borderRadius: '6px',
                          padding: '12px',
                          marginBottom: '10px',
                          backgroundColor: '#fafafa'
                        }}>
                          <h5 style={{ margin: '0 0 8px 0', color: '#333' }}>
                            "{templates[0].template_name}"
                          </h5>
                          <p style={{ fontSize: '12px', color: '#666', margin: '0 0 8px 0' }}>
                            {templates.length} duplicates found
                          </p>
                          {templates.map((template, index) => (
                            <div key={template.template_id} style={{
                              fontSize: '12px',
                              padding: '4px 8px',
                              backgroundColor: index === 0 ? '#e8f5e9' : '#ffebee',
                              border: `1px solid ${index === 0 ? '#4caf50' : '#f44336'}`,
                              borderRadius: '4px',
                              margin: '2px 0'
                            }}>
                              {index === 0 ? '✅ KEEP' : '🗑️ REMOVE'} - 
                              Version {template.metadata?.version || 1} - 
                              {template.metadata?.question_count || 0} questions - 
                              {new Date(template.metadata?.created_at).toLocaleDateString()}
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>

                    <div style={{ 
                      backgroundColor: '#fff3cd', 
                      padding: '15px', 
                      borderRadius: '8px', 
                      marginBottom: '20px',
                      border: '1px solid #ffc107'
                    }}>
                      <p style={{ margin: 0, fontSize: '14px', color: '#856404' }}>
                        ⚠️ <strong>Warning:</strong> This will permanently delete {cleanupPreview.duplicates_found} duplicate templates. 
                        The newest version or highest version number will be kept for each group.
                      </p>
                    </div>

                    <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                      <button
                        onClick={() => setShowCleanupModal(false)}
                        style={{
                          padding: '12px 20px',
                          border: 'none',
                          borderRadius: '6px',
                          fontSize: '16px',
                          cursor: 'pointer',
                          backgroundColor: '#6c757d',
                          color: 'white',
                          fontWeight: '600'
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        onClick={async () => {
                          if (window.confirm(`Are you sure you want to delete ${cleanupPreview.duplicates_found} duplicate templates? This cannot be undone.`)) {
                            try {
                              await performCleanup(false);
                              alert('Duplicate templates have been removed successfully!');
                              setShowCleanupModal(false);
                            } catch (error) {
                              alert('Failed to cleanup templates: ' + error.message);
                            }
                          }
                        }}
                        disabled={cleanupLoading}
                        style={{
                          padding: '12px 20px',
                          border: 'none',
                          borderRadius: '6px',
                          fontSize: '16px',
                          cursor: cleanupLoading ? 'not-allowed' : 'pointer',
                          backgroundColor: cleanupLoading ? '#ccc' : '#dc3545',
                          color: 'white',
                          fontWeight: '600'
                        }}
                      >
                        {cleanupLoading ? '🔄 Cleaning...' : `🗑️ Remove ${cleanupPreview.duplicates_found} Duplicates`}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px' }}>
                    <p style={{ fontSize: '18px', color: '#4caf50', marginBottom: '10px' }}>
                      ✅ No duplicate templates found!
                    </p>
                    <p style={{ color: '#666', fontSize: '14px' }}>
                      Your template library is clean and organized.
                    </p>
                    <button
                      onClick={() => setShowCleanupModal(false)}
                      style={{
                        padding: '12px 20px',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '16px',
                        cursor: 'pointer',
                        backgroundColor: '#4caf50',
                        color: 'white',
                        fontWeight: '600',
                        marginTop: '20px'
                      }}
                    >
                      Great!
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <p>Failed to load cleanup preview.</p>
                <button
                  onClick={() => setShowCleanupModal(false)}
                  style={{
                    padding: '12px 20px',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '16px',
                    cursor: 'pointer',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    fontWeight: '600'
                  }}
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default TemplatesGallery;