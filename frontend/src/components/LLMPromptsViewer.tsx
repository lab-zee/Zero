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
  Code,
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronUpIcon, ChevronRightIcon } from '@chakra-ui/icons';
import { FiCpu, FiMessageSquare } from 'react-icons/fi';
import { useState } from 'react';

export interface LLMPromptRecord {
  agent_name: string;
  agent_id: string;
  model: string;
  iteration: number;
  messages: Array<{
    role: string;
    content?: string | null;
    tool_calls?: any[];
    tool_call_id?: string;
  }>;
  tools?: any[] | null;
  response_content?: string | null;
  response_tool_calls?: any[] | null;
  timestamp: string;
}

interface LLMPromptsViewerProps {
  prompts: LLMPromptRecord[];
}

const roleColors: Record<string, string> = {
  system: 'gray.500',
  user: 'blue.300',
  assistant: 'green.300',
  tool: 'orange.300',
};

const roleBgColors: Record<string, string> = {
  system: 'whiteAlpha.50',
  user: 'blue.900',
  assistant: 'green.900',
  tool: 'orange.900',
};

const LLMPromptsViewer: React.FC<LLMPromptsViewerProps> = ({ prompts }) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [expandedCalls, setExpandedCalls] = useState<Set<number>>(new Set());
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  if (!prompts || prompts.length === 0) {
    return (
      <Box p={4} textAlign="center" color="gray.400" fontSize="sm">
        No LLM prompt data available for this query
      </Box>
    );
  }

  const toggleCall = (index: number) => {
    setExpandedCalls((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const toggleMessage = (key: string) => {
    setExpandedMessages((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const truncate = (text: string, max: number) =>
    text.length > max ? text.slice(0, max) + '...' : text;

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
          <Icon as={FiCpu} color="purple.400" />
          <Text fontWeight="semibold" fontSize="sm">
            LLM Calls ({prompts.length})
          </Text>
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
        <VStack spacing={1} align="stretch">
          {prompts.map((prompt, callIndex) => {
            const isCallExpanded = expandedCalls.has(callIndex);
            const messageCount = prompt.messages?.length || 0;
            const hasToolCalls = !!prompt.response_tool_calls?.length;

            return (
              <Box key={callIndex}>
                {/* Call Header - clickable to expand */}
                <HStack
                  spacing={2}
                  p={2}
                  borderRadius="sm"
                  cursor="pointer"
                  _hover={{ bg: 'whiteAlpha.100' }}
                  onClick={() => toggleCall(callIndex)}
                >
                  <Icon
                    as={isCallExpanded ? ChevronDownIcon : ChevronRightIcon}
                    boxSize={3}
                    color="gray.400"
                    flexShrink={0}
                  />
                  <Icon as={FiMessageSquare} color="purple.400" boxSize={3} flexShrink={0} />
                  <Text fontSize="xs" fontWeight="semibold" color="gray.300" noOfLines={1}>
                    {prompt.agent_name}
                  </Text>
                  {prompt.iteration > 0 && (
                    <Badge colorScheme="purple" variant="subtle" fontSize="2xs">
                      iter {prompt.iteration}
                    </Badge>
                  )}
                  <Badge colorScheme="gray" variant="subtle" fontSize="2xs">
                    {prompt.model}
                  </Badge>
                  <Text fontSize="2xs" color="gray.500">
                    {messageCount} msgs
                  </Text>
                  {hasToolCalls && (
                    <Badge colorScheme="orange" variant="subtle" fontSize="2xs">
                      tool calls
                    </Badge>
                  )}
                </HStack>

                {/* Expanded Call Details */}
                <Collapse in={isCallExpanded} animateOpacity>
                  <Box pl={7} pr={2} pb={2}>
                    <VStack spacing={1.5} align="stretch">
                      {prompt.messages?.map((msg, msgIndex) => {
                        const msgKey = `${callIndex}-${msgIndex}`;
                        const isMsgExpanded = expandedMessages.has(msgKey);
                        const content = msg.content || '';
                        const isLong = content.length > 200;
                        const roleColor = roleColors[msg.role] || 'gray.400';
                        const roleBg = roleBgColors[msg.role] || 'whiteAlpha.50';

                        return (
                          <Box
                            key={msgIndex}
                            borderRadius="sm"
                            bg={roleBg}
                            p={2}
                            borderLeftWidth={2}
                            borderLeftColor={roleColor}
                          >
                            <HStack spacing={2} mb={content ? 1 : 0}>
                              <Badge
                                fontSize="2xs"
                                colorScheme={
                                  msg.role === 'system'
                                    ? 'gray'
                                    : msg.role === 'user'
                                    ? 'blue'
                                    : msg.role === 'assistant'
                                    ? 'green'
                                    : 'orange'
                                }
                                variant="solid"
                              >
                                {msg.role}
                              </Badge>
                              {msg.tool_call_id && (
                                <Text fontSize="2xs" color="gray.500" fontFamily="mono">
                                  {msg.tool_call_id}
                                </Text>
                              )}
                              {isLong && (
                                <Text
                                  fontSize="2xs"
                                  color="purple.300"
                                  cursor="pointer"
                                  _hover={{ textDecoration: 'underline' }}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    toggleMessage(msgKey);
                                  }}
                                >
                                  {isMsgExpanded ? 'collapse' : 'expand'}
                                </Text>
                              )}
                            </HStack>
                            {content && (
                              <Text
                                fontSize="xs"
                                color="gray.300"
                                whiteSpace="pre-wrap"
                                wordBreak="break-word"
                                fontFamily="mono"
                              >
                                {isLong && !isMsgExpanded
                                  ? truncate(content, 200)
                                  : content}
                              </Text>
                            )}
                            {msg.tool_calls && msg.tool_calls.length > 0 && (
                              <Box mt={1}>
                                {msg.tool_calls.map((tc: any, tcIdx: number) => (
                                  <HStack key={tcIdx} spacing={1}>
                                    <Badge colorScheme="orange" variant="outline" fontSize="2xs">
                                      {tc.function?.name || 'unknown'}
                                    </Badge>
                                    <Code fontSize="2xs" color="gray.400" bg="transparent">
                                      {truncate(tc.function?.arguments || '', 100)}
                                    </Code>
                                  </HStack>
                                ))}
                              </Box>
                            )}
                          </Box>
                        );
                      })}

                      {/* Response summary */}
                      {prompt.response_content && (
                        <Box bg="green.900" p={2} borderRadius="sm" borderLeftWidth={2} borderLeftColor="green.300">
                          <Badge fontSize="2xs" colorScheme="green" variant="solid" mb={1}>
                            response
                          </Badge>
                          <Text fontSize="xs" color="gray.300" whiteSpace="pre-wrap" fontFamily="mono">
                            {truncate(prompt.response_content, 300)}
                          </Text>
                        </Box>
                      )}
                      {prompt.response_tool_calls && prompt.response_tool_calls.length > 0 && (
                        <HStack spacing={1} flexWrap="wrap">
                          <Text fontSize="2xs" color="gray.500">Tool calls:</Text>
                          {prompt.response_tool_calls.map((tc: any, i: number) => (
                            <Badge key={i} colorScheme="orange" variant="outline" fontSize="2xs">
                              {tc.function?.name || 'unknown'}
                            </Badge>
                          ))}
                        </HStack>
                      )}
                    </VStack>
                  </Box>
                </Collapse>

                {callIndex < prompts.length - 1 && <Divider />}
              </Box>
            );
          })}
        </VStack>
      </Collapse>
    </Box>
  );
};

export default LLMPromptsViewer;
