// Authentication utility functions for consistent token management
import config from '../config';

export const getAuthToken = () => {
  // Try multiple sources for backward compatibility
  let token = localStorage.getItem('token');
  
  if (!token) {
    // Fallback to user object
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        const userData = JSON.parse(storedUser);
        token = userData.sessionToken;
      } catch (e) {
        console.error('Failed to parse stored user data:', e);
      }
    }
  }
  
  return token;
};

export const getApiUrl = () => {
  return config.API_URL;
};

export const getWsUrl = () => {
  return config.WS_URL;
};

export const createAuthHeaders = (token = null) => {
  const authToken = token || getAuthToken();
  const headers = {
    'Content-Type': 'application/json'
  };
  
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  
  return headers;
};

export const makeAuthenticatedRequest = async (url, options = {}) => {
  const token = getAuthToken();
  
  if (!token) {
    throw new Error('No authentication token available');
  }
  
  const requestOptions = {
    ...options,
    headers: {
      ...createAuthHeaders(token),
      ...options.headers
    }
  };
  
  const response = await fetch(url, requestOptions);
  
  // Handle common auth errors
  if (response.status === 401) {
    // Token might be expired, clear it
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    throw new Error('Authentication expired. Please login again.');
  }
  
  return response;
};