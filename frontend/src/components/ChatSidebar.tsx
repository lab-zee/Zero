import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  VStack,
  Text,
  Button,
  IconButton,
  HStack,
  Tooltip,
  Flex,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Input,
  InputGroup,
  InputLeftElement,
  useDisclosure,
  useColorModeValue,
  Drawer,
  DrawerOverlay,
  DrawerContent,
  DrawerBody,
  DrawerHeader,
  Divider,
} from '@chakra-ui/react';
import {
  FiPlus,
  FiX,
  FiMessageSquare,
  FiSettings,
  FiCpu,
  FiMoreHorizontal,
  FiTrash2,
  FiSearch,
} from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { organizationAPI, chatAPI, Thread } from '../services/api';
import QuickWorkspaceModal from './QuickWorkspaceModal';
import { APP_CONFIG } from '../config';
import { useMemo, useState } from 'react';

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const ChatSidebar = ({ isOpen, onClose }: ChatSidebarProps) => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { isOpen: isWorkspaceOpen, onOpen: onWorkspaceOpen, onClose: onWorkspaceClose } = useDisclosure();
  const [threadQuery, setThreadQuery] = useState('');

  const selectedOrgId = searchParams.get('org') ? parseInt(searchParams.get('org')!, 10) : null;
  const selectedThreadId = searchParams.get('thread') ? parseInt(searchParams.get('thread')!, 10) : null;

  const bg = useColorModeValue('white', 'surface.900');
  const border = useColorModeValue('gray.200', 'whiteAlpha.100');
  const hoverBg = useColorModeValue('gray.100', 'whiteAlpha.100');
  const activeBg = useColorModeValue('gray.200', 'whiteAlpha.150');
  const muted = useColorModeValue('gray.600', 'gray.400');

  const { data: organizations } = useQuery({
    queryKey: ['organizationsWithStats', user?.id],
    queryFn: () => organizationAPI.getMyOrganizationsWithStats(user!.id),
    enabled: !!user,
  });

  const activeOrgId = selectedOrgId ?? organizations?.[0]?.id ?? null;

  const { data: threads } = useQuery({
    queryKey: ['threads', user?.id, activeOrgId],
    queryFn: () => chatAPI.getThreads(user!.id, activeOrgId!),
    enabled: !!user && !!activeOrgId,
  });

  const recentThreads = useMemo(() => {
    if (!threads) return [];
    const q = threadQuery.trim().toLowerCase();
    return [...threads]
      .sort((a, b) => {
        const da = new Date(a.updated_at || a.created_at || 0).getTime();
        const db = new Date(b.updated_at || b.created_at || 0).getTime();
        return db - da;
      })
      .filter((t) => {
        if (!q) return true;
        const title = (t.title || 'New chat').toLowerCase();
        return title.includes(q);
      })
      .slice(0, q ? 50 : 20);
  }, [threads, threadQuery]);

  const createThreadMutation = useMutation({
    mutationFn: (orgId: number) =>
      chatAPI.createThread({ organization_id: orgId }, user!.id),
    onSuccess: (thread, orgId) => {
      queryClient.invalidateQueries({ queryKey: ['threads', user?.id, orgId] });
      const params = new URLSearchParams();
      params.set('org', orgId.toString());
      params.set('thread', thread.id.toString());
      setSearchParams(params, { replace: true });
      navigate(`/chat?${params.toString()}`);
      onClose();
    },
  });

  const deleteThreadMutation = useMutation({
    mutationFn: (threadId: number) => chatAPI.deleteThread(threadId, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threads', user?.id, activeOrgId] });
      if (selectedThreadId) {
        const params = new URLSearchParams(searchParams);
        params.delete('thread');
        setSearchParams(params, { replace: true });
      }
    },
  });

  const selectThread = (thread: Thread) => {
    if (!activeOrgId) return;
    const params = new URLSearchParams();
    params.set('org', activeOrgId.toString());
    params.set('thread', thread.id.toString());
    setSearchParams(params, { replace: true });
    navigate(`/chat?${params.toString()}`);
    onClose();
  };

  const handleNewChat = () => {
    if (!activeOrgId) {
      onWorkspaceOpen();
      return;
    }
    createThreadMutation.mutate(activeOrgId);
  };

  const handleWorkspaceCreated = (orgId: number) => {
    const params = new URLSearchParams();
    params.set('org', orgId.toString());
    setSearchParams(params, { replace: true });
    createThreadMutation.mutate(orgId);
  };

  const threadTitle = (t: Thread) => t.title || 'New chat';
  const activeOrgName = organizations?.find((o) => o.id === activeOrgId)?.name;

  return (
    <>
      <Drawer isOpen={isOpen} placement="left" onClose={onClose} size="xs">
        <DrawerOverlay bg="blackAlpha.600" />
        <DrawerContent bg={bg} maxW="280px">
          <DrawerHeader px={3} py={3} borderBottomWidth="1px" borderColor={border}>
            <Flex align="center" justify="space-between">
              <Text fontWeight="600" fontSize="sm" color={muted}>
                {APP_CONFIG.name}
              </Text>
              <IconButton
                aria-label="Close sidebar"
                icon={<FiX />}
                size="sm"
                variant="ghost"
                onClick={onClose}
              />
            </Flex>
          </DrawerHeader>
          <DrawerBody px={2} py={3} display="flex" flexDirection="column">
            <Button
              leftIcon={<FiPlus />}
              justifyContent="flex-start"
              variant="outline"
              size="sm"
              mb={3}
              borderRadius="lg"
              onClick={handleNewChat}
              isLoading={createThreadMutation.isPending}
            >
              New chat
            </Button>

            {activeOrgName && (
              <Text fontSize="2xs" color={muted} px={2} mb={1} noOfLines={1}>
                {activeOrgName}
              </Text>
            )}

            <InputGroup size="sm" mb={2} px={1}>
              <InputLeftElement pointerEvents="none">
                <Box as={FiSearch} color={muted} boxSize="14px" />
              </InputLeftElement>
              <Input
                placeholder="Search chats"
                value={threadQuery}
                onChange={(e) => setThreadQuery(e.target.value)}
                borderRadius="md"
                aria-label="Search chats"
              />
            </InputGroup>

            <Text fontSize="xs" color={muted} px={2} mb={2} fontWeight="500">
              {threadQuery.trim() ? 'Results' : 'Recent'}
            </Text>
            <VStack align="stretch" spacing={0.5} flex="1" overflowY="auto">
              {!activeOrgId && (
                <Button size="sm" variant="ghost" onClick={onWorkspaceOpen}>
                  Create a workspace to start
                </Button>
              )}
              {activeOrgId && recentThreads.length === 0 && (
                <Text fontSize="xs" color={muted} px={2} py={2}>
                  {threadQuery.trim() ? 'No matching chats' : 'No chats yet'}
                </Text>
              )}
              {recentThreads.map((thread) => {
                const isActive = selectedThreadId === thread.id;
                return (
                  <HStack
                    key={thread.id}
                    px={2}
                    py={2}
                    borderRadius="md"
                    bg={isActive ? activeBg : 'transparent'}
                    _hover={{ bg: hoverBg }}
                    cursor="pointer"
                    onClick={() => selectThread(thread)}
                    role="group"
                  >
                    <Box as={FiMessageSquare} boxSize="14px" color={muted} flexShrink={0} />
                    <Text fontSize="sm" noOfLines={1} flex="1" color={isActive ? 'inherit' : muted}>
                      {threadTitle(thread)}
                    </Text>
                    <Menu>
                      <MenuButton
                        as={IconButton}
                        aria-label="Thread menu"
                        icon={<FiMoreHorizontal />}
                        size="xs"
                        variant="ghost"
                        opacity={0}
                        _groupHover={{ opacity: 1 }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <MenuList minW="120px">
                        <MenuItem
                          icon={<FiTrash2 />}
                          color="red.400"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteThreadMutation.mutate(thread.id);
                          }}
                        >
                          Delete
                        </MenuItem>
                      </MenuList>
                    </Menu>
                  </HStack>
                );
              })}
            </VStack>

            <Divider my={3} borderColor={border} />

            <VStack align="stretch" spacing={1}>
              <Tooltip label="Workspace settings, members, files">
                <Button
                  leftIcon={<FiSettings />}
                  variant="ghost"
                  size="sm"
                  justifyContent="flex-start"
                  onClick={() => {
                    navigate('/organizations');
                    onClose();
                  }}
                >
                  Workspaces
                </Button>
              </Tooltip>
              <Button
                leftIcon={<FiCpu />}
                variant="ghost"
                size="sm"
                justifyContent="flex-start"
                onClick={() => {
                  navigate('/admin');
                  onClose();
                }}
              >
                Agents
              </Button>
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      {user && (
        <QuickWorkspaceModal
          isOpen={isWorkspaceOpen}
          onClose={onWorkspaceClose}
          userId={user.id}
          onCreated={handleWorkspaceCreated}
        />
      )}
    </>
  );
};

export default ChatSidebar;
