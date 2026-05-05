import { useState, useRef } from 'react';
import {
  Box,
  Button,
  Input,
  VStack,
  HStack,
  Text,
  IconButton,
  Tooltip,
} from '@chakra-ui/react';
import { CloseIcon } from '@chakra-ui/icons';
import { FiPaperclip, FiSend } from 'react-icons/fi';
import { FileInfo } from '../services/api';
import { ToolAutocompleteTextarea } from './ToolAutocompleteTextarea';

interface MessageInputProps {
  message: string;
  onMessageChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isStreaming: boolean;
  selectedFileIds: number[];
  uploadedFiles: FileInfo[];
  onFileSelect: (fileId: number) => void;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  isUploading: boolean;
  selectedOrgId: number | null;
  isFollowUpMode?: boolean;
  onCancelFollowUp?: () => void;
}

const MessageInput = ({
  message,
  onMessageChange,
  onSubmit,
  isStreaming,
  selectedFileIds,
  uploadedFiles,
  onFileSelect,
  onFileUpload,
  isUploading,
  selectedOrgId,
  isFollowUpMode,
  onCancelFollowUp,
}: MessageInputProps) => {
  const [showFileSection, setShowFileSection] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <Box
      px={6}
      py={4}
      bg="surface.800"
      borderTopWidth="1px"
      borderColor="whiteAlpha.100"
      flexShrink={0}
      zIndex={10}
    >
      <form onSubmit={onSubmit}>
        <VStack spacing={3} align="stretch">

          {showFileSection && (
            <Box
              bg="surface.900"
              p={3}
              borderRadius="lg"
              borderWidth="1px"
              borderColor="whiteAlpha.100"
            >
              <HStack justify="space-between" mb={3}>
                <Text fontSize="sm" fontWeight="500" color="gray.200">
                  Attach Files
                </Text>
                <HStack>
                  {selectedFileIds.length > 0 && (
                    <Text fontSize="xs" color="brand.400" fontWeight="500">
                      {selectedFileIds.length} file{selectedFileIds.length > 1 ? 's' : ''} selected
                    </Text>
                  )}
                  <IconButton
                    aria-label="Close file section"
                    icon={<CloseIcon />}
                    size="xs"
                    variant="ghost"
                    onClick={() => setShowFileSection(false)}
                  />
                </HStack>
              </HStack>

              <VStack spacing={3} align="stretch">
                {/* Upload New File */}
                <Box>
                  <Text fontSize="xs" fontWeight="500" color="gray.400" mb={2}>
                    Upload New File:
                  </Text>
                  <HStack>
                    <Input
                      type="file"
                      ref={fileInputRef}
                      onChange={onFileUpload}
                      style={{ display: 'none' }}
                    />
                    <Button
                      leftIcon={<FiPaperclip />}
                      size="sm"
                      variant="outline"
                      onClick={() => fileInputRef.current?.click()}
                      isLoading={isUploading}
                      disabled={!selectedOrgId}
                      flex="1"
                      borderColor="whiteAlpha.200"
                      color="gray.300"
                      _hover={{ borderColor: 'brand.400', color: 'brand.400' }}
                    >
                      {isUploading ? 'Uploading...' : 'Choose File'}
                    </Button>
                  </HStack>
                </Box>

                {/* Select from Existing Files */}
                {uploadedFiles.length > 0 && (
                  <Box>
                    <Text fontSize="xs" fontWeight="500" color="gray.400" mb={2}>
                      Previously Uploaded:
                    </Text>
                    <Box
                      bg="surface.800"
                      p={2}
                      borderRadius="md"
                      borderWidth="1px"
                      borderColor="whiteAlpha.100"
                      maxH="150px"
                      overflowY="auto"
                    >
                      <VStack spacing={1.5} align="stretch">
                        {uploadedFiles.map((file) => {
                          const isSelected = selectedFileIds.includes(file.id);
                          return (
                            <HStack
                              key={file.id}
                              justify="space-between"
                              fontSize="sm"
                              p={2}
                              borderRadius="md"
                              bg={isSelected ? 'whiteAlpha.100' : 'transparent'}
                              borderWidth="1px"
                              borderColor={isSelected ? 'brand.400' : 'whiteAlpha.50'}
                              cursor="pointer"
                              onClick={() => onFileSelect(file.id)}
                              _hover={{
                                bg: 'whiteAlpha.50',
                                borderColor: isSelected ? 'brand.400' : 'whiteAlpha.100',
                              }}
                              transition="all 0.15s"
                            >
                              <HStack spacing={2} flex="1">
                                <Box as={FiPaperclip} color={isSelected ? 'brand.400' : 'gray.500'} />
                                <Text isTruncated maxW="250px" fontWeight={isSelected ? '500' : '400'} color="gray.200" fontSize="xs">
                                  {file.original_filename}
                                </Text>
                                <Text color="gray.400" fontSize="2xs">
                                  {(file.file_size / 1024).toFixed(1)} KB
                                </Text>
                              </HStack>
                              {isSelected && (
                                <Box
                                  bg="brand.500"
                                  color="white"
                                  borderRadius="full"
                                  w={4}
                                  h={4}
                                  display="flex"
                                  alignItems="center"
                                  justifyContent="center"
                                  fontSize="2xs"
                                  fontWeight="bold"
                                >
                                  ✓
                                </Box>
                              )}
                            </HStack>
                          );
                        })}
                      </VStack>
                    </Box>
                  </Box>
                )}

                {/* Selected Files Summary */}
                {selectedFileIds.length > 0 && (
                  <Box
                    bg="whiteAlpha.50"
                    p={2}
                    borderRadius="md"
                    borderWidth="1px"
                    borderColor="brand.400"
                  >
                    <Text fontSize="xs" fontWeight="500" mb={1} color="brand.400">
                      Attached:
                    </Text>
                    <VStack spacing={1} align="stretch">
                      {selectedFileIds.map((fileId) => {
                        const file = uploadedFiles.find((f) => f.id === fileId);
                        if (!file) return null;
                        return (
                          <HStack key={fileId} justify="space-between" fontSize="xs">
                            <HStack spacing={2}>
                              <Box as={FiPaperclip} color="brand.400" boxSize="12px" />
                              <Text isTruncated maxW="250px" fontWeight="400" color="gray.200">
                                {file.original_filename}
                              </Text>
                            </HStack>
                            <IconButton
                              aria-label="Remove file"
                              icon={<CloseIcon />}
                              size="xs"
                              variant="ghost"
                              color="gray.400"
                              _hover={{ color: 'red.400' }}
                              onClick={() => onFileSelect(fileId)}
                            />
                          </HStack>
                        );
                      })}
                    </VStack>
                  </Box>
                )}

                {uploadedFiles.length === 0 && (
                  <Text fontSize="xs" color="gray.400" fontStyle="italic" textAlign="center" py={2}>
                    No files uploaded yet.
                  </Text>
                )}
              </VStack>
            </Box>
          )}

          {/* Follow-up mode indicator */}
          {isFollowUpMode && (
            <HStack
              bg="teal.900"
              px={3}
              py={2}
              borderRadius="md"
              borderWidth="1px"
              borderColor="teal.700"
              justify="space-between"
            >
              <HStack spacing={2}>
                <Box w={2} h={2} borderRadius="full" bg="teal.400" />
                <Text fontSize="xs" color="teal.300" fontWeight="500">
                  Follow-up mode — your question will build on the previous analysis
                </Text>
              </HStack>
              <IconButton
                aria-label="Cancel follow-up mode"
                icon={<CloseIcon />}
                size="xs"
                variant="ghost"
                color="teal.400"
                _hover={{ color: 'teal.200', bg: 'whiteAlpha.100' }}
                onClick={onCancelFollowUp}
              />
            </HStack>
          )}

          {/* Message Input Field */}
          <HStack spacing={2} align="flex-end">
            <ToolAutocompleteTextarea
              value={message}
              onChange={onMessageChange}
              placeholder="Type your message..."
              size="md"
              minH="60px"
              maxH="200px"
              resize="none"
              rows={2}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  onSubmit(e as any);
                }
              }}
            />
            <Tooltip label="Attach files" placement="top">
              <IconButton
                aria-label="Attach files"
                icon={<FiPaperclip />}
                variant="ghost"
                onClick={() => setShowFileSection(!showFileSection)}
                color={selectedFileIds.length > 0 ? 'brand.400' : 'gray.500'}
                _hover={{ color: 'gray.200', bg: 'whiteAlpha.100' }}
              />
            </Tooltip>
            <Tooltip label="Send message" placement="top">
              <IconButton
                type="submit"
                aria-label="Send message"
                icon={<FiSend />}
                bg="brand.500"
                color="white"
                isLoading={isStreaming}
                isDisabled={!message.trim()}
                _hover={{ bg: 'brand.400' }}
                borderRadius="lg"
              />
            </Tooltip>
          </HStack>
        </VStack>
      </form>
    </Box>
  );
};

export default MessageInput;
