import { useToast as useChakraToast, UseToastOptions } from '@chakra-ui/react';
import { getErrorMessage } from '../utils/errorHandling';

interface CustomToastOptions extends Omit<UseToastOptions, 'title' | 'description'> {
  title?: string;
  description?: string;
}

export const useCustomToast = () => {
  const toast = useChakraToast();

  const showSuccess = (message: string, options?: CustomToastOptions) => {
    toast({
      title: 'Success',
      description: message,
      status: 'success',
      duration: 4000,
      isClosable: true,
      position: 'top-right',
      ...options,
    });
  };

  const showError = (error: unknown, options?: CustomToastOptions) => {
    const message = typeof error === 'string' ? error : getErrorMessage(error);

    toast({
      title: 'Error',
      description: message,
      status: 'error',
      duration: 6000,
      isClosable: true,
      position: 'top-right',
      ...options,
    });
  };

  const showWarning = (message: string, options?: CustomToastOptions) => {
    toast({
      title: 'Warning',
      description: message,
      status: 'warning',
      duration: 5000,
      isClosable: true,
      position: 'top-right',
      ...options,
    });
  };

  const showInfo = (message: string, options?: CustomToastOptions) => {
    toast({
      title: 'Info',
      description: message,
      status: 'info',
      duration: 4000,
      isClosable: true,
      position: 'top-right',
      ...options,
    });
  };

  return {
    success: showSuccess,
    error: showError,
    warning: showWarning,
    info: showInfo,
    toast, // Expose original toast for custom usage
  };
};
