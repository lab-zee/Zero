import axios, { AxiosError } from 'axios';

export interface APIError {
  message: string;
  code?: string;
  details?: any;
  statusCode?: number;
}

/**
 * Convert error to user-friendly message
 */
export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<APIError>;

    if (axiosError.response?.data?.message) {
      return axiosError.response.data.message;
    }

    if (axiosError.response?.status) {
      return getStatusCodeMessage(axiosError.response.status);
    }

    if (axiosError.code === 'ECONNABORTED') {
      return 'Request timed out. Please try again.';
    }

    if (axiosError.code === 'ERR_NETWORK') {
      return 'Unable to connect to the server. Please check your internet connection.';
    }

    if (axiosError.message) {
      return axiosError.message;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred. Please try again.';
};

/**
 * Get user-friendly message for HTTP status codes
 */
export const getStatusCodeMessage = (statusCode: number): string => {
  switch (statusCode) {
    case 400:
      return 'Invalid request. Please check your input and try again.';
    case 401:
      return 'Session expired. Please log in again.';
    case 403:
      return "You don't have permission to perform this action.";
    case 404:
      return 'The requested resource was not found.';
    case 409:
      return 'This resource already exists or conflicts with another resource.';
    case 413:
      return 'File or request is too large. Please reduce the size and try again.';
    case 429:
      return 'Too many requests. Please wait a moment and try again.';
    case 500:
      return 'Server error. Our team has been notified.';
    case 502:
      return 'Service temporarily unavailable. Please try again in a moment.';
    case 503:
      return 'Service is currently undergoing maintenance. Please try again later.';
    case 504:
      return 'Request timed out. The server took too long to respond.';
    default:
      return 'Something went wrong. Please try again.';
  }
};

/**
 * Extract error details from API error
 */
export const getErrorDetails = (error: unknown): APIError | null => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<APIError>;
    return {
      message: getErrorMessage(error),
      code: axiosError.response?.data?.code || axiosError.code,
      details: axiosError.response?.data?.details,
      statusCode: axiosError.response?.status,
    };
  }

  return null;
};

/**
 * Check if error is a network error
 */
export const isNetworkError = (error: unknown): boolean => {
  if (axios.isAxiosError(error)) {
    return (
      error.code === 'ERR_NETWORK' ||
      error.code === 'ECONNABORTED' ||
      error.message === 'Network Error'
    );
  }
  return false;
};

/**
 * Check if error is an authentication error
 */
export const isAuthError = (error: unknown): boolean => {
  if (axios.isAxiosError(error)) {
    return error.response?.status === 401;
  }
  return false;
};

/**
 * Check if error is a permission error
 */
export const isPermissionError = (error: unknown): boolean => {
  if (axios.isAxiosError(error)) {
    return error.response?.status === 403;
  }
  return false;
};

/**
 * Check if error is a validation error
 */
export const isValidationError = (error: unknown): boolean => {
  if (axios.isAxiosError(error)) {
    return error.response?.status === 400 || error.response?.status === 422;
  }
  return false;
};

/**
 * Retry function with exponential backoff
 */
export const retryWithBackoff = async <T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> => {
  let lastError: unknown;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (!isNetworkError(error) || attempt === maxRetries - 1) {
        throw error;
      }

      const delay = baseDelay * Math.pow(2, attempt);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError;
};
