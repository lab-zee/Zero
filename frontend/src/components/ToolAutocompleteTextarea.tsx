import { useRef, useState, useEffect } from 'react';
import {
  Box,
  Textarea,
  Text,
  HStack,
  VStack,
  useColorModeValue,
  type TextareaProps,
} from '@chakra-ui/react';
import { useTools } from '../hooks/useTools';
import { useToolAutocomplete } from '../hooks/useToolAutocomplete';

interface ToolAutocompleteTextareaProps extends Omit<TextareaProps, 'value' | 'onChange'> {
  value: string;
  onChange: (value: string) => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
}

/**
 * Textarea component with slash command autocomplete for tools.
 * When user types "/", shows a menu of available tools with descriptions.
 * Supports keyboard navigation (arrows, enter, escape, tab) and mouse selection.
 */
export const ToolAutocompleteTextarea = ({
  value,
  onChange,
  onKeyDown,
  ...textareaProps
}: ToolAutocompleteTextareaProps) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [cursorPosition, setCursorPosition] = useState(0);

  // Fetch tools from backend
  const { data: tools = [] } = useTools();

  // Update cursor position on change
  useEffect(() => {
    if (textareaRef.current) {
      setCursorPosition(textareaRef.current.selectionStart);
    }
  }, [value]);

  // Autocomplete logic
  const {
    isOpen,
    filteredTools,
    selectedIndex,
    handleKeyDown: handleAutocompleteKeyDown,
    handleToolSelect,
    selectedItemRef,
  } = useToolAutocomplete({
    value,
    cursorPosition,
    tools,
    onValueChange: onChange,
    textareaRef,
  });

  // Combined keyboard handler
  const handleKeyDownCombined = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Update cursor position
    setTimeout(() => {
      if (textareaRef.current) {
        setCursorPosition(textareaRef.current.selectionStart);
      }
    }, 0);

    // Try autocomplete handler first
    const handled = handleAutocompleteKeyDown(e);

    // If not handled by autocomplete, pass to original handler
    if (!handled && onKeyDown) {
      onKeyDown(e);
    }
  };

  // Handle clicks to update cursor position
  const handleClick = () => {
    if (textareaRef.current) {
      setCursorPosition(textareaRef.current.selectionStart);
    }
  };

  // Color mode values
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const hoverBg = useColorModeValue('gray.100', 'gray.700');
  const selectedBg = useColorModeValue('gray.100', 'gray.700');
  const brandColor = useColorModeValue('brand.500', 'brand.400');
  const descriptionColor = useColorModeValue('gray.600', 'gray.400');

  return (
    <Box position="relative" width="full">
      {/* Autocomplete Menu */}
      {isOpen && (
        <Box
          ref={menuRef}
          position="absolute"
          bottom="full"
          left={0}
          right={0}
          maxH="300px"
          overflowY="auto"
          bg={bgColor}
          borderWidth={1}
          borderColor={borderColor}
          borderRadius="md"
          boxShadow="lg"
          zIndex={1000}
          mb={2}
          role="listbox"
          aria-label="Available tools"
        >
          <VStack spacing={0} align="stretch">
            {filteredTools.map((tool, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <Box
                  key={tool.id}
                  ref={isSelected ? selectedItemRef : null}
                  id={`tool-${idx}`}
                  role="option"
                  aria-selected={isSelected}
                  px={4}
                  py={3}
                  cursor="pointer"
                  bg={isSelected ? selectedBg : 'transparent'}
                  _hover={{ bg: hoverBg }}
                  onClick={() => handleToolSelect(tool.name)}
                  transition="background 0.2s"
                >
                  <HStack spacing={3} align="start">
                    <Text
                      fontSize="sm"
                      fontWeight="bold"
                      color={brandColor}
                      fontFamily="mono"
                      flexShrink={0}
                    >
                      /{tool.name}
                    </Text>
                    <Text
                      fontSize="xs"
                      color={descriptionColor}
                      flex={1}
                      noOfLines={2}
                    >
                      {tool.description}
                    </Text>
                  </HStack>
                </Box>
              );
            })}
          </VStack>
        </Box>
      )}

      {/* Textarea */}
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDownCombined}
        onClick={handleClick}
        onSelect={handleClick}
        {...textareaProps}
      />
    </Box>
  );
};
