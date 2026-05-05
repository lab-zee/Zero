import React from 'react';
import {
  Box,
  Button,
  Heading,
  Text,
  VStack,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import { IconType } from 'react-icons';
import {
  FiMessageSquare,
  FiFolder,
  FiInbox,
  FiSearch,
} from 'react-icons/fi';

interface EmptyStateProps {
  icon?: IconType;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  variant?: 'default' | 'no-organizations' | 'no-threads' | 'no-messages' | 'no-results';
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  variant = 'default',
}) => {
  const textColor = useColorModeValue('gray.600', 'gray.400');
  const iconColor = useColorModeValue('gray.400', 'gray.500');

  const defaultIcons: Record<string, IconType> = {
    'no-organizations': FiFolder,
    'no-threads': FiMessageSquare,
    'no-messages': FiInbox,
    'no-results': FiSearch,
  };

  const IconComponent = icon || defaultIcons[variant] || FiInbox;

  return (
    <Box
      display="flex"
      alignItems="center"
      justifyContent="center"
      minH="400px"
      p={8}
    >
      <VStack spacing={6} maxW="md" textAlign="center">
        <Icon
          as={IconComponent}
          w={16}
          h={16}
          color={iconColor}
        />

        <VStack spacing={2}>
          <Heading size="md" fontWeight="semibold">
            {title}
          </Heading>
          <Text color={textColor} fontSize="md">
            {description}
          </Text>
        </VStack>

        {actionLabel && onAction && (
          <Button
            colorScheme="blue"
            size="lg"
            onClick={onAction}
            mt={4}
          >
            {actionLabel}
          </Button>
        )}
      </VStack>
    </Box>
  );
};

export default EmptyState;

export const NoOrganizationsState: React.FC<{ onCreate: () => void }> = ({ onCreate }) => (
  <EmptyState
    variant="no-organizations"
    title="No organizations yet"
    description="Create your first organization to get started with strategic decision-making tools"
    actionLabel="Create Organization"
    onAction={onCreate}
  />
);

export const NoThreadsState: React.FC<{ onStart: () => void }> = ({ onStart }) => (
  <EmptyState
    variant="no-threads"
    title="No conversations yet"
    description="Start a new conversation to begin exploring strategic questions"
    actionLabel="Start Conversation"
    onAction={onStart}
  />
);

export const NoMessagesState: React.FC = () => (
  <EmptyState
    variant="no-messages"
    title="Ready to help"
    description="Ask a strategic question to begin. Our AI agents will collaborate to provide comprehensive insights."
  />
);

export const NoResultsState: React.FC<{ searchTerm?: string }> = ({ searchTerm }) => (
  <EmptyState
    variant="no-results"
    title="No results found"
    description={
      searchTerm
        ? `We couldn't find anything matching "${searchTerm}". Try adjusting your search.`
        : "We couldn't find any results. Try adjusting your filters."
    }
  />
);
