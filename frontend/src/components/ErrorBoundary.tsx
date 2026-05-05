import React, { Component, ErrorInfo, ReactNode } from 'react';
import {
  Box,
  Button,
  Container,
  Heading,
  Text,
  VStack,
  useColorModeValue,
  Code,
} from '@chakra-ui/react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onReset={this.handleReset}
          onGoHome={this.handleGoHome}
        />
      );
    }

    return this.props.children;
  }
}

interface ErrorFallbackProps {
  error: Error | null;
  errorInfo: ErrorInfo | null;
  onReset: () => void;
  onGoHome: () => void;
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  errorInfo,
  onReset,
  onGoHome,
}) => {
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');

  return (
    <Box minH="100vh" bg={bgColor} py={12}>
      <Container maxW="container.md">
        <VStack
          spacing={6}
          bg={cardBg}
          p={8}
          borderRadius="lg"
          boxShadow="lg"
          align="stretch"
        >
          <VStack spacing={3} align="center">
            <Heading size="lg" color="red.500">
              Something went wrong
            </Heading>
            <Text color="gray.400" textAlign="center">
              We encountered an unexpected error. This has been logged for investigation.
            </Text>
          </VStack>

          {error && (
            <Box>
              <Text fontWeight="semibold" mb={2}>
                Error details:
              </Text>
              <Code
                display="block"
                p={4}
                borderRadius="md"
                bg={useColorModeValue('gray.100', 'gray.700')}
                whiteSpace="pre-wrap"
                fontSize="sm"
              >
                {error.message}
              </Code>
            </Box>
          )}

          {process.env.NODE_ENV === 'development' && errorInfo && (
            <Box>
              <Text fontWeight="semibold" mb={2}>
                Stack trace:
              </Text>
              <Code
                display="block"
                p={4}
                borderRadius="md"
                bg={useColorModeValue('gray.100', 'gray.700')}
                whiteSpace="pre-wrap"
                fontSize="xs"
                maxH="200px"
                overflowY="auto"
              >
                {errorInfo.componentStack}
              </Code>
            </Box>
          )}

          <VStack spacing={3}>
            <Button colorScheme="blue" width="full" onClick={onReset}>
              Try Again
            </Button>
            <Button variant="outline" width="full" onClick={onGoHome}>
              Go to Home
            </Button>
          </VStack>
        </VStack>
      </Container>
    </Box>
  );
};

export default ErrorBoundary;
