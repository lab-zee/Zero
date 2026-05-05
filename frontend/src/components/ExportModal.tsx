import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Button,
  VStack,
  FormControl,
  FormLabel,
  Switch,
  Divider,
  Text,
} from '@chakra-ui/react';
import { DownloadIcon } from '@chakra-ui/icons';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  includeTraces: boolean;
  onIncludeTracesChange: (value: boolean) => void;
  onExport: (format: 'markdown' | 'json' | 'text') => void;
  hasMessages: boolean;
}

const ExportModal = ({
  isOpen,
  onClose,
  includeTraces,
  onIncludeTracesChange,
  onExport,
  hasMessages,
}: ExportModalProps) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Export Conversation</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4} align="stretch">
            <FormControl display="flex" alignItems="center" justifyContent="space-between">
              <FormLabel htmlFor="include-traces" mb={0}>
                Include Agent Execution Traces
              </FormLabel>
              <Switch
                id="include-traces"
                isChecked={includeTraces}
                onChange={(e) => onIncludeTracesChange(e.target.checked)}
              />
            </FormControl>
            <Text fontSize="sm" color="gray.400">
              When enabled, exports will include detailed agent execution traces showing how the response was generated.
            </Text>
            <Divider />
            <VStack spacing={3} align="stretch">
              <Button
                leftIcon={<DownloadIcon />}
                colorScheme="blue"
                onClick={() => onExport('markdown')}
                isDisabled={!hasMessages}
              >
                Export as Markdown (.md)
              </Button>
              <Button
                leftIcon={<DownloadIcon />}
                colorScheme="green"
                onClick={() => onExport('json')}
                isDisabled={!hasMessages}
              >
                Export as JSON (.json)
              </Button>
              <Button
                leftIcon={<DownloadIcon />}
                colorScheme="gray"
                onClick={() => onExport('text')}
                isDisabled={!hasMessages}
              >
                Export as Plain Text (.txt)
              </Button>
            </VStack>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ExportModal;





