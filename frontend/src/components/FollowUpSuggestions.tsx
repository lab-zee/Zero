import React from 'react';
import {
  Box,
  Button,
  VStack,
  Text,
  Tooltip,
  useColorModeValue,
  Icon,
} from '@chakra-ui/react';
import { ArrowForwardIcon, LinkIcon, ChatIcon } from '@chakra-ui/icons';

export interface FollowUpQuestion {
  question: string;
  rationale: string;
  type?: 'related' | 'deep_dive';
}

interface FollowUpSuggestionsProps {
  questions: FollowUpQuestion[];
  onQuestionClick: (question: string, type?: string, parentQueryId?: number) => void;
  onActivateFollowUpMode?: (parentQueryId: number) => void;
  parentQueryId?: number;
}

const FollowUpSuggestions: React.FC<FollowUpSuggestionsProps> = ({
  questions,
  onQuestionClick,
  onActivateFollowUpMode,
  parentQueryId,
}) => {
  const purpleBg = useColorModeValue('purple.50', 'purple.900');
  const purpleBorder = useColorModeValue('purple.200', 'purple.700');
  const purpleHover = useColorModeValue('purple.100', 'purple.800');
  const purpleLabel = useColorModeValue('purple.700', 'purple.300');

  const tealBg = useColorModeValue('teal.50', 'teal.900');
  const tealBorder = useColorModeValue('teal.200', 'teal.700');
  const tealHover = useColorModeValue('teal.100', 'teal.800');
  const tealLabel = useColorModeValue('teal.700', 'teal.300');

  if (!questions || questions.length === 0) {
    return null;
  }

  const relatedQuestions = questions.filter(q => !q.type || q.type === 'related');
  const deepDiveQuestions = questions.filter(q => q.type === 'deep_dive');

  return (
    <>
      {relatedQuestions.length > 0 && (
        <Box
          mt={4}
          p={4}
          bg={purpleBg}
          borderRadius="md"
          borderWidth={1}
          borderColor={purpleBorder}
        >
          <Text fontSize="sm" fontWeight="bold" color={purpleLabel} mb={3}>
            Related Questions
          </Text>
          <VStack align="stretch" spacing={2}>
            {relatedQuestions.map((q, idx) => (
              <Tooltip
                key={`related-${idx}`}
                label={q.rationale}
                hasArrow
                placement="top"
                bg="gray.700"
                color="white"
                fontSize="sm"
                p={2}
                borderRadius="md"
              >
                <Button
                  size="sm"
                  variant="outline"
                  colorScheme="purple"
                  justifyContent="flex-start"
                  textAlign="left"
                  whiteSpace="normal"
                  height="auto"
                  py={2}
                  px={3}
                  onClick={() => onQuestionClick(q.question, 'related')}
                  rightIcon={<Icon as={ArrowForwardIcon} />}
                  _hover={{
                    bg: purpleHover,
                  }}
                >
                  <Text fontSize="sm" flex={1}>
                    {q.question}
                  </Text>
                </Button>
              </Tooltip>
            ))}
          </VStack>
        </Box>
      )}

      {(deepDiveQuestions.length > 0 || (parentQueryId && onActivateFollowUpMode)) && (
        <Box
          mt={4}
          p={4}
          bg={tealBg}
          borderRadius="md"
          borderWidth={1}
          borderColor={tealBorder}
        >
          <Text fontSize="sm" fontWeight="bold" color={tealLabel} mb={3}>
            Deep Dive Follow-Ups
          </Text>
          <Text fontSize="xs" color={tealLabel} mb={2} opacity={0.8}>
            Continues from previous analysis
          </Text>
          <VStack align="stretch" spacing={2}>
            {deepDiveQuestions.map((q, idx) => (
              <Tooltip
                key={`deepdive-${idx}`}
                label={q.rationale}
                hasArrow
                placement="top"
                bg="gray.700"
                color="white"
                fontSize="sm"
                p={2}
                borderRadius="md"
              >
                <Button
                  size="sm"
                  variant="outline"
                  colorScheme="teal"
                  justifyContent="flex-start"
                  textAlign="left"
                  whiteSpace="normal"
                  height="auto"
                  py={2}
                  px={3}
                  onClick={() => onQuestionClick(q.question, 'deep_dive', parentQueryId)}
                  rightIcon={<Icon as={LinkIcon} />}
                  _hover={{
                    bg: tealHover,
                  }}
                >
                  <Text fontSize="sm" flex={1}>
                    {q.question}
                  </Text>
                </Button>
              </Tooltip>
            ))}
            {parentQueryId && onActivateFollowUpMode && (
              <Button
                size="sm"
                variant="solid"
                colorScheme="teal"
                justifyContent="center"
                height="auto"
                py={2}
                px={3}
                mt={deepDiveQuestions.length > 0 ? 1 : 0}
                leftIcon={<Icon as={ChatIcon} />}
                onClick={() => onActivateFollowUpMode(parentQueryId)}
              >
                Ask your own follow-up
              </Button>
            )}
          </VStack>
        </Box>
      )}
    </>
  );
};

export default FollowUpSuggestions;
