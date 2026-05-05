import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  VStack,
  Text,
  Textarea,
  FormControl,
  FormLabel,
  FormErrorMessage,
  HStack,
  Icon,
} from '@chakra-ui/react';
import { FiHelpCircle } from 'react-icons/fi';
import { useState } from 'react';

interface ClarificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  questions: string[];
  onSubmit: (answers: string) => void;
  isSubmitting?: boolean;
}

const ClarificationModal: React.FC<ClarificationModalProps> = ({
  isOpen,
  onClose,
  questions,
  onSubmit,
  isSubmitting = false,
}) => {
  const [answers, setAnswers] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = () => {
    if (!answers.trim()) {
      setError('Please provide answers to the clarification questions');
      return;
    }
    setError('');
    onSubmit(answers);
  };

  const handleClose = () => {
    setAnswers('');
    setError('');
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          <HStack spacing={2}>
            <Icon as={FiHelpCircle} color="blue.500" />
            <Text>Additional Information Needed</Text>
          </HStack>
        </ModalHeader>
        <ModalBody>
          <VStack spacing={4} align="stretch">
            <Text color="gray.400">
              To provide you with the most accurate strategic guidance, I need some additional information:
            </Text>
            <VStack spacing={2} align="stretch" pl={4}>
              {questions.map((question, index) => (
                <HStack key={index} align="start" spacing={2}>
                  <Text fontWeight="medium" color="blue.600" minW="20px">
                    {index + 1}.
                  </Text>
                  <Text>{question}</Text>
                </HStack>
              ))}
            </VStack>
            <FormControl isRequired isInvalid={!!error}>
              <FormLabel>Your Answers</FormLabel>
              <Textarea
                value={answers}
                onChange={(e) => {
                  setAnswers(e.target.value);
                  if (error) setError('');
                }}
                placeholder="Please provide answers to the questions above. You can answer them in order (1, 2, 3) or in a free-form response."
                rows={6}
                resize="vertical"
              />
              {error && <FormErrorMessage>{error}</FormErrorMessage>}
            </FormControl>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <HStack spacing={3}>
            <Button variant="ghost" onClick={handleClose} isDisabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleSubmit}
              isLoading={isSubmitting}
              loadingText="Submitting..."
            >
              Submit Answers
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ClarificationModal;
