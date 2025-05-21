import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import FeatureList from './components/FeatureList';
import FeaturePage from './components/FeaturePage';
import Login from './components/Login';
import UserQuestions from './components/UserQuestions';
import LlmQuestions from './components/LlmQuestions';
import CodingChallengeList from './components/CodingChallengeList';
import CodingChallenge from './components/CodingChallenge';
import { AuthProvider, useAuth } from './context/AuthContext';
import './index.css';
import './components/Login.css';
import './components/Questions.css';

// Protected route component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return children;
};

// Main App content component
function AppContent() {
  const { user, isAuthenticated, logout } = useAuth();
  const [apiInfo, setApiInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Use the API URL from environment variables, or fallback to a default
    const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';

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

  // Default features to display if API is not available
  const fallbackFeatures = [
    {
      name: "Practice programming problems",
      description: "Sharpen your coding skills with various programming challenges."
    },
    {
      name: "Logical puzzles/riddles",
      description: "Test your problem-solving abilities with logic puzzles."
    },
    {
      name: "Interview questions",
      description: "Common technical questions to prepare for your interview."
    },
    {
      name: "Behavioral questions",
      description: "Practice answering questions about your past experiences."
    },
    {
      name: "Case studies",
      description: "Complex scenarios to test your analytical thinking."
    },
    {
      name: "Mock interviews",
      description: "Simulate a real interview environment with AI feedback."
    }
  ];

  // Format API features to include descriptions
  const formatApiFeatures = (features) => {
    return features.map(feature => {
      return {
        name: feature,
        description: getFeatureDescription(feature)
      };
    });
  };

  // Get a description for each feature
  const getFeatureDescription = (featureName) => {
    // Find matching feature in fallback list or provide generic description
    const fallbackFeature = fallbackFeatures.find(f => f.name === featureName);
    return fallbackFeature ? fallbackFeature.description : "Explore this feature to enhance your interview preparation.";
  };

  const features = apiInfo ? formatApiFeatures(apiInfo.features) : fallbackFeatures;

  return (
    <div className="app-container">
      <Header
        title="Interview Process Assistant"
        subtitle="Your journey to interview success starts here"
        username={user?.username}
        onLogout={logout}
        isAuthenticated={isAuthenticated}
      />

      <Routes>
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/" /> : <Login />}
        />

        <Route
          path="/"
          element={
            <ProtectedRoute>
              {loading ? (
                <p>Loading application information...</p>
              ) : error ? (
                <div>
                  <p>{error}</p>
                  <p>Using fallback data for demo purposes.</p>
                  <FeatureList features={fallbackFeatures} />
                </div>
              ) : (
                <div>
                  <p className="welcome-message">
                    Welcome, {user?.username || 'User'}! Ready to practice for your next interview?
                  </p>
                  <p>Version: {apiInfo?.version || '0.1.0'}</p>
                  <FeatureList features={features} />
                </div>
              )}
            </ProtectedRoute>
          }
        />

        <Route
          path="/feature/:featureId"
          element={
            <ProtectedRoute>
              <FeaturePage features={features} />
            </ProtectedRoute>
          }
        />

        {/* Routes for questions features */}
        <Route
          path="/user-questions"
          element={
            <ProtectedRoute>
              <UserQuestions />
            </ProtectedRoute>
          }
        />

        <Route
          path="/llm-questions"
          element={
            <ProtectedRoute>
              <LlmQuestions />
            </ProtectedRoute>
          }
        />

        {/* Routes for coding challenges */}
        <Route
          path="/coding-challenges"
          element={
            <ProtectedRoute>
              <CodingChallengeList />
            </ProtectedRoute>
          }
        />

        <Route
          path="/coding-challenges/:challengeId"
          element={
            <ProtectedRoute>
              <CodingChallenge />
            </ProtectedRoute>
          }
        />

        <Route
          path="*"
          element={<Navigate to="/" />}
        />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;