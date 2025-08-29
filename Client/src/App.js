import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { getApiUrl } from './utils/authUtils';
import Header from './components/Header';
import TemplatesGallery from "./components/TemplatesGallery";
import FeatureList from './components/FeatureList';
import FeaturePage from './components/FeaturePage';
import Login from './components/Login';
import UserQuestions from './components/UserQuestions';
import LlmQuestions from './components/LlmQuestions';
import { AuthProvider, useAuth } from './context/AuthContext';
import './index.css';
import './components/Login.css';
import './components/Questions.css';
import TemplateDetails from "./components/TemplateDetails";
import SessionBuilder from './components/SessionBuilder';
import InterviewSimulation from './components/InterviewSimulation';
import SessionJoinForm from './components/SessionJoinForm';
import EvaluationDashboard from './components/EvaluationDashboard';
import EvaluationSession from './components/EvaluationSession';
import EvaluationResults from './components/EvaluationResults';

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
    const apiUrl = getApiUrl()

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

  // Define the single feature to be displayed.
  const fallbackFeatures = [
    {
      name: "Interview questions",
      description: "Common technical questions to prepare for your interview."
    }
  ];

  // This function now filters for and formats only the "Interview questions" feature.
  const formatApiFeatures = (features) => {
    const interviewFeatureName = features.find(f => f.toLowerCase().includes('interview question'));
    if (interviewFeatureName) {
      return [{
        name: interviewFeatureName,
        description: "Common technical questions to prepare for your interview."
      }];
    }
    return [];
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
          path={"/templates"}
          element={
            <ProtectedRoute>
              <TemplatesGallery />
            </ProtectedRoute>
          }
        />

        <Route
            path="/template/:templateId"
            element={
              <ProtectedRoute>
                <TemplateDetails />
              </ProtectedRoute>
          }
        />

        <Route
            path="/interview/new"
            element={
              <ProtectedRoute>
                <InterviewSimulation />
              </ProtectedRoute>
          }
        />

        <Route
            path="/interview/:sessionId"
            element={
              <ProtectedRoute>
                <InterviewSimulation />
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

        {/* Session Management Routes */}
        <Route
          path="/sessions"
          element={
            <ProtectedRoute>
              <SessionJoinForm />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/session/:sessionCode"
          element={
            <ProtectedRoute>
              <SessionBuilder />
            </ProtectedRoute>
          }
        />

        {/* Evaluation Routes */}
        <Route
          path="/evaluations"
          element={
            <ProtectedRoute>
              <EvaluationDashboard />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/evaluations/session/:sessionId"
          element={
            <ProtectedRoute>
              <EvaluationSession />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/evaluations/results/:evaluationId"
          element={
            <ProtectedRoute>
              <EvaluationResults />
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