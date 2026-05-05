/**
 * Reusable validation utilities for form inputs
 */

export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

/**
 * Validates email format
 */
export const validateEmail = (email: string): ValidationResult => {
  const trimmed = email.trim();

  if (!trimmed) {
    return { isValid: false, error: 'Email is required' };
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(trimmed)) {
    return { isValid: false, error: 'Please enter a valid email address' };
  }

  return { isValid: true };
};

/**
 * Validates URL format
 */
export const validateUrl = (url: string): ValidationResult => {
  const trimmed = url.trim();

  if (!trimmed) {
    return { isValid: false, error: 'URL is required' };
  }

  try {
    // Check if URL already has a protocol
    const hasProtocol = /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(trimmed);
    const urlToValidate = hasProtocol ? trimmed : `https://${trimmed}`;

    const urlObj = new URL(urlToValidate);
    if (!['http:', 'https:'].includes(urlObj.protocol)) {
      return { isValid: false, error: 'URL must use http or https protocol' };
    }
    return { isValid: true };
  } catch {
    return { isValid: false, error: 'Please enter a valid URL (e.g., https://example.com)' };
  }
};

/**
 * Validates required field
 */
export const validateRequired = (value: string, fieldName: string = 'This field'): ValidationResult => {
  const trimmed = value?.trim();

  if (!trimmed) {
    return { isValid: false, error: `${fieldName} is required` };
  }

  return { isValid: true };
};

/**
 * Validates minimum length
 */
export const validateMinLength = (
  value: string,
  minLength: number,
  fieldName: string = 'This field'
): ValidationResult => {
  const trimmed = value?.trim();

  if (!trimmed) {
    return { isValid: false, error: `${fieldName} is required` };
  }

  if (trimmed.length < minLength) {
    return {
      isValid: false,
      error: `${fieldName} must be at least ${minLength} characters long`
    };
  }

  return { isValid: true };
};

/**
 * Validates maximum length
 */
export const validateMaxLength = (
  value: string,
  maxLength: number,
  fieldName: string = 'This field'
): ValidationResult => {
  const trimmed = value?.trim();

  if (trimmed && trimmed.length > maxLength) {
    return {
      isValid: false,
      error: `${fieldName} must be ${maxLength} characters or less`
    };
  }

  return { isValid: true };
};

/**
 * Validates password strength
 */
export const validatePassword = (password: string): ValidationResult => {
  if (!password) {
    return { isValid: false, error: 'Password is required' };
  }

  if (password.length < 8) {
    return { isValid: false, error: 'Password must be at least 8 characters long' };
  }

  if (!/[A-Z]/.test(password)) {
    return { isValid: false, error: 'Password must contain at least one uppercase letter' };
  }

  if (!/[a-z]/.test(password)) {
    return { isValid: false, error: 'Password must contain at least one lowercase letter' };
  }

  if (!/[0-9]/.test(password)) {
    return { isValid: false, error: 'Password must contain at least one number' };
  }

  return { isValid: true };
};

/**
 * Validates file size
 */
export const validateFileSize = (
  file: File,
  maxSizeMB: number = 10
): ValidationResult => {
  const maxSizeBytes = maxSizeMB * 1024 * 1024;

  if (file.size > maxSizeBytes) {
    return {
      isValid: false,
      error: `File size must be ${maxSizeMB}MB or less (current: ${(file.size / 1024 / 1024).toFixed(2)}MB)`
    };
  }

  return { isValid: true };
};

/**
 * Validates file type
 */
export const validateFileType = (
  file: File,
  allowedTypes: string[]
): ValidationResult => {
  const fileExtension = file.name.split('.').pop()?.toLowerCase();

  if (!fileExtension || !allowedTypes.includes(fileExtension)) {
    return {
      isValid: false,
      error: `File type must be one of: ${allowedTypes.join(', ')}`
    };
  }

  return { isValid: true };
};

/**
 * Custom error message formatter
 */
export const formatErrorMessage = (field: string, error: string): string => {
  return `${field}: ${error}`;
};

/**
 * Combine multiple validation results
 */
export const combineValidations = (...results: ValidationResult[]): ValidationResult => {
  const firstError = results.find(r => !r.isValid);

  if (firstError) {
    return firstError;
  }

  return { isValid: true };
};
