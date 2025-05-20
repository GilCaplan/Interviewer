import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import FeatureList from './components/FeatureList';

function App() {
  const [apiInfo, setApiInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Use the API URL from environment variables, or fallback to a default
    // In development with Docker, this should be the server service name
    const apiUrl = process.env.REACT_APP_API_URL || 'http://server:5010';

    // Fetch information from the server with explicit URL
    fetch(`${apiUrl}/api/info`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`Network response was not ok: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        setApiInfo(data);
        setLoading(false);
      })
      .catch(error => {
        setError('Could not connect to the server. Please try again later.');
        setLoading(false);
        console.error('Error fetching data:', error);
      });
  }, []);

  return (
    <div className="app-container">
      <Header
        title="Interview Process Assistant"
        subtitle="Your journey to interview success starts here"
      />

      {loading ? (
        <p>Loading application information...</p>
      ) : error ? (
        <div>
          <p>{error}</p>
          <p>Using fallback data for demo purposes.</p>
          <FeatureList features={[
            "Practice programming problems",
            "Logical puzzles/riddles",
            "Interview questions",
            "Behavioral questions",
            "Case studies",
            "Mock interviews"
          ]} />
        </div>
      ) : (
        <div>
          <p>Version: {apiInfo.version}</p>
          <FeatureList features={apiInfo.features} />
        </div>
      )}
    </div>
  );
}

export default App;