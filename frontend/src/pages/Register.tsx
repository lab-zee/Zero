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
  FormHelperText,
} from '@chakra-ui/react';
import { FiArrowLeft } from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { authAPI } from '../services/api';
import { useCustomToast } from '../hooks/useToast';
import { validateEmail, validatePassword, validateRequired, validateMinLength } from '../utils/validation';
import { APP_CONFIG } from '../config';

const Register = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const toast = useCustomToast();
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<{ email?: string; username?: string; password?: string }>({});
  const [loading, setLoading] = useState(false);

  const validateForm = (): boolean => {
    const newErrors: { email?: string; username?: string; password?: string } = {};

    const emailValidation = validateEmail(email);
    if (!emailValidation.isValid) {
      newErrors.email = emailValidation.error;
    }

    const usernameValidation = validateRequired(username, 'Username');
    if (!usernameValidation.isValid) {
      newErrors.username = usernameValidation.error;
    } else {
      const minLengthValidation = validateMinLength(username, 3, 'Username');
      if (!minLengthValidation.isValid) {
        newErrors.username = minLengthValidation.error;
      }
    }

    const passwordValidation = validatePassword(password);
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
      const user = await authAPI.register({
        email: email.trim(),
        username: username.trim(),
        password
      });
      login(user);
      toast.success('Registration successful');
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

  const handleUsernameChange = (value: string) => {
    setUsername(value);
    if (errors.username) {
      setErrors({ ...errors, username: undefined });
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
                Create an account
              </Heading>
              <Text fontSize="sm" color="gray.400">
                Get started with {APP_CONFIG.name}
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
                <FormControl isRequired isInvalid={!!errors.username}>
                  <FormLabel fontSize="sm" color="gray.300">Username</FormLabel>
                  <Input
                    type="text"
                    value={username}
                    onChange={(e) => handleUsernameChange(e.target.value)}
                    placeholder="Choose a username"
                  />
                  <FormHelperText color="gray.400" fontSize="xs">At least 3 characters</FormHelperText>
                  {errors.username && <FormErrorMessage>{errors.username}</FormErrorMessage>}
                </FormControl>
                <FormControl isRequired isInvalid={!!errors.password}>
                  <FormLabel fontSize="sm" color="gray.300">Password</FormLabel>
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => handlePasswordChange(e.target.value)}
                    placeholder="Create a password"
                  />
                  <FormHelperText color="gray.400" fontSize="xs">
                    At least 8 characters with uppercase, lowercase, and number
                  </FormHelperText>
                  {errors.password && <FormErrorMessage>{errors.password}</FormErrorMessage>}
                </FormControl>
                <Button
                  type="submit"
                  width="100%"
                  isLoading={loading}
                  isDisabled={!email.trim() || !username.trim() || !password}
                  bg="brand.500"
                  color="white"
                  _hover={{ bg: 'brand.400' }}
                  mt={2}
                >
                  Create Account
                </Button>
              </VStack>
            </form>
            <Text fontSize="sm" color="gray.400">
              Already have an account?{' '}
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

export default Register;
