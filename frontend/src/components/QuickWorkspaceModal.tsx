import { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  VStack,
} from '@chakra-ui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { organizationAPI } from '../services/api';
import { useCustomToast } from '../hooks/useToast';

interface QuickWorkspaceModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: number;
  onCreated?: (orgId: number) => void;
}

const QuickWorkspaceModal = ({
  isOpen,
  onClose,
  userId,
  onCreated,
}: QuickWorkspaceModalProps) => {
  const queryClient = useQueryClient();
  const toast = useCustomToast();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const reset = () => {
    setName('');
    setDescription('');
  };

  const createMutation = useMutation({
    mutationFn: () =>
      organizationAPI.create(
        { name: name.trim(), description: description.trim() || undefined },
        userId
      ),
    onSuccess: (org) => {
      queryClient.invalidateQueries({ queryKey: ['organizations', userId] });
      queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', userId] });
      toast.success('Workspace created');
      reset();
      onClose();
      onCreated?.(org.id);
    },
    onError: (error) => {
      toast.error(error);
    },
  });

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error('Workspace name is required');
      return;
    }
    createMutation.mutate();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="md">
      <ModalOverlay />
      <ModalContent>
        <form onSubmit={handleSubmit}>
          <ModalHeader>New workspace</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <FormControl isRequired>
                <FormLabel>Name</FormLabel>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Dinner planning, Legal review"
                  autoFocus
                />
              </FormControl>
              <FormControl>
                <FormLabel>Description</FormLabel>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional — what this workspace is for"
                  rows={2}
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={handleClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              colorScheme="orange"
              isLoading={createMutation.isPending}
            >
              Create
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
};

export default QuickWorkspaceModal;
