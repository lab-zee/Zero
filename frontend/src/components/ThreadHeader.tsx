import {
  Box,
  HStack,
  VStack,
  Heading,
  Text,
  Badge,
  IconButton,
  Tooltip,
  useColorModeValue,
} from '@chakra-ui/react';
import { CopyIcon, DownloadIcon, SettingsIcon } from '@chakra-ui/icons';
import { Thread } from '../services/api';

interface ThreadHeaderProps {
  thread: Thread;
  messageCount: number;
  onShareLink: () => void;
  onExport: () => void;
  onPreferences: () => void;
}

const ThreadHeader = ({
  thread,
  messageCount,
  onShareLink,
  onExport,
  onPreferences,
}: ThreadHeaderProps) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Box
      px={6}
      py={4}
      bg={bgColor}
      borderBottomWidth={1}
      borderColor={borderColor}
      position="sticky"
      top={0}
      zIndex={10}
    >
      <HStack justify="space-between" align="center">
        <VStack align="start" spacing={1} flex="1">
          <HStack spacing={3}>
            <Heading size="md" fontWeight="semibold">
              {thread.title || 'Untitled Thread'}
            </Heading>
            {thread.thread_metadata?.budget_focus !== undefined && (
              <Badge
                colorScheme={
                  thread.thread_metadata.budget_focus < 0.3
                    ? 'blue'
                    : thread.thread_metadata.budget_focus < 0.7
                    ? 'gray'
                    : 'green'
                }
                fontSize="xs"
              >
                {thread.thread_metadata.budget_focus < 0.3
                  ? 'Budget-Conscious'
                  : thread.thread_metadata.budget_focus < 0.7
                  ? 'Balanced'
                  : 'Outcome-Conscious'}
              </Badge>
            )}
            {thread.selected_agent_ids && thread.selected_agent_ids.length > 0 && (
              <Tooltip label="Custom agent selection active" placement="top">
                <Badge colorScheme="purple" fontSize="xs" variant="subtle">
                  {thread.selected_agent_ids.length} agent{thread.selected_agent_ids.length !== 1 ? 's' : ''}
                </Badge>
              </Tooltip>
            )}
          </HStack>
          <HStack spacing={4} fontSize="xs" color="gray.400">
            <Text>
              {messageCount > 0 && `${messageCount} message${messageCount !== 1 ? 's' : ''}`}
            </Text>
            {thread.created_at && (
              <Text>
                Created {new Date(thread.created_at).toLocaleDateString()}
              </Text>
            )}
          </HStack>
        </VStack>
        <HStack spacing={2}>
          <Tooltip label="Share Link" placement="bottom">
            <IconButton
              aria-label="Share Link"
              icon={<CopyIcon />}
              size="sm"
              variant="ghost"
              onClick={onShareLink}
            />
          </Tooltip>
          <Tooltip label="Export Conversation" placement="bottom">
            <IconButton
              aria-label="Export Conversation"
              icon={<DownloadIcon />}
              size="sm"
              variant="ghost"
              onClick={onExport}
            />
          </Tooltip>
          <Tooltip label="Thread Preferences" placement="bottom">
            <IconButton
              aria-label="Thread preferences"
              icon={<SettingsIcon />}
              size="sm"
              variant="ghost"
              onClick={onPreferences}
            />
          </Tooltip>
        </HStack>
      </HStack>
    </Box>
  );
};

export default ThreadHeader;





