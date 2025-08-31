// Input validation and sanitization utilities

export const sanitizeInput = (input) => {
  if (typeof input !== 'string') return '';
  
  // Remove HTML tags and script content
  return input
    .replace(/<script[^>]*>.*?<\/script>/gi, '')
    .replace(/<[^>]*>/g, '')
    .replace(/javascript:/gi, '')
    .replace(/on\w+\s*=/gi, '')
    .trim();
};

export const validateUsername = (username) => {
  const cleaned = sanitizeInput(username);
  const errors = [];
  
  if (!cleaned) {
    errors.push('Username is required');
  } else if (cleaned.length < 3) {
    errors.push('Username must be at least 3 characters');
  } else if (cleaned.length > 30) {
    errors.push('Username must be less than 30 characters');
  } else if (!/^[a-zA-Z0-9_]+$/.test(cleaned)) {
    errors.push('Username can only contain letters, numbers, and underscores');
  }
  
  return { isValid: errors.length === 0, errors, cleanValue: cleaned };
};

export const validateSessionCode = (sessionCode) => {
  const cleaned = sanitizeInput(sessionCode.toUpperCase());
  const errors = [];
  
  if (!cleaned) {
    errors.push('Session code is required');
  } else if (!/^[A-Z0-9]{6}$/.test(cleaned)) {
    errors.push('Session code must be exactly 6 characters (letters and numbers only)');
  }
  
  return { isValid: errors.length === 0, errors, cleanValue: cleaned };
};

export const validatePassword = (password) => {
  const errors = [];
  
  if (password && password.length > 0) {
    if (password.length < 4) {
      errors.push('Password must be at least 4 characters');
    } else if (password.length > 50) {
      errors.push('Password must be less than 50 characters');
    }
    
    // Check for suspicious patterns
    // eslint-disable-next-line no-script-url
    const suspiciousPatterns = ['<script', 'javascript:', 'drop table', '<img'];
    for (const pattern of suspiciousPatterns) {
      if (password.toLowerCase().includes(pattern)) {
        errors.push('Password contains invalid characters');
        break;
      }
    }
  }
  
  return { isValid: errors.length === 0, errors };
};

export const validateSessionTitle = (title) => {
  const cleaned = sanitizeInput(title);
  const errors = [];
  
  if (!cleaned) {
    errors.push('Session title is required');
  } else if (cleaned.length < 3) {
    errors.push('Session title must be at least 3 characters');
  } else if (cleaned.length > 100) {
    errors.push('Session title must be less than 100 characters');
  }
  
  return { isValid: errors.length === 0, errors, cleanValue: cleaned };
};

export const validateDescription = (description) => {
  const cleaned = sanitizeInput(description);
  const errors = [];
  
  if (cleaned.length > 500) {
    errors.push('Description must be less than 500 characters');
  }
  
  return { isValid: errors.length === 0, errors, cleanValue: cleaned };
};