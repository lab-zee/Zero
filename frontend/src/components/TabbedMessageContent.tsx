import React, { useState } from 'react';
import {
  Box,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  VStack,
  Text,
  Code,
  useColorModeValue,
  Image,
  HStack,
  Badge,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
} from '@chakra-ui/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ReactECharts from 'echarts-for-react';
import { Citation, FileInfo } from '../services/api';
import ReferenceList from './ReferenceList';
import InlineCitation from './InlineCitation';

// Convert HTML <br> tags to markdown line breaks so ReactMarkdown renders them
const sanitizeHtmlLineBreaks = (text: string): string =>
  text.replace(/<br\s*\/?>/gi, '  \n');

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

interface ContentStructure {
  summary?: string;
  visualizations?: Array<{
    type: string;
    url?: string;
    data?: any;
    caption?: string;
  }>;
  raw_data?: Array<{
    label: string;
    value: any;
    type?: string;
  }>;
  references?: Citation[];
}

interface TabbedMessageContentProps {
  content: string;
  contentStructure?: ContentStructure;
  citations?: Citation[];
  files?: FileInfo[];
  userId?: number;
}

const TabbedMessageContent: React.FC<TabbedMessageContentProps> = ({
  content,
  contentStructure,
  citations,
  files,
  userId,
}) => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [highlightedCitation, setHighlightedCitation] = useState<number | null>(null);
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  // Handler to jump to and highlight a reference when citation is clicked
  const handleCitationClick = (citationNumber: number) => {
    // Switch to References tab
    const tabIndex = [
      true, // Summary always exists
      hasRawData,
      hasVisualizations,
      hasReferences,
    ].filter(Boolean).length - 1; // References is always last

    if (hasReferences) {
      setSelectedTab(tabIndex);
      setHighlightedCitation(citationNumber);

      // Clear highlight after 3 seconds
      setTimeout(() => {
        setHighlightedCitation(null);
      }, 3000);
    }
  };

  // Custom component to parse and render inline citations
  // Only match citations that are not part of markdown links [text](url)
  const renderTextWithCitations = (text: string | React.ReactNode) => {
    // Handle non-string children
    if (typeof text !== 'string') {
      return text;
    }

    const citationPattern = /\[(\d+)\](?!\()/g; // Negative lookahead to avoid matching [1](url)
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;

    while ((match = citationPattern.exec(text)) !== null) {
      // Add text before citation
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }

      // Add citation component
      const citationNumber = parseInt(match[1], 10);
      parts.push(
        <InlineCitation
          key={`citation-${match.index}-${citationNumber}`}
          number={citationNumber}
          onClick={handleCitationClick}
          isHighlighted={highlightedCitation === citationNumber}
        />
      );

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? <>{parts}</> : text;
  };

  // Check what content we have
  const imageFiles = files?.filter(f => f.content_type?.startsWith('image/')) || [];
  const hasGeneratedImages = imageFiles.length > 0;
  const hasVisualizations = (contentStructure?.visualizations && contentStructure.visualizations.length > 0) || hasGeneratedImages;
  const hasRawData = contentStructure?.raw_data && contentStructure.raw_data.length > 0;
  const hasReferences = (contentStructure?.references && contentStructure.references.length > 0) ||
                        (citations && citations.length > 0);

  // Custom img component that filters out hallucinated/malformed image URLs
  const SafeImage = (props: React.ImgHTMLAttributes<HTMLImageElement>) => {
    let src = props.src || '';
    // Reject extremely long URLs (hallucinated signatures)
    if (src.length > 500) return null;
    // Reject known hallucinated CDN domains
    if (src.includes('files.oaiusercontent.com') || src.includes('oaidalleapiprodscus.blob.core.windows.net')) return null;
    // Resolve relative uploads/ paths to full API URLs
    if (src.startsWith('uploads/')) {
      src = `${API_URL}/${src}`;
    }
    return <Image {...props} src={src} maxW="100%" borderRadius="md" my={2} />;
  };

  // If there's no special content (no visualizations, data, or references), show plain markdown
  if (!hasVisualizations && !hasRawData && !hasReferences) {
    return (
      <Box
        sx={{
          '& p': { mb: 2, lineHeight: 1.6 },
          '& h1, & h2, & h3, & h4, & h5, & h6': { fontWeight: 'bold', mt: 4, mb: 2 },
          '& h1': { fontSize: 'xl' },
          '& h2': { fontSize: 'lg' },
          '& h3': { fontSize: 'md' },
          '& ul, & ol': { pl: 4, mb: 2 },
          '& li': { mb: 1 },
          '& code': {
            bg: 'surface.800',
            px: 1,
            py: 0.5,
            borderRadius: 'sm',
            fontSize: 'sm',
            fontFamily: 'mono',
          },
          '& pre': {
            bg: 'surface.800',
            p: 2,
            borderRadius: 'md',
            overflowX: 'auto',
            mb: 2,
          },
          '& pre code': {
            bg: 'transparent',
            p: 0,
          },
          '& blockquote': {
            borderLeft: '4px solid',
            borderColor: 'gray.300',
            pl: 3,
            py: 1,
            my: 2,
            fontStyle: 'italic',
          },
        }}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            img: SafeImage as any,
            p: ({ children }) => {
              // Process children to render citations
              const processedChildren = React.Children.map(children, (child) => {
                if (typeof child === 'string') {
                  return renderTextWithCitations(child);
                }
                return child;
              });
              return <Text mb={2} lineHeight={1.6}>{processedChildren}</Text>;
            },
            // Also handle text nodes directly
            text: ({ children }) => {
              if (typeof children === 'string') {
                return <>{renderTextWithCitations(children)}</>;
              }
              return <>{children}</>;
            },
          }}
        >
          {sanitizeHtmlLineBreaks(contentStructure?.summary || content)}
        </ReactMarkdown>
      </Box>
    );
  }

  return (
    <Box>
      <Tabs index={selectedTab} onChange={setSelectedTab} variant="enclosed">
        <TabList>
          <Tab>Summary</Tab>
          {hasRawData && <Tab>Data</Tab>}
          {hasVisualizations && <Tab>Visualizations</Tab>}
          {hasReferences && <Tab>References</Tab>}
        </TabList>

        <TabPanels>
          {/* Summary Tab */}
          <TabPanel>
            <Box
              sx={{
                '& p': { mb: 2, lineHeight: 1.6 },
                '& h1, & h2, & h3, & h4, & h5, & h6': { fontWeight: 'bold', mt: 4, mb: 2 },
                '& h1': { fontSize: 'xl' },
                '& h2': { fontSize: 'lg' },
                '& h3': { fontSize: 'md' },
                '& ul, & ol': { pl: 4, mb: 2 },
                '& li': { mb: 1 },
                '& code': {
                  bg: 'surface.800',
                  px: 1,
                  py: 0.5,
                  borderRadius: 'sm',
                  fontSize: 'sm',
                  fontFamily: 'mono',
                },
                '& pre': {
                  bg: 'surface.800',
                  p: 2,
                  borderRadius: 'md',
                  overflowX: 'auto',
                  mb: 2,
                },
                '& pre code': {
                  bg: 'transparent',
                  p: 0,
                },
                '& blockquote': {
                  borderLeft: '4px solid',
                  borderColor: 'gray.300',
                  pl: 3,
                  py: 1,
                  my: 2,
                  fontStyle: 'italic',
                },
              }}
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  img: SafeImage as any,
                  p: ({ children }) => {
                    // Process children to render citations
                    const processedChildren = React.Children.map(children, (child) => {
                      if (typeof child === 'string') {
                        return renderTextWithCitations(child);
                      }
                      return child;
                    });
                    return <Text mb={2} lineHeight={1.6}>{processedChildren}</Text>;
                  },
                  // Also handle text nodes directly
                  text: ({ children }) => {
                    if (typeof children === 'string') {
                      return <>{renderTextWithCitations(children)}</>;
                    }
                    return <>{children}</>;
                  },
                }}
              >
                {sanitizeHtmlLineBreaks(contentStructure?.summary || content)}
              </ReactMarkdown>
            </Box>
          </TabPanel>

          {/* Data Tab - Render tables for dataframes, key-value for simple data */}
          {hasRawData && (
            <TabPanel>
              <VStack spacing={4} align="stretch">
                {contentStructure.raw_data?.map((item, idx) => {
                  // Check if value is an array of objects (dataframe format)
                  const isDataframe = Array.isArray(item.value) &&
                    item.value.length > 0 &&
                    typeof item.value[0] === 'object' &&
                    !Array.isArray(item.value[0]);

                  return (
                    <Box
                      key={idx}
                      p={4}
                      borderWidth={1}
                      borderColor={borderColor}
                      borderRadius="md"
                      bg={bgColor}
                    >
                      <HStack justify="space-between" mb={3}>
                        <Text fontWeight="semibold" fontSize="md">{item.label}</Text>
                        {item.type && (
                          <Badge colorScheme="blue" fontSize="xs">
                            {item.type}
                          </Badge>
                        )}
                      </HStack>

                      {isDataframe ? (
                        // Render as table for dataframe data
                        <TableContainer>
                          <Table size="sm" variant="simple">
                            <Thead>
                              <Tr>
                                {Object.keys(item.value[0]).map((key) => (
                                  <Th key={key} fontSize="xs" textTransform="none" fontWeight="semibold">
                                    {key}
                                  </Th>
                                ))}
                              </Tr>
                            </Thead>
                            <Tbody>
                              {item.value.map((row: any, rowIdx: number) => (
                                <Tr key={rowIdx}>
                                  {Object.values(row).map((cell: any, cellIdx: number) => (
                                    <Td key={cellIdx} fontSize="sm">
                                      {typeof cell === 'object' ? JSON.stringify(cell) : String(cell)}
                                    </Td>
                                  ))}
                                </Tr>
                              ))}
                            </Tbody>
                          </Table>
                        </TableContainer>
                      ) : typeof item.value === 'object' && !Array.isArray(item.value) ? (
                        // Render as key-value pairs for object data
                        <VStack spacing={2} align="stretch">
                          {Object.entries(item.value).map(([key, value]) => (
                            <HStack key={key} spacing={3} align="start">
                              <Text fontWeight="medium" fontSize="sm" minW="150px" color="gray.400">
                                {key}:
                              </Text>
                              <Text fontSize="sm" flex="1">
                                {typeof value === 'object' ? (
                                  <Code
                                    display="block"
                                    whiteSpace="pre"
                                    p={2}
                                    borderRadius="md"
                                    fontSize="xs"
                                  >
                                    {JSON.stringify(value, null, 2)}
                                  </Code>
                                ) : (
                                  String(value)
                                )}
                              </Text>
                            </HStack>
                          ))}
                        </VStack>
                      ) : Array.isArray(item.value) ? (
                        // Render as list for simple arrays
                        <VStack spacing={1} align="stretch">
                          {item.value.map((val: any, i: number) => (
                            <HStack key={i} spacing={2}>
                              <Badge colorScheme="gray" fontSize="xs">{i + 1}</Badge>
                              <Text fontSize="sm">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</Text>
                            </HStack>
                          ))}
                        </VStack>
                      ) : (
                        // Render as simple text for primitive values
                        <Text fontSize="sm">{String(item.value)}</Text>
                      )}
                    </Box>
                  );
                })}
              </VStack>
            </TabPanel>
          )}

          {/* Visualizations Tab */}
          {hasVisualizations && (
            <TabPanel>
              <VStack spacing={6} align="stretch">
                {/* ECharts visualizations from contentStructure */}
                {contentStructure?.visualizations?.map((viz, idx) => (
                  <Box
                    key={`viz-${idx}`}
                    p={4}
                    borderWidth={1}
                    borderColor={borderColor}
                    borderRadius="md"
                    bg={bgColor}
                  >
                    {viz.caption && (
                      <Text mb={3} fontSize="sm" fontWeight="semibold" color="gray.300">
                        {viz.caption}
                      </Text>
                    )}
                    {viz.url && (
                      <Image
                        src={viz.url}
                        alt={viz.caption || `Visualization ${idx + 1}`}
                        maxW="100%"
                        borderRadius="md"
                      />
                    )}
                    {viz.data && (
                      <Box bg="surface.800" p={3} borderRadius="md" borderWidth={1} minH="400px">
                        <ReactECharts
                          option={{
                            ...viz.data,
                            legend: {
                              ...(viz.data.legend || {}),
                              bottom: 0,
                              orient: viz.data.legend?.orient || 'horizontal',
                              selectedMode: 'multiple',
                              type: viz.data.legend?.type || 'scroll',
                            },
                          }}
                          style={{ height: '400px', width: '100%' }}
                          opts={{ renderer: 'canvas', locale: 'EN' }}
                        />
                      </Box>
                    )}
                  </Box>
                ))}

                {/* Generated images from files */}
                {imageFiles.map((file) => {
                  const imageUrl = `${API_URL}/api/files/${file.id}/download${userId ? `?user_id=${userId}` : ''}`;
                  return (
                    <Box
                      key={`img-${file.id}`}
                      p={4}
                      borderWidth={1}
                      borderColor={borderColor}
                      borderRadius="md"
                      bg={bgColor}
                    >
                      <Text mb={3} fontSize="sm" fontWeight="semibold" color="gray.300">
                        {file.original_filename}
                      </Text>
                      <Image
                        src={imageUrl}
                        alt={file.original_filename}
                        maxW="100%"
                        borderRadius="md"
                      />
                    </Box>
                  );
                })}
              </VStack>
            </TabPanel>
          )}

          {/* References Tab */}
          {hasReferences && (
            <TabPanel>
              <ReferenceList
                citations={contentStructure?.references || citations || []}
                highlightedNumber={highlightedCitation}
                onHover={setHighlightedCitation}
              />
            </TabPanel>
          )}
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default TabbedMessageContent;
