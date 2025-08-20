import React from 'react';
import { Link } from 'react-router-dom';
import './FeatureList.css';

function FeatureList({ features }) {
  // Filter out the unwanted features: "Behavioral questions" and "More Coming Soon"
  const filteredFeatures = features.filter(feature =>
    !feature.name.toLowerCase().includes('behavioral questions') &&
    !feature.name.toLowerCase().includes('more coming soon')
  );
  // Group features into rows of 3 for better layout
  const chunkArray = (array, size) => {
    const result = [];
    for (let i = 0; i < array.length; i += size) {
      result.push(array.slice(i, i + size));
    }
    return result;
  };

  const featureRows = chunkArray(filteredFeatures, 3); // Use filtered features here

  return (
    <div className="feature-list-container">
      <h2>Available Features</h2>
      <p className="feature-intro">
        Choose from our selection of interview preparation tools designed to help you succeed
      </p>

      <div className="features-list">
        {filteredFeatures.map((feature, index) => ( // Map over filtered features
          <Link
            to={feature.route || `/feature/${index}`}
            key={index}
            className="feature-link"
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <div className="feature-card">
              {/* Feature icon based on type */}
              <div className="feature-icon">
                {getFeatureIcon(feature.name)}
              </div>

              <h3>{feature.name}</h3>
              <p>{feature.description}</p>

              <div className="feature-card-footer">
                <span className="explore-text">
                  {feature.route ? 'Open feature' : 'Explore feature'}
                </span>
                <span className="arrow-icon">→</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

// Helper function to determine appropriate icon for each feature
function getFeatureIcon(featureName) {
  const name = featureName.toLowerCase();

  if (name.includes('collaborative') || name.includes('session')) {
    return '👥';
  } else if (name.includes('programming') || name.includes('coding')) {
    return '💻';
  } else if (name.includes('puzzle') || name.includes('riddle')) {
    return '🧩';
  } else if (name.includes('interview question')) {
    return '❓';
  } else if (name.includes('case stud')) {
    return '📊';
  } else if (name.includes('mock')) {
    return '🎭';
  } else if (name.includes('resume')) {
    return '📄';
  } else if (name.includes('dashboard')) {
    return '📈';
  } else {
    return '🎯';
  }
}

export default FeatureList;