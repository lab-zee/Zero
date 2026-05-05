import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  VStack,
  HStack,
  Heading,
  Container,
  FormErrorMessage,
} from '@chakra-ui/react';
import { useAuth } from '../contexts/AuthContext';
import { organizationAPI } from '../services/api';
import { useCustomToast } from '../hooks/useToast';
import { validateRequired, validateMinLength, validateMaxLength } from '../utils/validation';

const CreateOrganization = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const toast = useCustomToast();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<{ name?: string; description?: string }>({});

  const validateForm = (): boolean => {
    const newErrors: { name?: string; description?: string } = {};

    const nameValidation = validateRequired(name, 'Organization name');
    if (!nameValidation.isValid) {
      newErrors.name = nameValidation.error;
    } else {
      const minLengthValidation = validateMinLength(name, 2, 'Organization name');
      if (!minLengthValidation.isValid) {
        newErrors.name = minLengthValidation.error;
      } else {
        const maxLengthValidation = validateMaxLength(name, 100, 'Organization name');
        if (!maxLengthValidation.isValid) {
          newErrors.name = maxLengthValidation.error;
        }
      }
    }

    if (description.trim()) {
      const maxLengthValidation = validateMaxLength(description, 500, 'Description');
      if (!maxLengthValidation.isValid) {
        newErrors.description = maxLengthValidation.error;
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      organizationAPI.create(data, user!.id),
    onSuccess: (org) => {
      queryClient.invalidateQueries({ queryKey: ['organizations', user?.id] });
      queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', user?.id] });
      toast.success('Organization created successfully');
      navigate(`/organizations/${org.id}`);
    },
    onError: (error) => {
      toast.error(error);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      toast.error('Please fix the errors in the form');
      return;
    }

    createMutation.mutate({ name: name.trim(), description: description.trim() || undefined });
  };

  const handleNameChange = (value: string) => {
    setName(value);
    if (errors.name) {
      setErrors({ ...errors, name: undefined });
    }
  };

  const handleDescriptionChange = (value: string) => {
    setDescription(value);
    if (errors.description) {
      setErrors({ ...errors, description: undefined });
    }
  };

  if (!user) {
    navigate('/login');
    return null;
  }

  return (
    <Container maxW="2xl" py={8}>
      <Heading mb={6}>Create Organization</Heading>
      <Box borderWidth={1} borderRadius="lg" p={6}>
        <form onSubmit={handleSubmit}>
          <VStack spacing={4}>
            <FormControl isRequired isInvalid={!!errors.name}>
              <FormLabel>Organization Name</FormLabel>
              <Input
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="Acme Inc."
              />
              {errors.name && <FormErrorMessage>{errors.name}</FormErrorMessage>}
            </FormControl>
            <FormControl isInvalid={!!errors.description}>
              <FormLabel>Description</FormLabel>
              <Textarea
                value={description}
                onChange={(e) => handleDescriptionChange(e.target.value)}
                placeholder="A brief description of your organization..."
                rows={4}
                maxLength={500}
              />
              {errors.description && <FormErrorMessage>{errors.description}</FormErrorMessage>}
            </FormControl>
            <HStack width="100%" justify="flex-end" mt={4}>
              <Button onClick={() => navigate('/organizations')}>Cancel</Button>
              <Button
                type="submit"
                colorScheme="blue"
                isLoading={createMutation.isPending}
              >
                Create Organization
              </Button>
            </HStack>
          </VStack>
        </form>
      </Box>
    </Container>
  );
};

export default CreateOrganization;

