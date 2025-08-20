import { getApiUrl, getAuthToken } from './authUtils';

/**
 * A wrapper around the native fetch API that simplifies making authenticated API calls
 * and provides consistent, detailed error handling.
 *
 * @param {string} endpoint - The API endpoint to call (e.g., '/api/sessions/123').
 * @param {object} options - The options object for the fetch call (method, body, etc.).
 * @returns {Promise<any>} - A promise that resolves with the JSON response data.
 * @throws {Error} - Throws a detailed error if the network request fails or the server returns an error.
 */
export const fetchApi = async (endpoint, options = {}) => {
  const apiUrl = getApiUrl();
  const token = getAuthToken();

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${apiUrl}${endpoint}`, { ...options, headers });

  if (!response.ok) {
    let errorMessage = `Request failed with status: ${response.status}`;
    try {
      // Try to parse the JSON body of the error response for more details
      const errorJson = await response.json();
      errorMessage = errorJson.error || 'An unknown error occurred.';
      if (errorJson.reason) {
        errorMessage += ` Reason: ${errorJson.reason}`;
      }
    } catch (e) {
      // Fallback if the body isn't JSON or another error occurs
    }
    throw new Error(errorMessage);
  }

  // If the response is OK but has no content (e.g., a 204 response)
  if (response.status === 204) {
    return null;
  }

  return response.json();
};