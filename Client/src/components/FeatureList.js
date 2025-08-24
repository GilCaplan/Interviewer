import React from 'react';
import { Link } from 'react-router-dom';
import './FeatureList.css';

function FeatureList({ features }) {
  // This component now assumes the `features` prop is pre-filtered at its source.
  // It simply displays the features it receives.

  return (
    <div className="feature-list-container">
      <h2>Available Features</h2>
      <p className="feature-intro">
        Choose from our selection of interview preparation tools designed to help you succeed
      </p>

      <div className="features-list">
        {features.map((feature, index) => ( // Map over features directly
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