import {
  Box,
  VStack,
  HStack,
  Text,
  Icon,
  Collapse,
  IconButton,
  Badge,
  useColorModeValue,
  Divider,
} from '@chakra-ui/react';
import ReactMarkdown from 'react-markdown';
import { ChevronDownIcon, ChevronUpIcon } from '@chakra-ui/icons';
import { FiActivity, FiArrowRight, FiTool } from 'react-icons/fi';
import { useState } from 'react';

export interface ProgressUpdate {
  agent_name: string;
  message: string;
  type?: 'delegation' | 'tool_result' | 'finding';
  delegate_to?: string;
  tool_name?: string;
  timestamp?: string;
}

interface ProgressTimelineProps {
  updates: ProgressUpdate[];
  isStreaming?: boolean;
}

const ProgressTimeline: React.FC<ProgressTimelineProps> = ({
  updates,
  isStreaming = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const delegationColor = useColorModeValue('blue.500', 'blue.300');
  const toolColor = useColorModeValue('green.500', 'green.300');
  const findingColor = useColorModeValue('purple.500', 'purple.300');

  if (updates.length === 0) return null;

  const getIcon = (type?: string) => {
    switch (type) {
      case 'delegation':
        return FiArrowRight;
      case 'tool_result':
        return FiTool;
      default:
        return FiActivity;
    }
  };

  const getColor = (type?: string) => {
    switch (type) {
      case 'delegation':
        return delegationColor;
      case 'tool_result':
        return toolColor;
      default:
        return findingColor;
    }
  };

  return (
    <Box
      borderWidth={1}
      borderColor={borderColor}
      borderRadius="md"
      bg={bgColor}
      p={3}
      mb={3}
    >
      <HStack justify="space-between" mb={2}>
        <HStack spacing={2}>
          <Icon as={FiActivity} color="blue.500" />
          <Text fontWeight="semibold" fontSize="sm">
            Reasoning Progress
          </Text>
          {isStreaming && (
            <Badge colorScheme="blue" variant="subtle" fontSize="xs">
              Live
            </Badge>
          )}
        </HStack>
        <IconButton
          aria-label={isExpanded ? 'Collapse' : 'Expand'}
          icon={isExpanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
          size="xs"
          variant="ghost"
          onClick={() => setIsExpanded(!isExpanded)}
        />
      </HStack>

      <Collapse in={isExpanded} animateOpacity>
        <VStack spacing={2} align="stretch">
          {updates.map((update, index) => (
            <Box key={index}>
              <HStack spacing={3} align="start">
                <Icon
                  as={getIcon(update.type)}
                  color={getColor(update.type)}
                  mt={0.5}
                  flexShrink={0}
                />
                <VStack spacing={0.5} align="start" flex="1">
                  <HStack spacing={2} flexWrap="wrap">
                    <Text fontSize="xs" fontWeight="semibold" color="gray.400">
                      {update.agent_name}
                    </Text>
                    {update.type === 'delegation' && update.delegate_to && (
                      <>
                        <Icon as={FiArrowRight} boxSize={3} color="gray.400" />
                        <Text fontSize="xs" fontWeight="semibold" color={delegationColor}>
                          {update.delegate_to}
                        </Text>
                      </>
                    )}
                    {update.type === 'tool_result' && update.tool_name && (
                      <Badge colorScheme="green" variant="subtle" fontSize="xs">
                        {update.tool_name}
                      </Badge>
                    )}
                  </HStack>
                  <Box fontSize="sm" color="gray.300" sx={{
                    '& p': { margin: 0 },
                    '& strong': { fontWeight: 'semibold' },
                  }}>
                    <ReactMarkdown>{update.message}</ReactMarkdown>
                  </Box>
                </VStack>
              </HStack>
              {index < updates.length - 1 && <Divider mt={2} />}
            </Box>
          ))}
        </VStack>
      </Collapse>
    </Box>
  );
};

export default ProgressTimeline;
