import {
  VStack,
  HStack,
  Text,
  Link,
  Box,
  Badge,
  useColorModeValue,
} from '@chakra-ui/react';
import { ExternalLinkIcon } from '@chakra-ui/icons';

export interface Citation {
  number?: number;
  type: string;
  url?: string;
  title?: string;
  author?: string;
  date?: string;
  description?: string;
}

interface ReferenceListProps {
  citations: Citation[];
  highlightedNumber?: number | null;
  onHover?: (number: number | null) => void;
}

const ReferenceList: React.FC<ReferenceListProps> = ({
  citations,
  highlightedNumber = null,
  onHover,
}) => {
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const highlightBg = useColorModeValue('yellow.50', 'yellow.900');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');

  // Sort citations by number if available
  const sortedCitations = [...citations].sort((a, b) => {
    if (a.number && b.number) return a.number - b.number;
    return 0;
  });

  return (
    <VStack spacing={3} align="stretch">
      {sortedCitations.map((citation, index) => {
        const citationNumber = citation.number || index + 1;
        const isHighlighted = highlightedNumber === citationNumber;

        return (
          <Box
            key={citationNumber}
            p={3}
            borderWidth={1}
            borderColor={borderColor}
            borderRadius="md"
            bg={isHighlighted ? highlightBg : 'transparent'}
            _hover={{ bg: hoverBg }}
            transition="all 0.2s"
            onMouseEnter={() => onHover?.(citationNumber)}
            onMouseLeave={() => onHover?.(null)}
            id={`citation-${citationNumber}`}
          >
            <HStack spacing={2} align="start">
              <Text fontWeight="bold" color="blue.500" minW="30px">
                [{citationNumber}]
              </Text>
              <VStack spacing={1} align="start" flex="1">
                <HStack spacing={2} flexWrap="wrap">
                  {citation.author && (
                    <Text fontWeight="semibold">{citation.author}</Text>
                  )}
                  {citation.date && (
                    <Text color="gray.400">({citation.date})</Text>
                  )}
                  {citation.type && citation.type !== 'web' && (
                    <Badge colorScheme="purple" fontSize="xs">
                      {citation.type}
                    </Badge>
                  )}
                </HStack>
                {citation.title && (
                  <Text fontSize="sm" fontStyle="italic">
                    "{citation.title}"
                  </Text>
                )}
                {citation.url && (
                  <Link
                    href={citation.url}
                    isExternal
                    color="blue.500"
                    fontSize="sm"
                    _hover={{ textDecoration: 'underline' }}
                  >
                    {citation.url} <ExternalLinkIcon mx="2px" />
                  </Link>
                )}
                {citation.description && !citation.title && (
                  <Text fontSize="sm" color="gray.400">
                    {citation.description}
                  </Text>
                )}
              </VStack>
            </HStack>
          </Box>
        );
      })}
    </VStack>
  );
};

export default ReferenceList;
