import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import {
  Box,
  VStack,
  Text,
  Button,
  Avatar,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useDisclosure,
  IconButton,
  HStack,
  Tooltip,
  Flex,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Badge,
  useColorModeValue,
  Input,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  useToast,
} from '@chakra-ui/react';
import {
  FiMessageSquare,
  FiSettings,
  FiCpu,
  FiPlus,
  FiChevronLeft,
  FiChevronRight,
  FiLogOut,
  FiUser,
  FiMessageCircle,
  FiMoreVertical,
  FiEdit2,
  FiTrash2,
} from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { organizationAPI, chatAPI, OrganizationWithStats } from '../services/api';
import UserProfileModal from './UserProfileModal';
import { useState, useMemo, useEffect, useRef } from 'react';
import { APP_CONFIG } from '../config';

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

const Sidebar = ({ isCollapsed, onToggleCollapse }: SidebarProps) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, logout } = useAuth();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const queryClient = useQueryClient();

  const selectedOrgId = searchParams.get('org') ? parseInt(searchParams.get('org')!) : null;
  const selectedThreadId = searchParams.get('thread') ? parseInt(searchParams.get('thread')!) : null;
  const toast = useToast();

  const [visibleThreadCount, setVisibleThreadCount] = useState(5);
  const [renamingThreadId, setRenamingThreadId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [threadToDelete, setThreadToDelete] = useState<number | null>(null);
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Mode-aware colors
  const sidebarBg = useColorModeValue('white', 'surface.900');
  const sidebarBorder = useColorModeValue('gray.200', 'whiteAlpha.100');
  const hoverBg = useColorModeValue('gray.100', 'whiteAlpha.100');
  const subtleHoverBg = useColorModeValue('gray.50', 'whiteAlpha.50');
  const activeItemBg = useColorModeValue('orange.50', 'whiteAlpha.100');
  const textMuted = useColorModeValue('gray.500', 'gray.400');
  const textSubtle = useColorModeValue('gray.400', 'gray.500');
  const textDefault = useColorModeValue('gray.700', 'gray.200');
  const accordionHoverBg = useColorModeValue('gray.50', 'whiteAlpha.50');

  const { data: organizations } = useQuery({
    queryKey: ['organizationsWithStats', user?.id],
    queryFn: () => organizationAPI.getMyOrganizationsWithStats(user!.id),
    enabled: !!user,
  });

  const { data: threads } = useQuery({
    queryKey: ['threads', user?.id, selectedOrgId],
    queryFn: () => chatAPI.getThreads(user!.id, selectedOrgId!),
    enabled: !!user && !!selectedOrgId,
  });

  const sortedThreads = useMemo(() => {
    if (!threads) return [];
    return [...threads].sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return dateB - dateA;
    });
  }, [threads]);

  const visibleThreads = useMemo(() => {
    return sortedThreads.slice(0, visibleThreadCount);
  }, [sortedThreads, visibleThreadCount]);

  const hasMoreThreads = sortedThreads.length > visibleThreadCount;

  const handleShowMore = () => {
    setVisibleThreadCount(prev => prev + 10);
  };

  useEffect(() => {
    if (selectedOrgId) {
      setVisibleThreadCount(5);
    }
  }, [selectedOrgId]);

  const handleOrgChange = (orgId: number | null) => {
    const params = new URLSearchParams();
    if (orgId) {
      params.set('org', orgId.toString());
    }
    params.delete('thread');
    setSearchParams(params, { replace: true });
  };

  const handleThreadSelect = (threadId: number, orgId: number) => {
    const params = new URLSearchParams(searchParams);
    params.set('org', orgId.toString());
    params.set('thread', threadId.toString());
    setSearchParams(params, { replace: true });
  };

  const createThreadMutation = useMutation({
    mutationFn: ({ orgId, title }: { orgId: number; title?: string }) =>
      chatAPI.createThread({ organization_id: orgId, title }, user!.id),
    onSuccess: (newThread, variables) => {
      queryClient.invalidateQueries({ queryKey: ['threads', user?.id, variables.orgId] });
      queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', user?.id] });
      const params = new URLSearchParams();
      params.set('org', variables.orgId.toString());
      params.set('thread', newThread.id.toString());
      setSearchParams(params, { replace: true });
    },
  });

  const handleCreateThread = (orgId: number) => {
    createThreadMutation.mutate({ orgId });
  };

  const renameThreadMutation = useMutation({
    mutationFn: ({ threadId, title }: { threadId: number; title: string }) =>
      chatAPI.updateThread(threadId, { title }, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threads', user?.id, selectedOrgId] });
      queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', user?.id] });
      setRenamingThreadId(null);
      toast({ title: 'Thread renamed', status: 'success', duration: 2000, isClosable: true });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to rename thread',
        description: error.response?.data?.detail || error.message,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const deleteThreadMutation = useMutation({
    mutationFn: (threadId: number) => chatAPI.deleteThread(threadId, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threads', user?.id, selectedOrgId] });
      queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', user?.id] });
      if (selectedThreadId === threadToDelete) {
        const params = new URLSearchParams(searchParams);
        params.delete('thread');
        setSearchParams(params, { replace: true });
      }
      setThreadToDelete(null);
      onDeleteClose();
      toast({ title: 'Thread deleted', status: 'success', duration: 2000, isClosable: true });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to delete thread',
        description: error.response?.data?.detail || error.message,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      setThreadToDelete(null);
      onDeleteClose();
    },
  });

  const handleRenameSubmit = (threadId: number) => {
    const trimmed = renameValue.trim();
    if (trimmed) {
      renameThreadMutation.mutate({ threadId, title: trimmed });
    } else {
      setRenamingThreadId(null);
    }
  };

  const handleDeleteConfirm = () => {
    if (threadToDelete) {
      deleteThreadMutation.mutate(threadToDelete);
    }
  };

  const formatTimeAgo = (dateString: string | undefined): string => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    const diffWeeks = Math.floor(diffDays / 7);
    const diffMonths = Math.floor(diffDays / 30);
    const diffYears = Math.floor(diffDays / 365);

    if (diffSecs < 60) return 'now';
    if (diffMins < 60) return `${diffMins}m`;
    if (diffHours < 24) return `${diffHours}h`;
    if (diffDays < 7) return `${diffDays}d`;
    if (diffWeeks < 4) return `${diffWeeks}w`;
    if (diffMonths < 12) return `${diffMonths}mo`;
    return `${diffYears}y`;
  };

  const isActive = (path: string) => location.pathname.startsWith(path);

  if (!user) return null;

  const sidebarWidth = isCollapsed ? '64px' : '260px';

  // Compute accordion index from selectedOrgId
  const accordionIndex = organizations
    ? organizations.findIndex(org => org.id === selectedOrgId)
    : -1;

  const handleAccordionChange = (index: number | number[]) => {
    const idx = Array.isArray(index) ? index[0] : index;
    if (idx === undefined || idx < 0 || !organizations) {
      handleOrgChange(null);
      return;
    }
    const org = organizations[idx];
    if (org) {
      handleOrgChange(org.id);
    }
  };

  return (
    <Box
      w={sidebarWidth}
      minW={sidebarWidth}
      h="100vh"
      bg={sidebarBg}
      borderRightWidth="1px"
      borderColor={sidebarBorder}
      display="flex"
      flexDirection="column"
      position="fixed"
      left={0}
      top={0}
      zIndex={1000}
      transition="all 0.2s ease"
      overflow="hidden"
    >
      {/* Header */}
      <Flex
        p={isCollapsed ? 2 : 3}
        borderBottomWidth="1px"
        borderColor={sidebarBorder}
        align="center"
        justify={isCollapsed ? 'center' : 'space-between'}
        minH="52px"
      >
        {!isCollapsed && (
          <Text
            fontSize="lg"
            fontWeight="700"
            color="orange.400"
            letterSpacing="-0.02em"
          >
            {APP_CONFIG.name}
          </Text>
        )}
        <IconButton
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          icon={isCollapsed ? <FiChevronRight /> : <FiChevronLeft />}
          onClick={onToggleCollapse}
          variant="ghost"
          size="sm"
          color={textMuted}
          _hover={{ color: textDefault, bg: hoverBg }}
        />
      </Flex>

      {/* Navigation */}
      <VStack align="stretch" spacing={1} p={2} flex="1" overflowY="auto">
        {/* Chat Button */}
        <Tooltip label="Chat" placement="right" isDisabled={!isCollapsed}>
          <Button
            w="100%"
            justifyContent={isCollapsed ? 'center' : 'flex-start'}
            variant="ghost"
            bg={isActive('/chat') ? activeItemBg : 'transparent'}
            color={isActive('/chat') ? 'orange.400' : textMuted}
            onClick={() => {
              // Restore last chat selection from sessionStorage when navigating back
              const storedOrgId = sessionStorage.getItem('lastChatOrgId');
              const storedThreadId = sessionStorage.getItem('lastChatThreadId');
              if (storedOrgId) {
                const params = new URLSearchParams();
                params.set('org', storedOrgId);
                if (storedThreadId) params.set('thread', storedThreadId);
                navigate(`/chat?${params.toString()}`);
              } else {
                navigate('/chat');
              }
            }}
            px={isCollapsed ? 0 : 3}
            py={2}
            borderRadius="lg"
            leftIcon={!isCollapsed ? <Box as={FiMessageSquare} boxSize="16px" /> : undefined}
            _hover={{ bg: hoverBg, color: textDefault }}
            fontSize="sm"
          >
            {isCollapsed ? <Box as={FiMessageSquare} boxSize="18px" /> : 'Chat'}
          </Button>
        </Tooltip>

        {/* Organization Accordion - Only when expanded and on chat page */}
        {!isCollapsed && isActive('/chat') && (
          <Box>
            {organizations && organizations.length > 0 ? (
              <Accordion
                index={accordionIndex >= 0 ? accordionIndex : undefined}
                onChange={handleAccordionChange}
                allowToggle
                reduceMotion
              >
                {organizations.map((org: OrganizationWithStats) => {
                  const isOrgSelected = selectedOrgId === org.id;
                  return (
                    <AccordionItem key={org.id} border="none">
                      <AccordionButton
                        px={2}
                        py={1.5}
                        borderRadius="md"
                        _hover={{ bg: accordionHoverBg }}
                        bg={isOrgSelected ? activeItemBg : 'transparent'}
                      >
                        <HStack flex="1" spacing={2} minW={0}>
                          <Text
                            fontSize="xs"
                            fontWeight={isOrgSelected ? '600' : '500'}
                            color={isOrgSelected ? 'orange.400' : textDefault}
                            noOfLines={1}
                            textAlign="left"
                          >
                            {org.name}
                          </Text>
                          <Badge
                            colorScheme="orange"
                            variant="subtle"
                            fontSize="2xs"
                            borderRadius="full"
                            px={1.5}
                            minW="auto"
                          >
                            {org.thread_count}
                          </Badge>
                        </HStack>
                        <AccordionIcon boxSize="14px" color={textMuted} />
                      </AccordionButton>
                      <AccordionPanel px={1} py={1}>
                        {/* Thread list header */}
                        <HStack justify="space-between" align="center" mb={1} px={1}>
                          <Text fontSize="2xs" fontWeight="600" color={textSubtle} textTransform="uppercase" letterSpacing="0.05em">
                            {org.total_message_count} messages
                          </Text>
                          <Tooltip label="New thread">
                            <IconButton
                              aria-label="New thread"
                              icon={<FiPlus />}
                              size="xs"
                              variant="ghost"
                              color={textMuted}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCreateThread(org.id);
                              }}
                              isLoading={createThreadMutation.isPending}
                              _hover={{ color: 'orange.400' }}
                            />
                          </Tooltip>
                        </HStack>

                        {/* Thread list */}
                        {isOrgSelected && (
                          <VStack spacing={0.5} align="stretch">
                            {visibleThreads.length > 0 ? (
                              <>
                                {visibleThreads.map((thread) => {
                                  const threadTitle = thread.title || `Thread ${thread.id}`;
                                  const isSelected = selectedThreadId === thread.id;
                                  const isRenaming = renamingThreadId === thread.id;
                                  return (
                                    <HStack
                                      key={thread.id}
                                      spacing={1}
                                      px={2}
                                      py={1.5}
                                      borderRadius="md"
                                      bg={isSelected ? activeItemBg : 'transparent'}
                                      _hover={{ bg: subtleHoverBg }}
                                      cursor="pointer"
                                      onClick={() => !isRenaming && handleThreadSelect(thread.id, org.id)}
                                      align="center"
                                      role="group"
                                    >
                                      <Box
                                        as={FiMessageCircle}
                                        boxSize="12px"
                                        color={isSelected ? 'orange.400' : textSubtle}
                                        flexShrink={0}
                                      />
                                      {isRenaming ? (
                                        <Input
                                          size="xs"
                                          value={renameValue}
                                          onChange={(e) => setRenameValue(e.target.value)}
                                          onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                              handleRenameSubmit(thread.id);
                                            } else if (e.key === 'Escape') {
                                              setRenamingThreadId(null);
                                            }
                                          }}
                                          onBlur={() => handleRenameSubmit(thread.id)}
                                          autoFocus
                                          flex="1"
                                          minW={0}
                                          fontSize="xs"
                                          onClick={(e) => e.stopPropagation()}
                                        />
                                      ) : (
                                        <Tooltip
                                          label={threadTitle}
                                          placement="right"
                                          isDisabled={threadTitle.length <= 25}
                                          hasArrow
                                        >
                                          <Text
                                            fontSize="xs"
                                            flex="1"
                                            noOfLines={1}
                                            fontWeight={isSelected ? '500' : '400'}
                                            color={isSelected ? textDefault : textMuted}
                                            minW={0}
                                          >
                                            {threadTitle}
                                          </Text>
                                        </Tooltip>
                                      )}
                                      {!isRenaming && (
                                        <>
                                          <Text
                                            fontSize="2xs"
                                            color={textSubtle}
                                            flexShrink={0}
                                            _groupHover={{ display: 'none' }}
                                          >
                                            {formatTimeAgo(thread.updated_at)}
                                          </Text>
                                          <Menu strategy="fixed">
                                            <MenuButton
                                              as={IconButton}
                                              aria-label="Thread options"
                                              icon={<FiMoreVertical />}
                                              size="xs"
                                              variant="ghost"
                                              color={textMuted}
                                              display="none"
                                              _groupHover={{ display: 'flex' }}
                                              onClick={(e) => e.stopPropagation()}
                                              minW="auto"
                                              h="auto"
                                              p={0.5}
                                              _hover={{ color: textDefault }}
                                            />
                                              <MenuList fontSize="sm" minW="140px" zIndex={2000}>
                                                <MenuItem
                                                  icon={<FiEdit2 />}
                                                  onClick={(e) => {
                                                    e.stopPropagation();
                                                    setRenameValue(thread.title || '');
                                                    setRenamingThreadId(thread.id);
                                                  }}
                                                >
                                                  Rename
                                                </MenuItem>
                                                <MenuItem
                                                  icon={<FiTrash2 />}
                                                  color="red.400"
                                                  onClick={(e) => {
                                                    e.stopPropagation();
                                                    setThreadToDelete(thread.id);
                                                    onDeleteOpen();
                                                  }}
                                                >
                                                  Delete
                                                </MenuItem>
                                              </MenuList>
                                          </Menu>
                                        </>
                                      )}
                                    </HStack>
                                  );
                                })}
                                {hasMoreThreads && (
                                  <Button
                                    size="xs"
                                    variant="ghost"
                                    color={textMuted}
                                    onClick={handleShowMore}
                                    mt={1}
                                    _hover={{ color: textDefault }}
                                    fontWeight="400"
                                  >
                                    Show more ({sortedThreads.length - visibleThreadCount})
                                  </Button>
                                )}
                              </>
                            ) : (
                              <Text fontSize="xs" color={textSubtle} textAlign="center" py={2}>
                                No threads yet
                              </Text>
                            )}
                          </VStack>
                        )}
                      </AccordionPanel>
                    </AccordionItem>
                  );
                })}
              </Accordion>
            ) : (
              <Box pl={2}>
                <Button
                  size="sm"
                  variant="outline"
                  w="100%"
                  onClick={() => navigate('/organizations/new')}
                  mb={2}
                  colorScheme="orange"
                  fontSize="xs"
                  leftIcon={<FiPlus />}
                >
                  Create Organization
                </Button>
              </Box>
            )}
          </Box>
        )}

        {/* Manage Organizations link */}
        {!isCollapsed && (
          <Tooltip label="Manage Organizations" placement="right">
            <Button
              w="100%"
              justifyContent="flex-start"
              variant="ghost"
              color={isActive('/organizations') ? 'orange.400' : textMuted}
              bg={isActive('/organizations') ? activeItemBg : 'transparent'}
              onClick={() => navigate('/organizations')}
              px={3}
              py={2}
              borderRadius="lg"
              leftIcon={<Box as={FiSettings} boxSize="16px" />}
              _hover={{ bg: hoverBg, color: textDefault }}
              fontSize="sm"
            >
              Organizations
            </Button>
          </Tooltip>
        )}

        {/* Collapsed: Org config icon only */}
        {isCollapsed && (
          <Tooltip label="Organizations" placement="right">
            <IconButton
              aria-label="Organizations"
              icon={<FiSettings />}
              variant="ghost"
              color={isActive('/organizations') ? 'orange.400' : textMuted}
              onClick={() => navigate('/organizations')}
              _hover={{ bg: hoverBg, color: textDefault }}
              w="100%"
            />
          </Tooltip>
        )}

        {/* Admin / Agent Registry */}
        <Tooltip label="Agent Registry" placement="right" isDisabled={!isCollapsed}>
          <Button
            w="100%"
            justifyContent={isCollapsed ? 'center' : 'flex-start'}
            variant="ghost"
            bg={isActive('/admin') ? activeItemBg : 'transparent'}
            color={isActive('/admin') ? 'orange.400' : textMuted}
            onClick={() => navigate('/admin')}
            px={isCollapsed ? 0 : 3}
            py={2}
            borderRadius="lg"
            leftIcon={!isCollapsed ? <Box as={FiCpu} boxSize="16px" /> : undefined}
            _hover={{ bg: hoverBg, color: textDefault }}
            fontSize="sm"
          >
            {isCollapsed ? <Box as={FiCpu} boxSize="18px" /> : 'Agent Registry'}
          </Button>
        </Tooltip>
      </VStack>

      {/* User Profile Section */}
      <Box p={2} borderTopWidth="1px" borderColor={sidebarBorder}>
        {isCollapsed ? (
          <Menu>
            <MenuButton
              as={IconButton}
              aria-label="User menu"
              icon={<Avatar size="xs" name={user.username} bg="orange.500" color="white" />}
              variant="ghost"
              w="100%"
              _hover={{ bg: hoverBg }}
            />
            <MenuList>
              <MenuItem icon={<FiUser />} onClick={onOpen}>Profile</MenuItem>
              <MenuItem icon={<FiLogOut />} onClick={logout} color="red.400">Logout</MenuItem>
            </MenuList>
          </Menu>
        ) : (
          <Menu>
            <MenuButton
              as={Button}
              variant="ghost"
              w="100%"
              justifyContent="flex-start"
              px={2}
              py={2}
              borderRadius="lg"
              _hover={{ bg: hoverBg }}
            >
              <HStack spacing={2} w="100%">
                <Avatar size="xs" name={user.username} bg="orange.500" color="white" />
                <VStack align="start" spacing={0} flex="1" overflow="hidden">
                  <Text fontSize="xs" fontWeight="500" color={textDefault} isTruncated>
                    {user.username}
                  </Text>
                  <Text fontSize="2xs" color={textMuted} isTruncated>
                    {user.email}
                  </Text>
                </VStack>
                <Box as={FiMoreVertical} boxSize="14px" color={textMuted} />
              </HStack>
            </MenuButton>
            <MenuList>
              <MenuItem icon={<FiUser />} onClick={onOpen}>Profile & Settings</MenuItem>
              <MenuItem icon={<FiLogOut />} onClick={logout} color="red.400">Logout</MenuItem>
            </MenuList>
          </Menu>
        )}
      </Box>

      <UserProfileModal isOpen={isOpen} onClose={onClose} />

      {/* Delete Thread Confirmation Dialog */}
      <AlertDialog
        isOpen={isDeleteOpen}
        leastDestructiveRef={cancelRef}
        onClose={onDeleteClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Thread
            </AlertDialogHeader>
            <AlertDialogBody>
              Are you sure you want to delete this thread? This action cannot be undone.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onDeleteClose}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={handleDeleteConfirm}
                ml={3}
                isLoading={deleteThreadMutation.isPending}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Box>
  );
};

export default Sidebar;
