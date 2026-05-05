import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  Heading,
  Text,
  Container,
  FormErrorMessage,
  FormHelperText,
} from '@chakra-ui/react';
import { FiArrowLeft } from 'react-icons/fi';
import { authAPI } from '../services/api';
import { useCustomToast } from '../hooks/useToast';
import { validatePassword, validateRequired } from '../utils/validation';
import { APP_CONFIG } from '../config';

const ResetPassword = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const toast = useCustomToast();
  const tokenFromUrl = searchParams.get('token') || '';

  const [token, setToken] = useState(tokenFromUrl);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<{ token?: string; newPassword?: string; confirmPassword?: string }>({});
  const [loading, setLoading] = useState(false);

  const validateForm = (): boolean => {
    const newErrors: { token?: string; newPassword?: string; confirmPassword?: string } = {};

    const tokenValidation = validateRequired(token, 'Reset token');
    if (!tokenValidation.isValid) {
      newErrors.token = tokenValidation.error;
    }

    const passwordValidation = validatePassword(newPassword);
    if (!passwordValidation.isValid) {
      newErrors.newPassword = passwordValidation.error;
    }

    if (newPassword !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      toast.error('Please fix the errors in the form');
      return;
    }

    setLoading(true);

    try {
      await authAPI.resetPassword(token.trim(), newPassword);
      toast.success('Password reset successful. Please sign in with your new password.');
      navigate('/login');
    } catch (err) {
      toast.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box minH="100vh" bg="surface.950" display="flex" alignItems="center" justifyContent="center">
      <Container maxW="sm">
        <Button
          variant="ghost"
          size="sm"
          color="gray.400"
          leftIcon={<FiArrowLeft />}
          onClick={() => navigate('/login')}
          mb={8}
          _hover={{ color: 'gray.300' }}
        >
          Back to Login
        </Button>
        <Box
          w="100%"
          p={8}
          bg="surface.800"
          borderWidth="1px"
          borderColor="whiteAlpha.100"
          borderRadius="xl"
        >
          <VStack spacing={6}>
            <VStack spacing={1}>
              <Text fontSize="lg" fontWeight="700" color="brand.400">
                {APP_CONFIG.name}
              </Text>
              <Heading size="md" color="gray.100">
                Reset Password
              </Heading>
              <Text fontSize="sm" color="gray.400" textAlign="center">
                Enter your reset token and choose a new password
              </Text>
            </VStack>
            <form onSubmit={handleSubmit} style={{ width: '100%' }}>
              <VStack spacing={4}>
                <FormControl isRequired isInvalid={!!errors.token}>
                  <FormLabel fontSize="sm" color="gray.300">Reset Token</FormLabel>
                  <Input
                    value={token}
                    onChange={(e) => {
                      setToken(e.target.value);
                      if (errors.token) setErrors({ ...errors, token: undefined });
                    }}
                    placeholder="Paste your reset token"
                  />
                  {errors.token && <FormErrorMessage>{errors.token}</FormErrorMessage>}
                  <FormHelperText color="gray.500" fontSize="xs">
                    This token was provided by your administrator
                  </FormHelperText>
                </FormControl>
                <FormControl isRequired isInvalid={!!errors.newPassword}>
                  <FormLabel fontSize="sm" color="gray.300">New Password</FormLabel>
                  <Input
                    type="password"
                    value={newPassword}
                    onChange={(e) => {
                      setNewPassword(e.target.value);
                      if (errors.newPassword) setErrors({ ...errors, newPassword: undefined });
                    }}
                    placeholder="Enter new password"
                  />
                  {errors.newPassword && <FormErrorMessage>{errors.newPassword}</FormErrorMessage>}
                  <FormHelperText color="gray.500" fontSize="xs">
                    Min 8 chars, with uppercase, lowercase, and a number
                  </FormHelperText>
                </FormControl>
                <FormControl isRequired isInvalid={!!errors.confirmPassword}>
                  <FormLabel fontSize="sm" color="gray.300">Confirm Password</FormLabel>
                  <Input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (errors.confirmPassword) setErrors({ ...errors, confirmPassword: undefined });
                    }}
                    placeholder="Confirm new password"
                  />
                  {errors.confirmPassword && <FormErrorMessage>{errors.confirmPassword}</FormErrorMessage>}
                </FormControl>
                <Button
                  type="submit"
                  width="100%"
                  isLoading={loading}
                  isDisabled={!token.trim() || !newPassword || !confirmPassword}
                  bg="brand.500"
                  color="white"
                  _hover={{ bg: 'brand.400' }}
                  mt={2}
                >
                  Reset Password
                </Button>
              </VStack>
            </form>
            <Text fontSize="sm" color="gray.400">
              Remember your password?{' '}
              <Link to="/login">
                <Text as="span" color="brand.400" fontWeight="500">
                  Sign in
                </Text>
              </Link>
            </Text>
          </VStack>
        </Box>
      </Container>
    </Box>
  );
};

export default ResetPassword;
