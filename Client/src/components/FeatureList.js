import React from 'react';

function FeatureList({ features }) {
  return (
    <div>
      <h2>Available Features</h2>
      <div className="features-list">
        {features.map((feature, index) => (
          <div key={index} className="feature-card">
            <h3>Feature {index + 1}</h3>
            <p>{feature}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default FeatureList;