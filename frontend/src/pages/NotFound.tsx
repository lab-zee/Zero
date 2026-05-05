import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Heading,
  Text,
  VStack,
  Container,
  useColorModeValue,
} from '@chakra-ui/react';

const NotFound = () => {
  const navigate = useNavigate();
  const bgColor = useColorModeValue('gray.50', 'gray.900');

  return (
    <Box minH="100vh" bg={bgColor} display="flex" alignItems="center" justifyContent="center">
      <Container maxW="md">
        <VStack spacing={6} textAlign="center">
          <Heading size="4xl" color="blue.500">
            404
          </Heading>
          <Heading size="lg">Page Not Found</Heading>
          <Text color="gray.400" fontSize="lg">
            The page you're looking for doesn't exist or has been moved.
          </Text>
          <VStack spacing={3} pt={4}>
            <Button
              colorScheme="blue"
              size="lg"
              onClick={() => navigate('/chat')}
            >
              Go to Chat
            </Button>
            <Button
              variant="ghost"
              onClick={() => navigate(-1)}
            >
              Go Back
            </Button>
          </VStack>
        </VStack>
      </Container>
    </Box>
  );
};

export default NotFound;
