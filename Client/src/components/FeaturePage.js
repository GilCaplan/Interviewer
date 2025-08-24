import React from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';

function FeaturePage({ features }) {
  const { featureId } = useParams();
  const navigate = useNavigate();
  const featureIndex = parseInt(featureId);

  // Make sure we have valid features and a valid index
  if (!features || featureIndex < 0 || featureIndex >= features.length) {
    return (
      <div className="feature-page">
        <h2>Feature Not Found</h2>
        <p>Sorry, the requested feature could not be found.</p>
        <Link to="/" className="back-button">Back to Features</Link>
      </div>
    );
  }

  const feature = features[featureIndex];
  const isInterviewQuestions = feature.name.toLowerCase().includes('interview question');

  const handleStartNewSession = () => {
    const newSessionCode = Math.random().toString(36).substring(2, 8).toUpperCase();
    navigate(`/session/${newSessionCode}`);
  };

  // Detailed descriptions for each feature type
  const getDetailedDescription = (featureName) => {
    const name = featureName.toLowerCase();

    if (name.includes('interview question')) {
      return (
        <>
          <p>Prepare for technical interviews with commonly asked questions.</p>
          <ul>
            <li>Language-specific technical questions</li>
            <li>System design problems</li>
            <li>Database and SQL queries</li>
            <li>Web development concepts</li>
          </ul>
          <div className="feature-actions">
            <Link to="/user-questions" className="feature-action-btn">
              📝 My Questions
            </Link>
            <Link to="/llm-questions" className="feature-action-btn ai-btn">
              🤖 Generate AI Questions
            </Link>
            <button
              onClick={handleStartNewSession}
              className="feature-action-btn"
              style={{ backgroundColor: "#4CAF50" }}
            >
              ➕ Start New Template Session
            </button>
          </div>
          <p>Coming soon: AI-powered feedback on your answers.</p>
        </>
      );
    } else {
      // Fallback for any other feature, which shouldn't be accessible with the new filtering.
      return <p>Details for this feature are not available.</p>;
    }
  };

  return (
    <div className="feature-page">
      <h2>{feature.name}</h2>
      <div className="feature-description">
        {getDetailedDescription(feature.name)}
      </div>

      <div className="navigation-buttons">
        <Link to="/" className="back-button">Back to Features</Link>
      </div>


    </div>
  );
}

export default FeaturePage;