import {
  Box,
  HStack,
  Text,
  IconButton,
  Select,
  Badge,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiMenu, FiMoreVertical, FiShare2, FiDownload, FiSettings } from 'react-icons/fi';
import { useSidebar } from '../contexts/SidebarContext';
import { APP_CONFIG } from '../config';
import { Organization } from '../services/api';

interface ChatTopBarProps {
  organizations?: Organization[];
  selectedOrgId: number | null;
  onOrgChange: (orgId: number) => void;
  crewDisplayName?: string;
  threadTitle?: string;
  messageCount?: number;
  hasThread?: boolean;
  onShare?: () => void;
  onExport?: () => void;
  onPreferences?: () => void;
}

const ChatTopBar = ({
  organizations,
  selectedOrgId,
  onOrgChange,
  crewDisplayName,
  threadTitle,
  messageCount = 0,
  hasThread = false,
  onShare,
  onExport,
  onPreferences,
}: ChatTopBarProps) => {
  const { openSidebar } = useSidebar();
  const border = useColorModeValue('gray.200', 'whiteAlpha.100');
  const bg = useColorModeValue('white', 'surface.900');
  const muted = useColorModeValue('gray.500', 'gray.400');

  return (
    <HStack
      px={3}
      py={2}
      borderBottomWidth="1px"
      borderColor={border}
      bg={bg}
      spacing={2}
      flexShrink={0}
    >
      <IconButton
        aria-label="Open sidebar"
        icon={<FiMenu />}
        size="sm"
        variant="ghost"
        onClick={openSidebar}
      />
      <Box flex="1" minW={0}>
        <Text fontSize="sm" fontWeight="600" noOfLines={1}>
          {threadTitle || 'New chat'}
        </Text>
        <HStack spacing={2} mt={0.5} flexWrap="wrap">
          <Badge variant="subtle" colorScheme="orange" fontSize="2xs">
            {crewDisplayName || APP_CONFIG.defaultCrewName}
          </Badge>
          {organizations && organizations.length > 0 && (
            <Select
              size="xs"
              w="auto"
              maxW="200px"
              variant="unstyled"
              value={selectedOrgId ?? ''}
              onChange={(e) => onOrgChange(parseInt(e.target.value, 10))}
              fontSize="xs"
              color={muted}
            >
              {organizations.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name}
                </option>
              ))}
            </Select>
          )}
          {hasThread && messageCount > 0 && (
            <Text fontSize="2xs" color={muted}>
              {messageCount} message{messageCount !== 1 ? 's' : ''}
            </Text>
          )}
        </HStack>
      </Box>
      {hasThread && (
        <Menu>
          <MenuButton
            as={IconButton}
            aria-label="Thread options"
            icon={<FiMoreVertical />}
            size="sm"
            variant="ghost"
          />
          <MenuList fontSize="sm">
            {onShare && (
              <MenuItem icon={<FiShare2 />} onClick={onShare}>
                Share link
              </MenuItem>
            )}
            {onExport && (
              <MenuItem icon={<FiDownload />} onClick={onExport}>
                Export
              </MenuItem>
            )}
            {onPreferences && (
              <MenuItem icon={<FiSettings />} onClick={onPreferences}>
                Thread preferences
              </MenuItem>
            )}
          </MenuList>
        </Menu>
      )}
    </HStack>
  );
};

export default ChatTopBar;
