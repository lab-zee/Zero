import { useState } from 'react';
import { useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Container,
  Heading,
  VStack,
  HStack,
  Text,
  Badge,
  Spinner,
  Center,
  Divider,
  Button,
  Collapse,
  Code,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  useToast,
  IconButton,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  Switch,
  Select,
  Checkbox,
  Wrap,
  WrapItem,
  Tooltip,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
} from '@chakra-ui/react';
import { ChevronDownIcon, ChevronUpIcon, AddIcon, EditIcon, DeleteIcon } from '@chakra-ui/icons';
import { useAuth } from '../contexts/AuthContext';
import { agentAPI, AgentInfo, CustomAgent, CustomAgentCreate, usageAPI, adminAPI, AdminUserCreate } from '../services/api';
import { useTools } from '../hooks/useTools';
import ReactECharts from 'echarts-for-react';

const AgentCard = ({ agent, onEdit, onDelete }: { agent: AgentInfo | CustomAgent; onEdit?: () => void; onDelete?: () => void }) => {
  const { isOpen, onToggle } = useDisclosure();
  const isCustom = 'is_custom' in agent ? agent.is_custom : false;
  const agentId = 'id' in agent && typeof agent.id === 'number' ? `custom_${agent.id}` : agent.id;

  return (
    <Box
      borderWidth={1}
      borderRadius="lg"
      p={6}
      bg="surface.800"
      boxShadow="sm"
      _hover={{ boxShadow: 'md', transform: 'translateY(-2px)' }}
      transition="all 0.2s"
      borderColor={isCustom ? 'purple.200' : 'gray.200'}
      borderLeftWidth={isCustom ? '4px' : '1px'}
      borderLeftColor={isCustom ? 'purple.500' : undefined}
    >
      <HStack justify="space-between" mb={4}>
        <HStack>
          <Heading size="md">{agent.name}</Heading>
          {isCustom && (
            <Badge colorScheme="purple" fontSize="xs" px={2} py={1} borderRadius="full">
              Custom
            </Badge>
          )}
        </HStack>
        <HStack>
          <Badge colorScheme="blue" fontSize="sm" px={3} py={1} borderRadius="full">
            {agentId}
          </Badge>
          {isCustom && onEdit && (
            <IconButton
              aria-label="Edit agent"
              icon={<EditIcon />}
              size="sm"
              variant="ghost"
              onClick={onEdit}
            />
          )}
          {isCustom && onDelete && (
            <IconButton
              aria-label="Delete agent"
              icon={<DeleteIcon />}
              size="sm"
              variant="ghost"
              colorScheme="red"
              onClick={onDelete}
            />
          )}
        </HStack>
      </HStack>

      <Text mb={4} color="gray.300">
        {('role' in agent ? agent.role : null) || agent.description || 'No description provided'}
      </Text>

      <Divider my={4} />

      <VStack align="stretch" spacing={3}>
        {('tools' in agent && agent.tools && agent.tools.length > 0) && (
          <Box>
            <Text fontWeight="bold" mb={2} fontSize="sm" color="gray.400">
              Available Tools:
            </Text>
            <HStack spacing={2} flexWrap="wrap">
              {agent.tools.map((tool, index) => (
                <Badge
                  key={index}
                  colorScheme="orange"
                  variant="subtle"
                  fontSize="xs"
                  px={2}
                  py={1}
                  borderRadius="md"
                >
                  {tool}
                </Badge>
              ))}
            </HStack>
          </Box>
        )}

        {('can_delegate_to' in agent && agent.can_delegate_to && agent.can_delegate_to.length > 0) && (
          <Box>
            <Text fontWeight="bold" mb={2} fontSize="sm" color="gray.400">
              Can Delegate To:
            </Text>
            <HStack spacing={2} flexWrap="wrap">
              {agent.can_delegate_to.map((delegateId, index) => (
                <Badge
                  key={index}
                  colorScheme="blue"
                  variant="subtle"
                  fontSize="xs"
                  px={2}
                  py={1}
                  borderRadius="md"
                >
                  {delegateId}
                </Badge>
              ))}
            </HStack>
          </Box>
        )}

        {agent.style && (
          <Box>
            <Text fontWeight="bold" mb={2} fontSize="sm" color="gray.400">
              Response Style:
            </Text>
            <Text fontSize="sm" color="gray.300">
              {agent.style}
            </Text>
          </Box>
        )}

        {agent.use_cases && agent.use_cases.length > 0 && (
          <Box>
            <Text fontWeight="bold" mb={2} fontSize="sm" color="gray.400">
              Use Cases:
            </Text>
            <HStack spacing={2} flexWrap="wrap">
              {agent.use_cases.map((useCase, index) => (
                <Badge
                  key={index}
                  colorScheme="green"
                  variant="subtle"
                  fontSize="xs"
                  px={2}
                  py={1}
                  borderRadius="md"
                >
                  {useCase}
                </Badge>
              ))}
            </HStack>
          </Box>
        )}

        <Box>
          <Button
            size="sm"
            variant="outline"
            onClick={onToggle}
            rightIcon={isOpen ? <ChevronUpIcon /> : <ChevronDownIcon />}
            width="100%"
            mb={2}
          >
            {isOpen ? 'Hide' : 'Show'} Raw System Prompt
          </Button>
          <Collapse in={isOpen} animateOpacity>
            <Box
              p={4}
              bg="surface.900"
              borderRadius="md"
              borderWidth={1}
              borderColor="whiteAlpha.100"
              maxH="400px"
              overflowY="auto"
            >
              <Code
                display="block"
                whiteSpace="pre-wrap"
                fontSize="xs"
                p={0}
                bg="transparent"
                color="gray.200"
              >
                {agent.system_prompt}
              </Code>
            </Box>
          </Collapse>
        </Box>
      </VStack>
    </Box>
  );
};

const CustomAgentModal = ({
  isOpen,
  onClose,
  agent,
  userId,
}: {
  isOpen: boolean;
  onClose: () => void;
  agent?: CustomAgent;
  userId: number;
}) => {
  const [name, setName] = useState(agent?.name || '');
  const [description, setDescription] = useState(agent?.description || '');
  const [role, setRole] = useState(agent?.role || '');
  const [systemPrompt, setSystemPrompt] = useState(agent?.system_prompt || '');
  const [style, setStyle] = useState(agent?.style || '');
  const [useCases, setUseCases] = useState(agent?.use_cases?.join(', ') || '');
  const [isAgentic, setIsAgentic] = useState(agent?.is_agentic || false);
  const [selectedTools, setSelectedTools] = useState<string[]>(agent?.tools || []);
  const [canDelegateTo, setCanDelegateTo] = useState<string[]>(agent?.can_delegate_to || []);
  const [model, setModel] = useState(agent?.model || '');
  const [sharedWithOrg, setSharedWithOrg] = useState(agent?.shared_with_org || false);
  const toast = useToast();
  const queryClient = useQueryClient();

  // Fetch available tools and agents for pickers
  const { data: toolsData } = useTools();
  const { data: agentsData } = useQuery({
    queryKey: ['agents', userId],
    queryFn: () => agentAPI.getAgents(userId),
  });
  const availableTools = toolsData || [];
  const availableAgents = (agentsData || []).filter(
    (a: AgentInfo) => a.id !== `custom_${agent?.id}` && a.id !== 'director' && a.id !== 'synthesizer'
  );

  const createMutation = useMutation({
    mutationFn: (data: CustomAgentCreate) => agentAPI.createCustomAgent(data, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      queryClient.invalidateQueries({ queryKey: ['customAgents', userId] });
      toast({
        title: 'Custom agent created',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
      onClose();
      resetForm();
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create custom agent',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<CustomAgentCreate>) =>
      agentAPI.updateCustomAgent(agent!.id, data, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      queryClient.invalidateQueries({ queryKey: ['customAgents', userId] });
      toast({
        title: 'Custom agent updated',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
      onClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to update custom agent',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const resetForm = () => {
    setName('');
    setDescription('');
    setRole('');
    setSystemPrompt('');
    setStyle('');
    setUseCases('');
    setIsAgentic(false);
    setSelectedTools([]);
    setCanDelegateTo([]);
    setModel('');
    setSharedWithOrg(false);
  };

  const handleSubmit = () => {
    if (!name.trim() || !systemPrompt.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Name and System Prompt are required',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    const useCasesArray = useCases
      .split(',')
      .map((uc) => uc.trim())
      .filter((uc) => uc.length > 0);

    const data: CustomAgentCreate = {
      name: name.trim(),
      description: description.trim() || undefined,
      role: role.trim() || undefined,
      system_prompt: systemPrompt.trim(),
      style: style.trim() || undefined,
      use_cases: useCasesArray.length > 0 ? useCasesArray : undefined,
      is_agentic: isAgentic,
      tools: isAgentic ? selectedTools : [],
      can_delegate_to: isAgentic ? canDelegateTo : [],
      model: model.trim() || undefined,
      shared_with_org: sharedWithOrg,
    };

    if (agent) {
      updateMutation.mutate(data);
    } else {
      createMutation.mutate(data);
    }
  };

  const handleToolToggle = (toolId: string) => {
    setSelectedTools((prev) =>
      prev.includes(toolId) ? prev.filter((t) => t !== toolId) : [...prev, toolId]
    );
  };

  const handleDelegateToggle = (agentId: string) => {
    setCanDelegateTo((prev) =>
      prev.includes(agentId) ? prev.filter((a) => a !== agentId) : [...prev, agentId]
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="2xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{agent ? 'Edit Custom Agent' : 'Create Custom Agent'}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <FormControl isRequired>
              <FormLabel>Agent Name</FormLabel>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Technical Writer"
              />
            </FormControl>

            <FormControl>
              <FormLabel>Description</FormLabel>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of what this agent does"
                rows={2}
              />
            </FormControl>

            <FormControl>
              <FormLabel>Role</FormLabel>
              <Input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g., Expert in technical documentation and API design"
              />
              <Text fontSize="xs" color="gray.400" mt={1}>
                One-line role description used by the director when choosing which agent to delegate to.
              </Text>
            </FormControl>

            <FormControl isRequired>
              <FormLabel>System Prompt</FormLabel>
              <Textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="Enter the system prompt that defines this agent's behavior..."
                rows={10}
                fontFamily="mono"
                fontSize="sm"
              />
              <Text fontSize="xs" color="gray.400" mt={1}>
                This prompt defines how the agent will behave and respond to queries.
              </Text>
            </FormControl>

            <Divider />

            <FormControl display="flex" alignItems="center">
              <FormLabel htmlFor="is-agentic" mb="0">
                Agentic Mode
              </FormLabel>
              <Switch
                id="is-agentic"
                isChecked={isAgentic}
                onChange={(e) => setIsAgentic(e.target.checked)}
                colorScheme="green"
              />
              <Text fontSize="xs" color="gray.400" ml={3}>
                {isAgentic
                  ? 'Agent participates in the crew system with tools and delegation'
                  : 'Agent is a standalone chat persona'}
              </Text>
            </FormControl>

            {isAgentic && (
              <>
                <FormControl>
                  <FormLabel>Model Override</FormLabel>
                  <Select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder="Use default model"
                  >
                    <option value="gemini-3-flash-preview">Gemini 3 Flash</option>
                    <option value="gpt-4o">GPT-4o</option>
                    <option value="gpt-4o-mini">GPT-4o Mini</option>
                    <option value="claude-sonnet-4-5-20250929">Claude Sonnet 4.5</option>
                  </Select>
                </FormControl>

                <FormControl>
                  <FormLabel>Tools</FormLabel>
                  <Text fontSize="xs" color="gray.400" mb={2}>
                    Select which tools this agent can use during execution.
                  </Text>
                  <Wrap spacing={2}>
                    {availableTools.map((tool) => (
                      <WrapItem key={tool.id}>
                        <Tooltip label={tool.description} placement="top" hasArrow>
                          <Box>
                            <Checkbox
                              isChecked={selectedTools.includes(tool.id)}
                              onChange={() => handleToolToggle(tool.id)}
                              size="sm"
                            >
                              {tool.name}
                            </Checkbox>
                          </Box>
                        </Tooltip>
                      </WrapItem>
                    ))}
                  </Wrap>
                </FormControl>

                <FormControl>
                  <FormLabel>Can Delegate To</FormLabel>
                  <Text fontSize="xs" color="gray.400" mb={2}>
                    Select which other agents this agent can delegate tasks to.
                  </Text>
                  <Wrap spacing={2}>
                    {availableAgents.map((a: AgentInfo) => (
                      <WrapItem key={a.id}>
                        <Tooltip label={a.role || a.description} placement="top" hasArrow>
                          <Box>
                            <Checkbox
                              isChecked={canDelegateTo.includes(a.id)}
                              onChange={() => handleDelegateToggle(a.id)}
                              size="sm"
                            >
                              {a.name}
                            </Checkbox>
                          </Box>
                        </Tooltip>
                      </WrapItem>
                    ))}
                  </Wrap>
                </FormControl>
              </>
            )}

            <Divider />

            <FormControl display="flex" alignItems="center">
              <FormLabel htmlFor="shared-with-org" mb="0">
                Share with Organization
              </FormLabel>
              <Switch
                id="shared-with-org"
                isChecked={sharedWithOrg}
                onChange={(e) => setSharedWithOrg(e.target.checked)}
                colorScheme="blue"
              />
              <Text fontSize="xs" color="gray.400" ml={3}>
                {sharedWithOrg
                  ? 'All organization members can use this agent'
                  : 'Only you can use this agent'}
              </Text>
            </FormControl>

            <FormControl>
              <FormLabel>Response Style</FormLabel>
              <Input
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                placeholder="e.g., Concise, technical, code-focused"
              />
            </FormControl>

            <FormControl>
              <FormLabel>Use Cases (comma-separated)</FormLabel>
              <Input
                value={useCases}
                onChange={(e) => setUseCases(e.target.value)}
                placeholder="e.g., Code documentation, Technical writing, API docs"
              />
              <Text fontSize="xs" color="gray.400" mt={1}>
                Separate multiple use cases with commas
              </Text>
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancel
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSubmit}
            isLoading={createMutation.isPending || updateMutation.isPending}
          >
            {agent ? 'Update' : 'Create'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

const Admin = () => {
  const { user } = useAuth();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [editingAgent, setEditingAgent] = useState<CustomAgent | undefined>();
  const deleteDialog = useDisclosure();
  const invalidateAllDialog = useDisclosure();
  const resetTokenModal = useDisclosure();
  const [agentToDelete, setAgentToDelete] = useState<CustomAgent | undefined>();
  const cancelDeleteRef = useRef<HTMLButtonElement>(null);
  const cancelInvalidateAllRef = useRef<HTMLButtonElement>(null);
  const [resetTokenData, setResetTokenData] = useState<{ token: string; reset_url: string; expires_in_hours: number; username: string } | null>(null);
  const createUserModal = useDisclosure();
  const [createUserForm, setCreateUserForm] = useState<AdminUserCreate>({ email: '', username: '', password: '', is_admin: false });
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data: agents, isLoading } = useQuery({
    queryKey: ['agents', user?.id],
    queryFn: () => agentAPI.getAgents(user?.id),
    enabled: !!user,
  });

  const { data: customAgents } = useQuery({
    queryKey: ['customAgents', user?.id],
    queryFn: () => agentAPI.getCustomAgents(user!.id),
    enabled: !!user,
  });

  const { data: tools } = useQuery({
    queryKey: ['tools'],
    queryFn: () => agentAPI.getTools(),
  });

  const { data: users, isLoading: usersLoading } = useQuery({
    queryKey: ['allUsers'],
    queryFn: () => adminAPI.getUsers(),
    enabled: !!user && user.is_admin,
  });

  const updateUserMutation = useMutation({
    mutationFn: ({ targetUserId, update }: { targetUserId: number; update: { is_admin?: boolean; is_active?: boolean } }) =>
      adminAPI.updateUser(targetUserId, user!.id, update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['allUsers'] });
      toast({
        title: 'User updated successfully',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error updating user',
        description: error.response?.data?.detail || 'Failed to update user',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const invalidateSessionMutation = useMutation({
    mutationFn: (targetUserId: number) =>
      adminAPI.invalidateUserSession(targetUserId, user!.id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['allUsers'] });
      toast({
        title: data.message,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error invalidating session',
        description: error.response?.data?.detail || 'Failed to invalidate session',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const invalidateAllSessionsMutation = useMutation({
    mutationFn: () => adminAPI.invalidateAllSessions(user!.id),
    onSuccess: (data) => {
      toast({
        title: data.message,
        status: 'warning',
        duration: 5000,
        isClosable: true,
      });
      invalidateAllDialog.onClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Error invalidating sessions',
        description: error.response?.data?.detail || 'Failed to invalidate all sessions',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const generateResetTokenMutation = useMutation({
    mutationFn: (targetUserId: number) =>
      adminAPI.generatePasswordResetToken(targetUserId, user!.id),
    onSuccess: (data, targetUserId) => {
      const targetUser = users?.find((u) => u.id === targetUserId);
      setResetTokenData({
        token: data.token,
        reset_url: data.reset_url,
        expires_in_hours: data.expires_in_hours,
        username: targetUser?.username || 'Unknown',
      });
      resetTokenModal.onOpen();
    },
    onError: (error: any) => {
      toast({
        title: 'Error generating reset token',
        description: error.response?.data?.detail || 'Failed to generate reset token',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const createUserMutation = useMutation({
    mutationFn: (data: AdminUserCreate) => adminAPI.createUser(user!.id, data),
    onSuccess: (newUser) => {
      queryClient.invalidateQueries({ queryKey: ['allUsers'] });
      toast({
        title: `User "${newUser.username}" created successfully`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      createUserModal.onClose();
      setCreateUserForm({ email: '', username: '', password: '', is_admin: false });
    },
    onError: (error: any) => {
      toast({
        title: 'Error creating user',
        description: error.response?.data?.detail || 'Failed to create user',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const [usageDays, setUsageDays] = useState(30);
  const { data: allUsersUsage, isLoading: usageLoading } = useQuery({
    queryKey: ['allUsersUsage', user?.id, usageDays],
    queryFn: () => usageAPI.getAllUsersUsageStats(user!.id, usageDays),
    enabled: !!user,
  });

  const deleteMutation = useMutation({
    mutationFn: (agentId: number) => agentAPI.deleteCustomAgent(agentId, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      queryClient.invalidateQueries({ queryKey: ['customAgents', user?.id] });
      toast({
        title: 'Custom agent deleted',
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
      deleteDialog.onClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete custom agent',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const handleEdit = (agent: CustomAgent) => {
    setEditingAgent(agent);
    onOpen();
  };

  const handleDelete = (agent: CustomAgent) => {
    setAgentToDelete(agent);
    deleteDialog.onOpen();
  };

  const handleCreate = () => {
    setEditingAgent(undefined);
    onOpen();
  };

  const handleClose = () => {
    onClose();
    setEditingAgent(undefined);
  };

  if (isLoading) {
    return (
      <Container maxW="7xl" py={8}>
        <Center py={8}>
          <Spinner size="xl" />
        </Center>
      </Container>
    );
  }

  const builtInAgents = agents?.filter((a) => !a.is_custom) || [];
  const userCustomAgents = agents?.filter((a) => a.is_custom) || [];

  return (
    <Container maxW="7xl" py={8}>
      <HStack justify="space-between" mb={6}>
        <Box>
          <Heading mb={2}>Agent Registry</Heading>
          <Text color="gray.400">
            View and manage all available AI agents and prompt systems.
          </Text>
        </Box>
        {user && (
          <Button leftIcon={<AddIcon />} colorScheme="blue" onClick={handleCreate}>
            Create Custom Agent
          </Button>
        )}
      </HStack>

      {/* Custom Agents Section */}
      {user && userCustomAgents.length > 0 && (
        <Box mb={8}>
          <Heading size="md" mb={4}>
            Your Custom Agents
          </Heading>
          <VStack spacing={4} align="stretch">
            {userCustomAgents.map((agent) => {
              const customAgent = customAgents?.find(
                (ca) => `custom_${ca.id}` === agent.id
              );
              if (!customAgent) return null;
              return (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  onEdit={() => handleEdit(customAgent)}
                  onDelete={() => handleDelete(customAgent)}
                />
              );
            })}
          </VStack>
        </Box>
      )}

      {/* Built-in Agents Section */}
      <Box>
        <Heading size="md" mb={4}>
          Built-in Agents
        </Heading>
        <VStack spacing={4} align="stretch">
          {builtInAgents.length > 0 ? (
            builtInAgents.map((agent) => <AgentCard key={agent.id} agent={agent} />)
          ) : (
            <Center py={8}>
              <Text color="gray.400">No agents found.</Text>
            </Center>
          )}
        </VStack>
      </Box>

      {/* Tools Section */}
      <Box mt={8}>
        <Heading size="md" mb={4}>
          Available Tools
        </Heading>
        <Box p={4} bg="surface.800" borderRadius="lg" borderWidth={1} borderColor="whiteAlpha.100">
          {tools && tools.length > 0 ? (
            <>
              <HStack spacing={2} flexWrap="wrap" mb={3}>
                {tools.map((tool) => (
                  <Badge
                    key={tool.id}
                    colorScheme="orange"
                    fontSize="sm"
                    px={3}
                    py={1}
                    borderRadius="full"
                    title={tool.description}
                  >
                    {tool.id}
                  </Badge>
                ))}
              </HStack>
              <Text fontSize="xs" color="gray.400" mt={3}>
                Tools are used by agents to perform specific tasks. Each agent has access to a subset of these tools based on their role.
              </Text>
            </>
          ) : (
            <Text color="gray.400">Loading tools...</Text>
          )}
        </Box>
      </Box>

      {/* User Management Section */}
      {user && user.is_admin && (
        <Box mt={8}>
          <HStack justify="space-between" mb={4}>
            <Box>
              <Heading size="md">User Management</Heading>
              <Text color="gray.400" mt={1}>
                Manage user accounts, admin permissions, and user status.
              </Text>
            </Box>
            <HStack spacing={2}>
              <Button
                colorScheme="green"
                size="sm"
                leftIcon={<AddIcon />}
                onClick={createUserModal.onOpen}
              >
                Create User
              </Button>
              <Button
                colorScheme="red"
                size="sm"
                variant="outline"
                onClick={invalidateAllDialog.onOpen}
              >
                Invalidate All Sessions
              </Button>
            </HStack>
          </HStack>

          {usersLoading ? (
            <Center py={8}>
              <Spinner />
            </Center>
          ) : users && users.length > 0 ? (
            <TableContainer
              borderWidth={1}
              borderRadius="lg"
              borderColor="whiteAlpha.100"
              bg="surface.800"
              boxShadow="sm"
            >
              <Table variant="simple">
                <Thead bg="surface.900">
                  <Tr>
                    <Th>User</Th>
                    <Th>Email</Th>
                    <Th>Admin</Th>
                    <Th>Active</Th>
                    <Th>Joined</Th>
                    <Th>Actions</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {users.map((targetUser) => (
                    <Tr key={targetUser.id}>
                      <Td>
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="medium">{targetUser.username}</Text>
                          <Badge colorScheme="gray" fontSize="xs">
                            ID: {targetUser.id}
                          </Badge>
                        </VStack>
                      </Td>
                      <Td>
                        <Text fontSize="sm">{targetUser.email}</Text>
                      </Td>
                      <Td>
                        <HStack>
                          <Switch
                            isChecked={targetUser.is_admin}
                            isDisabled={targetUser.id === user.id || updateUserMutation.isPending}
                            onChange={(e) => {
                              updateUserMutation.mutate({
                                targetUserId: targetUser.id,
                                update: { is_admin: e.target.checked },
                              });
                            }}
                            colorScheme="purple"
                          />
                          {targetUser.is_admin && (
                            <Badge colorScheme="purple" fontSize="xs">
                              Admin
                            </Badge>
                          )}
                        </HStack>
                      </Td>
                      <Td>
                        <HStack>
                          <Switch
                            isChecked={targetUser.is_active}
                            isDisabled={targetUser.id === user.id || updateUserMutation.isPending}
                            onChange={(e) => {
                              updateUserMutation.mutate({
                                targetUserId: targetUser.id,
                                update: { is_active: e.target.checked },
                              });
                            }}
                            colorScheme="green"
                          />
                          <Badge colorScheme={targetUser.is_active ? 'green' : 'red'} fontSize="xs">
                            {targetUser.is_active ? 'Active' : 'Disabled'}
                          </Badge>
                        </HStack>
                      </Td>
                      <Td>
                        <Text fontSize="sm" color="gray.400">
                          {new Date(targetUser.created_at).toLocaleDateString()}
                        </Text>
                      </Td>
                      <Td>
                        <HStack spacing={2}>
                          <Button
                            size="xs"
                            colorScheme="orange"
                            variant="outline"
                            isDisabled={invalidateSessionMutation.isPending}
                            onClick={() => invalidateSessionMutation.mutate(targetUser.id)}
                          >
                            Invalidate Session
                          </Button>
                          <Button
                            size="xs"
                            colorScheme="blue"
                            variant="outline"
                            isDisabled={generateResetTokenMutation.isPending}
                            onClick={() => generateResetTokenMutation.mutate(targetUser.id)}
                          >
                            Reset Password
                          </Button>
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </TableContainer>
          ) : (
            <Box p={4} bg="surface.900" borderRadius="md" borderWidth={1}>
              <Text color="gray.400" textAlign="center">
                No users found
              </Text>
            </Box>
          )}
        </Box>
      )}

      {/* Usage Statistics Section */}
      <Box mt={8}>
        <HStack justify="space-between" mb={4}>
          <Box>
            <Heading size="md" mb={2}>User Usage Statistics</Heading>
            <Text color="gray.400">
              Track API usage across all users over time.
            </Text>
          </Box>
          <select
            style={{ padding: '8px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.1)' }}
            value={usageDays}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setUsageDays(parseInt(e.target.value))}
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
        </HStack>

        {usageLoading ? (
          <Center py={8}>
            <Spinner />
          </Center>
        ) : allUsersUsage && allUsersUsage.length > 0 ? (
          <VStack spacing={6} align="stretch">
            {allUsersUsage.map((userUsage) => {
              const totalCalls = userUsage.daily_usage.reduce((sum, day) => sum + day.count, 0);
              return (
                <Box
                  key={userUsage.user_id}
                  borderWidth={1}
                  borderRadius="lg"
                  p={6}
                  bg="surface.800"
                  boxShadow="sm"
                >
                  <HStack justify="space-between" mb={4}>
                    <VStack align="start" spacing={1}>
                      <Text fontWeight="bold" fontSize="md">
                        {userUsage.username}
                      </Text>
                      <Text fontSize="sm" color="gray.400">
                        {userUsage.email}
                      </Text>
                    </VStack>
                    <Badge colorScheme="blue" fontSize="md" px={3} py={1}>
                      Total: {totalCalls} calls
                    </Badge>
                  </HStack>
                  
                  <Box height="200px">
                    <ReactECharts
                      option={{
                        tooltip: {
                          trigger: 'axis',
                          formatter: (params: any) => {
                            const param = params[0];
                            return `${param.name}<br/>${param.seriesName}: ${param.value}`;
                          }
                        },
                        xAxis: {
                          type: 'category',
                          data: userUsage.daily_usage.map(stat => {
                            const date = new Date(stat.date);
                            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                          }),
                          axisLabel: { rotate: 45, fontSize: 10 }
                        },
                        yAxis: {
                          type: 'value',
                          name: 'API Calls'
                        },
                        series: [{
                          name: 'API Calls',
                          type: 'line',
                          data: userUsage.daily_usage.map(stat => stat.count),
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
                          bottom: '20%',
                          containLabel: true
                        }
                      }}
                      style={{ height: '100%', width: '100%' }}
                    />
                  </Box>
                </Box>
              );
            })}
          </VStack>
        ) : (
          <Box p={4} bg="surface.900" borderRadius="md" borderWidth={1}>
            <Text color="gray.400" textAlign="center">
              No usage data available
            </Text>
          </Box>
        )}
      </Box>

      <Box mt={8} p={4} bg="whiteAlpha.50" borderRadius="md" borderWidth={1} borderColor="blue.700">
        <Text fontSize="sm" color="blue.300">
          <strong>Note:</strong> This is an agentic system where the Strategic Director orchestrates specialist agents. 
          Agents can use tools and delegate to other agents. The system automatically routes queries through the appropriate agents.
        </Text>
      </Box>

      {/* Create/Edit Modal */}
      {user && (
        <CustomAgentModal
          isOpen={isOpen}
          onClose={handleClose}
          agent={editingAgent}
          userId={user.id}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        isOpen={deleteDialog.isOpen}
        leastDestructiveRef={cancelDeleteRef}
        onClose={deleteDialog.onClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Custom Agent
            </AlertDialogHeader>

            <AlertDialogBody>
              Are you sure you want to delete "{agentToDelete?.name}"? This action cannot be undone.
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelDeleteRef} onClick={deleteDialog.onClose}>Cancel</Button>
              <Button
                colorScheme="red"
                onClick={() => agentToDelete && deleteMutation.mutate(agentToDelete.id)}
                ml={3}
                isLoading={deleteMutation.isPending}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>

      {/* Invalidate All Sessions Confirmation Dialog */}
      <AlertDialog
        isOpen={invalidateAllDialog.isOpen}
        leastDestructiveRef={cancelInvalidateAllRef}
        onClose={invalidateAllDialog.onClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent bg="surface.800">
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Invalidate All Sessions
            </AlertDialogHeader>

            <AlertDialogBody>
              <VStack align="start" spacing={3}>
                <Text>
                  This will rotate every user's API key, forcing all users to re-login — including you.
                </Text>
                <Text fontWeight="bold" color="red.300">
                  You will be logged out immediately after this action.
                </Text>
              </VStack>
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelInvalidateAllRef} onClick={invalidateAllDialog.onClose}>Cancel</Button>
              <Button
                colorScheme="red"
                onClick={() => invalidateAllSessionsMutation.mutate()}
                ml={3}
                isLoading={invalidateAllSessionsMutation.isPending}
              >
                Invalidate All
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>

      {/* Create User Modal */}
      <Modal isOpen={createUserModal.isOpen} onClose={() => { createUserModal.onClose(); setCreateUserForm({ email: '', username: '', password: '', is_admin: false }); }} size="md">
        <ModalOverlay />
        <ModalContent bg="surface.800">
          <ModalHeader>Create User Account</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Email</FormLabel>
                <Input
                  type="email"
                  placeholder="user@example.com"
                  value={createUserForm.email}
                  onChange={(e) => setCreateUserForm({ ...createUserForm, email: e.target.value })}
                />
              </FormControl>
              <FormControl isRequired>
                <FormLabel>Username</FormLabel>
                <Input
                  placeholder="username"
                  value={createUserForm.username}
                  onChange={(e) => setCreateUserForm({ ...createUserForm, username: e.target.value })}
                />
              </FormControl>
              <FormControl isRequired>
                <FormLabel>Password</FormLabel>
                <Input
                  type="password"
                  placeholder="Password"
                  value={createUserForm.password}
                  onChange={(e) => setCreateUserForm({ ...createUserForm, password: e.target.value })}
                />
              </FormControl>
              <FormControl display="flex" alignItems="center">
                <FormLabel mb="0">Make Admin</FormLabel>
                <Switch
                  colorScheme="purple"
                  isChecked={createUserForm.is_admin}
                  onChange={(e) => setCreateUserForm({ ...createUserForm, is_admin: e.target.checked })}
                />
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={() => { createUserModal.onClose(); setCreateUserForm({ email: '', username: '', password: '', is_admin: false }); }}>
              Cancel
            </Button>
            <Button
              colorScheme="green"
              onClick={() => createUserMutation.mutate(createUserForm)}
              isLoading={createUserMutation.isPending}
              isDisabled={!createUserForm.email || !createUserForm.username || !createUserForm.password}
            >
              Create User
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Password Reset Token Modal */}
      <Modal isOpen={resetTokenModal.isOpen} onClose={resetTokenModal.onClose} size="lg">
        <ModalOverlay />
        <ModalContent bg="surface.800">
          <ModalHeader>Password Reset Token</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {resetTokenData && (
              <VStack align="stretch" spacing={4}>
                <Text>
                  Reset token generated for <strong>{resetTokenData.username}</strong>.
                  Share the URL below with the user. It expires in {resetTokenData.expires_in_hours} hour(s).
                </Text>
                <FormControl>
                  <FormLabel fontSize="sm" color="gray.300">Reset URL</FormLabel>
                  <HStack>
                    <Input
                      value={`${window.location.origin}${resetTokenData.reset_url}`}
                      isReadOnly
                      fontSize="sm"
                    />
                    <Button
                      size="sm"
                      colorScheme="blue"
                      onClick={() => {
                        navigator.clipboard.writeText(`${window.location.origin}${resetTokenData.reset_url}`);
                        toast({
                          title: 'Copied to clipboard',
                          status: 'success',
                          duration: 2000,
                          isClosable: true,
                        });
                      }}
                    >
                      Copy
                    </Button>
                  </HStack>
                </FormControl>
                <FormControl>
                  <FormLabel fontSize="sm" color="gray.300">Token (raw)</FormLabel>
                  <HStack>
                    <Input
                      value={resetTokenData.token}
                      isReadOnly
                      fontSize="sm"
                      fontFamily="mono"
                    />
                    <Button
                      size="sm"
                      colorScheme="blue"
                      variant="outline"
                      onClick={() => {
                        navigator.clipboard.writeText(resetTokenData.token);
                        toast({
                          title: 'Token copied to clipboard',
                          status: 'success',
                          duration: 2000,
                          isClosable: true,
                        });
                      }}
                    >
                      Copy
                    </Button>
                  </HStack>
                </FormControl>
              </VStack>
            )}
          </ModalBody>
          <ModalFooter>
            <Button onClick={resetTokenModal.onClose}>Close</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
};

export default Admin;
