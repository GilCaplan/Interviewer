import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function Login() {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleLogin = async (e) => {
    e.preventDefault();

    if (!username.trim()) {
      setError('Username cannot be empty');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Get API URL from environment or use default
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';

      const response = await fetch(`${apiUrl}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username }),
        credentials: 'include' // Important for cookies
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Login failed');
      }

      const data = await response.json();

      // Store the user data in localStorage
      localStorage.setItem('user', JSON.stringify({
        username: data.username,
        sessionToken: data.token
      }));
      
      // Also store token separately for easy access
      localStorage.setItem('token', data.token);

      // Call the login function from AuthContext
      login({
        username: data.username,
        sessionToken: data.token
      });

      // Redirect to home
      navigate('/');
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGuestLogin = () => {
    // Generate a random guest username
    const guestUsername = `Guest_${Math.floor(Math.random() * 10000)}`;
    setUsername(guestUsername);
    // Submit the form
    handleLogin({ preventDefault: () => {} });
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h2>Welcome to Interview Assistant</h2>
        <p>Log in to track your progress and access all features</p>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              disabled={loading}
            />
          </div>

          <div className="login-buttons">
            <button
              type="submit"
              className="login-button"
              disabled={loading}
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>

            <button
              type="button"
              className="guest-button"
              onClick={handleGuestLogin}
              disabled={loading}
            >
              Continue as Guest
            </button>
          </div>
        </form>

        <div className="login-footer">
          <p>No account needed to get started!</p>
          <p className="login-note">* More login options coming soon</p>
        </div>
      </div>
    </div>
  );
}

export default Login;