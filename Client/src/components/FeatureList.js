import React from 'react';
import { Link } from 'react-router-dom';

function FeatureList({ features }) {
  return (
    <div>
      <h2>Available Features</h2>
      <div className="features-list">
        {features.map((feature, index) => (
          <Link
            to={`/feature/${index}`}
            key={index}
            className="feature-link"
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <div className="feature-card">
              <h3>{feature.name}</h3>
              <p>{feature.description}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default FeatureList;