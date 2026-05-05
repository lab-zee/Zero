import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  VStack,
  HStack,
  Text,
  Button,
  Input,
  FormControl,
  FormLabel,
  useToast,
  IconButton,
  Box,
  Heading,
  Select,
  Switch,
  useColorMode,
  useColorModeValue,
  Divider,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { usageAPI } from '../services/api';
import ReactECharts from 'echarts-for-react';

interface UserProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const UserProfileModal = ({ isOpen, onClose }: UserProfileModalProps) => {
  const { user } = useAuth();
  const toast = useToast();
  const { colorMode, toggleColorMode } = useColorMode();
  const [copied, setCopied] = useState(false);
  const [days, setDays] = useState(30);
  const sectionBg = useColorModeValue('gray.50', 'whiteAlpha.50');
  
  // Fetch usage stats
  const { data: usageStats, isLoading: usageLoading } = useQuery({
    queryKey: ['usageStats', user?.id, days],
    queryFn: () => usageAPI.getMyUsageStats(user!.id, days),
    enabled: !!user && isOpen,
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast({
      title: 'Copied to clipboard',
      status: 'success',
      duration: 2000,
      isClosable: true,
    });
    setTimeout(() => setCopied(false), 2000);
  };

  if (!user) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Profile & Settings</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4} align="stretch">
            <FormControl>
              <FormLabel>Username</FormLabel>
              <Input value={user.username} isReadOnly />
            </FormControl>

            <FormControl>
              <FormLabel>Email</FormLabel>
              <Input value={user.email} isReadOnly />
            </FormControl>

            <FormControl>
              <FormLabel>API Key</FormLabel>
              <HStack>
                <Input
                  value={user.api_key}
                  isReadOnly
                  fontFamily="monospace"
                  fontSize="sm"
                />
                <IconButton
                  aria-label="Copy API key"
                  icon={<Text>{copied ? '✓' : '📋'}</Text>}
                  onClick={() => copyToClipboard(user.api_key)}
                />
              </HStack>
              <Text fontSize="xs" color="gray.400" mt={1}>
                Use this API key to authenticate API requests
              </Text>
            </FormControl>

            <Box>
              <Text fontSize="sm" fontWeight="semibold" mb={2}>
                Account Information
              </Text>
              <Text fontSize="sm" color="gray.400">
                Member since: {new Date(user.created_at).toLocaleDateString()}
              </Text>
            </Box>

            <Divider />

            {/* Appearance */}
            <Box>
              <Text fontSize="sm" fontWeight="semibold" mb={3}>
                Appearance
              </Text>
              <HStack
                justify="space-between"
                p={3}
                borderRadius="lg"
                bg={sectionBg}
              >
                <HStack spacing={3}>
                  <Text fontSize="lg">{colorMode === 'dark' ? '🌙' : '☀️'}</Text>
                  <Box>
                    <Text fontSize="sm" fontWeight="medium">
                      {colorMode === 'dark' ? 'Dark mode' : 'Light mode'}
                    </Text>
                    <Text fontSize="xs" color="gray.400">
                      Toggle between light and dark themes
                    </Text>
                  </Box>
                </HStack>
                <Switch
                  isChecked={colorMode === 'dark'}
                  onChange={toggleColorMode}
                  colorScheme="orange"
                  size="md"
                />
              </HStack>
            </Box>

            {/* Usage Statistics */}
            <Box mt={4}>
              <HStack justify="space-between" mb={3}>
                <Heading size="sm">Usage Statistics</Heading>
                <Select
                  size="sm"
                  width="120px"
                  value={days}
                  onChange={(e) => setDays(parseInt(e.target.value))}
                >
                  <option value={7}>Last 7 days</option>
                  <option value={30}>Last 30 days</option>
                  <option value={90}>Last 90 days</option>
                  <option value={365}>Last year</option>
                </Select>
              </HStack>
              
              {usageLoading ? (
                <Text fontSize="sm" color="gray.400">Loading usage data...</Text>
              ) : usageStats ? (
                <VStack spacing={3} align="stretch">
                  <Box>
                    <Text fontSize="sm" color="gray.400">
                      Total API calls: <strong>{usageStats.total_count}</strong>
                    </Text>
                  </Box>
                  <Box height="250px">
                    <ReactECharts
                      option={{
                        title: {
                          text: 'Daily API Usage',
                          left: 'center',
                          textStyle: { fontSize: 14 }
                        },
                        tooltip: {
                          trigger: 'axis',
                          formatter: (params: any) => {
                            const param = params[0];
                            return `${param.name}<br/>${param.seriesName}: ${param.value}`;
                          }
                        },
                        xAxis: {
                          type: 'category',
                          data: usageStats.daily_usage.map(stat => {
                            const date = new Date(stat.date);
                            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                          }),
                          axisLabel: { rotate: 45 }
                        },
                        yAxis: {
                          type: 'value',
                          name: 'API Calls'
                        },
                        series: [{
                          name: 'API Calls',
                          type: 'line',
                          data: usageStats.daily_usage.map(stat => stat.count),
                          smooth: true,
                          areaStyle: {
                            opacity: 0.3
                          },
                          lineStyle: {
                            color: '#63b3ed'
                          },
                          itemStyle: {
                            color: '#63b3ed'
                          }
                        }],
                        grid: {
                          left: '3%',
                          right: '4%',
                          bottom: '15%',
                          containLabel: true
                        }
                      }}
                      style={{ height: '100%', width: '100%' }}
                    />
                  </Box>
                </VStack>
              ) : (
                <Text fontSize="sm" color="gray.400">No usage data available</Text>
              )}
            </Box>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button onClick={onClose}>Close</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default UserProfileModal;

