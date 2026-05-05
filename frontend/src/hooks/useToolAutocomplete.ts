import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import type { ToolInfo } from './useTools';

interface SlashCommandInfo {
  isSlashCommand: boolean;
  query: string;
  startPosition: number;
}

interface UseToolAutocompleteOptions {
  value: string;
  cursorPosition: number;
  tools: ToolInfo[];
  onValueChange: (value: string) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement>;
}

/**
 * Detects if there's a valid slash command at the cursor position.
 * A slash command is valid if:
 * 1. "/" is preceded by whitespace or is at the start of the text
 * 2. No whitespace exists between "/" and the cursor
 */
const detectSlashCommand = (text: string, cursorPosition: number): SlashCommandInfo => {
  const textBeforeCursor = text.slice(0, cursorPosition);
  const lastSlashIndex = textBeforeCursor.lastIndexOf('/');

  if (lastSlashIndex === -1) {
    return { isSlashCommand: false, query: '', startPosition: -1 };
  }

  const afterSlash = textBeforeCursor.slice(lastSlashIndex + 1);
  const charBeforeSlash = lastSlashIndex > 0 ? textBeforeCursor[lastSlashIndex - 1] : ' ';
  const isValidPosition = /\s/.test(charBeforeSlash);
  const hasNoSpaceAfter = !/\s/.test(afterSlash);

  return {
    isSlashCommand: isValidPosition && hasNoSpaceAfter,
    query: afterSlash,
    startPosition: lastSlashIndex,
  };
};

/**
 * Filters tools based on the query string.
 * Prioritizes matches at the start of the tool name.
 */
const filterTools = (tools: ToolInfo[], query: string): ToolInfo[] => {
  if (!query.trim()) {
    return tools; // Show all tools when just "/" typed
  }

  const lowerQuery = query.toLowerCase();

  return tools
    .filter((tool) => tool.name.toLowerCase().includes(lowerQuery))
    .sort((a, b) => {
      // Prioritize matches at start of tool name
      const aStarts = a.name.toLowerCase().startsWith(lowerQuery);
      const bStarts = b.name.toLowerCase().startsWith(lowerQuery);

      if (aStarts && !bStarts) return -1;
      if (!aStarts && bStarts) return 1;

      return a.name.localeCompare(b.name);
    });
};

/**
 * Hook for managing tool autocomplete functionality.
 * Handles slash detection, filtering, keyboard navigation, and tool insertion.
 */
export const useToolAutocomplete = ({
  value,
  cursorPosition,
  tools,
  onValueChange,
  textareaRef,
}: UseToolAutocompleteOptions) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const selectedItemRef = useRef<HTMLDivElement>(null);

  // Detect slash command at current cursor position
  const slashInfo = useMemo(
    () => detectSlashCommand(value, cursorPosition),
    [value, cursorPosition]
  );

  // Filter tools based on query
  const filteredTools = useMemo(
    () => (slashInfo.isSlashCommand ? filterTools(tools, slashInfo.query) : []),
    [tools, slashInfo]
  );

  const isOpen = slashInfo.isSlashCommand && filteredTools.length > 0;

  // Reset selected index when filtered tools change
  useEffect(() => {
    setSelectedIndex(0);
  }, [filteredTools.length]);

  // Auto-scroll selected item into view
  useEffect(() => {
    if (selectedItemRef.current) {
      selectedItemRef.current.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
      });
    }
  }, [selectedIndex]);

  /**
   * Handles tool selection - inserts the tool name into the text.
   */
  const handleToolSelect = useCallback(
    (toolName: string) => {
      if (!textareaRef.current) return;

      const before = value.slice(0, slashInfo.startPosition);
      const after = value.slice(cursorPosition);
      const newValue = `${before}/${toolName} ${after}`;

      onValueChange(newValue);

      // Set cursor after inserted tool name
      setTimeout(() => {
        const newCursorPos = slashInfo.startPosition + toolName.length + 2; // +2 for "/" and space
        textareaRef.current?.setSelectionRange(newCursorPos, newCursorPos);
        textareaRef.current?.focus();
      }, 0);
    },
    [value, cursorPosition, slashInfo.startPosition, onValueChange, textareaRef]
  );

  /**
   * Handles keyboard navigation within the autocomplete menu.
   * Returns true if the event was handled, false otherwise.
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>): boolean => {
      if (!isOpen || filteredTools.length === 0) {
        return false; // Event not handled
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev < filteredTools.length - 1 ? prev + 1 : prev
          );
          return true;

        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev));
          return true;

        case 'Enter':
          if (!e.shiftKey) {
            e.preventDefault();
            handleToolSelect(filteredTools[selectedIndex].name);
            return true;
          }
          // Shift+Enter falls through for new line
          return false;

        case 'Escape':
          e.preventDefault();
          // Close menu by clearing the slash command (or just blur)
          // For now, we'll just let it close naturally
          return true;

        case 'Tab':
          e.preventDefault();
          handleToolSelect(filteredTools[selectedIndex].name);
          return true;

        default:
          return false;
      }
    },
    [isOpen, filteredTools, selectedIndex, handleToolSelect]
  );

  return {
    isOpen,
    filteredTools,
    selectedIndex,
    handleKeyDown,
    handleToolSelect,
    selectedItemRef,
  };
};
