// Centralized configuration file for environment variables
// All environment-dependent values should be defined here

const config = {
  // Server configuration - pulled from environment
  SERVER_PORT: process.env.REACT_APP_SERVER_PORT,
  
  // API URL construction
  get API_URL() {
    // For Docker environments, use the service name 'server'
    if (process.env.NODE_ENV === 'development' && window.location.hostname !== 'localhost') {
      return 'http://server:5001';
    }
    
    const port = this.SERVER_PORT;
    if (!port) {
      console.warn('REACT_APP_SERVER_PORT environment variable is not defined, using default port 5001');
      return 'http://localhost:5001';
    }
    return `http://localhost:${port}`;
  },
  
  // WebSocket URL construction  
  get WS_URL() {
    // For Docker environments, use the service name 'server'
    if (process.env.NODE_ENV === 'development' && window.location.hostname !== 'localhost') {
      return 'ws://server:5001';
    }
    
    const port = this.SERVER_PORT;
    if (!port) {
      console.warn('REACT_APP_SERVER_PORT environment variable is not defined, using default port 5001');
      return 'ws://localhost:5001';
    }
    return `ws://localhost:${port}`;
  }
};

export default config;