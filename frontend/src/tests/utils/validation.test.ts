import { describe, it, expect } from 'vitest';
import {
  validateEmail,
  validateUrl,
  validateRequired,
  validateMinLength,
  validateMaxLength,
  validatePassword,
} from '../../utils/validation';

describe('Validation Utilities', () => {
  describe('validateEmail', () => {
    it('validates correct email addresses', () => {
      expect(validateEmail('test@example.com').isValid).toBe(true);
      expect(validateEmail('user.name@domain.co.uk').isValid).toBe(true);
      expect(validateEmail('user+tag@example.com').isValid).toBe(true);
    });

    it('invalidates incorrect email addresses', () => {
      expect(validateEmail('invalid').isValid).toBe(false);
      expect(validateEmail('invalid@').isValid).toBe(false);
      expect(validateEmail('@example.com').isValid).toBe(false);
      expect(validateEmail('test@').isValid).toBe(false);
    });

    it('handles empty string', () => {
      const result = validateEmail('');
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Email is required');
    });
  });

  describe('validateUrl', () => {
    it('validates correct URLs', () => {
      expect(validateUrl('https://example.com').isValid).toBe(true);
      expect(validateUrl('http://test.co.uk').isValid).toBe(true);
      expect(validateUrl('https://sub.domain.com/path').isValid).toBe(true);
    });

    it('invalidates incorrect URLs', () => {
      expect(validateUrl('example.com').isValid).toBe(true); // auto-prepends https://
      expect(validateUrl('ftp://example.com').isValid).toBe(false);
    });
  });

  describe('validateRequired', () => {
    it('passes for non-empty values', () => {
      expect(validateRequired('value', 'Field').isValid).toBe(true);
      expect(validateRequired('  text  ', 'Field').isValid).toBe(true);
    });

    it('fails for empty values', () => {
      const result1 = validateRequired('', 'Field');
      expect(result1.isValid).toBe(false);
      expect(result1.error).toBe('Field is required');

      const result2 = validateRequired('   ', 'Field');
      expect(result2.isValid).toBe(false);
      expect(result2.error).toBe('Field is required');
    });
  });

  describe('validateMinLength', () => {
    it('passes for strings meeting minimum length', () => {
      expect(validateMinLength('hello', 3, 'Field').isValid).toBe(true);
      expect(validateMinLength('test', 4, 'Field').isValid).toBe(true);
    });

    it('fails for strings below minimum length', () => {
      const result = validateMinLength('ab', 3, 'Field');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('at least 3 characters');
    });
  });

  describe('validateMaxLength', () => {
    it('passes for strings within maximum length', () => {
      expect(validateMaxLength('hello', 10, 'Field').isValid).toBe(true);
      expect(validateMaxLength('test', 4, 'Field').isValid).toBe(true);
    });

    it('fails for strings exceeding maximum length', () => {
      const result = validateMaxLength('toolong', 5, 'Field');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('characters or less');
    });
  });

  describe('validatePassword', () => {
    it('validates strong passwords', () => {
      expect(validatePassword('Strong123!').isValid).toBe(true);
      expect(validatePassword('MyP@ssw0rd').isValid).toBe(true);
    });

    it('rejects weak passwords', () => {
      expect(validatePassword('weak').isValid).toBe(false);
      expect(validatePassword('12345678').isValid).toBe(false);
      expect(validatePassword('password').isValid).toBe(false);
    });

    it('requires minimum length', () => {
      const result = validatePassword('Sh0rt!');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('at least 8 characters');
    });
  });
});
