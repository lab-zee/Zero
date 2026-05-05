import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
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
} from '@chakra-ui/react';
import { FiArrowLeft } from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { authAPI } from '../services/api';
import { useCustomToast } from '../hooks/useToast';
import { validateEmail, validateRequired } from '../utils/validation';
import { APP_CONFIG } from '../config';

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const toast = useCustomToast();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [loading, setLoading] = useState(false);

  const validateForm = (): boolean => {
    const newErrors: { email?: string; password?: string } = {};

    const emailValidation = validateEmail(email);
    if (!emailValidation.isValid) {
      newErrors.email = emailValidation.error;
    }

    const passwordValidation = validateRequired(password, 'Password');
    if (!passwordValidation.isValid) {
      newErrors.password = passwordValidation.error;
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
      const user = await authAPI.login({ email: email.trim(), password });
      login(user);
      toast.success('Login successful');
      navigate('/chat');
    } catch (err) {
      toast.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleEmailChange = (value: string) => {
    setEmail(value);
    if (errors.email) {
      setErrors({ ...errors, email: undefined });
    }
  };

  const handlePasswordChange = (value: string) => {
    setPassword(value);
    if (errors.password) {
      setErrors({ ...errors, password: undefined });
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
          onClick={() => navigate('/')}
          mb={8}
          _hover={{ color: 'gray.300' }}
        >
          Back
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
                Welcome back
              </Heading>
              <Text fontSize="sm" color="gray.400">
                Sign in to your account
              </Text>
            </VStack>
            <form onSubmit={handleSubmit} style={{ width: '100%' }}>
              <VStack spacing={4}>
                <FormControl isRequired isInvalid={!!errors.email}>
                  <FormLabel fontSize="sm" color="gray.300">Email</FormLabel>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => handleEmailChange(e.target.value)}
                    placeholder="your@email.com"
                  />
                  {errors.email && <FormErrorMessage>{errors.email}</FormErrorMessage>}
                </FormControl>
                <FormControl isRequired isInvalid={!!errors.password}>
                  <FormLabel fontSize="sm" color="gray.300">Password</FormLabel>
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => handlePasswordChange(e.target.value)}
                    placeholder="Enter your password"
                  />
                  {errors.password && <FormErrorMessage>{errors.password}</FormErrorMessage>}
                </FormControl>
                <Button
                  type="submit"
                  width="100%"
                  isLoading={loading}
                  isDisabled={!email.trim() || !password}
                  bg="brand.500"
                  color="white"
                  _hover={{ bg: 'brand.400' }}
                  mt={2}
                >
                  Sign In
                </Button>
              </VStack>
            </form>
            <Text fontSize="sm" color="gray.400">
              Don't have an account?{' '}
              <Link to="/register">
                <Text as="span" color="brand.400" fontWeight="500">
                  Create one
                </Text>
              </Link>
            </Text>
            <Text fontSize="sm" color="gray.400">
              Forgot your password?{' '}
              <Link to="/reset-password">
                <Text as="span" color="brand.400" fontWeight="500">
                  Reset it here
                </Text>
              </Link>
            </Text>
          </VStack>
        </Box>
      </Container>
    </Box>
  );
};

export default Login;
