import React from 'react';
import {
  Box,
  Spinner,
  Text,
  VStack,
  useColorModeValue,
} from '@chakra-ui/react';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  fullScreen?: boolean;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message,
  size = 'xl',
  fullScreen = false,
}) => {
  const bgColor = useColorModeValue('white', 'gray.800');

  const content = (
    <VStack spacing={4}>
      <Spinner
        size={size}
        thickness="4px"
        speed="0.65s"
        color="blue.500"
      />
      {message && (
        <Text color="gray.400" fontSize="sm">
          {message}
        </Text>
      )}
    </VStack>
  );

  if (fullScreen) {
    return (
      <Box
        display="flex"
        alignItems="center"
        justifyContent="center"
        minH="100vh"
        bg={bgColor}
      >
        {content}
      </Box>
    );
  }

  return (
    <Box
      display="flex"
      alignItems="center"
      justifyContent="center"
      p={8}
    >
      {content}
    </Box>
  );
};

export default LoadingSpinner;
