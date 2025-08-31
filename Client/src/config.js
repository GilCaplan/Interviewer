// Centralized configuration file for environment variables
// All environment-dependent values should be defined here

const config = {
  // API URL construction - uses environment variables
  get API_URL() {
    // Use REACT_APP_API_URL if defined (recommended approach)
    if (process.env.REACT_APP_API_URL) {
      return process.env.REACT_APP_API_URL;
    }
    
    // For Docker environments, use the service name 'server'
    if (process.env.NODE_ENV === 'development' && window.location.hostname !== 'localhost') {
      const port = process.env.REACT_APP_SERVER_PORT || process.env.SERVER_PORT || '5001';
      return `http://server:${port}`;
    }
    
    // Fallback to localhost with configurable port
    const port = process.env.REACT_APP_SERVER_PORT || process.env.SERVER_PORT || '5001';
    return `http://localhost:${port}`;
  },
  
  // WebSocket URL construction  
  get WS_URL() {
    // Use REACT_APP_WS_URL if defined (recommended approach)
    if (process.env.REACT_APP_WS_URL) {
      return process.env.REACT_APP_WS_URL;
    }
    
    // For Docker environments, use the service name 'server'
    if (process.env.NODE_ENV === 'development' && window.location.hostname !== 'localhost') {
      const port = process.env.REACT_APP_SERVER_PORT || process.env.SERVER_PORT || '5001';
      return `ws://server:${port}`;
    }
    
    // Fallback to localhost with configurable port
    const port = process.env.REACT_APP_SERVER_PORT || process.env.SERVER_PORT || '5001';
    return `ws://localhost:${port}`;
  }
};

export default config;