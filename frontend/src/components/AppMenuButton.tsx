import { IconButton, useColorModeValue } from '@chakra-ui/react';
import { FiMenu } from 'react-icons/fi';
import { useLocation } from 'react-router-dom';
import { useSidebar } from '../contexts/SidebarContext';

const AppMenuButton = () => {
  const location = useLocation();
  const { isOpen, openSidebar } = useSidebar();
  const color = useColorModeValue('gray.600', 'gray.300');

  if (isOpen || location.pathname.startsWith('/chat')) return null;

  return (
    <IconButton
      aria-label="Open menu"
      icon={<FiMenu />}
      size="sm"
      variant="ghost"
      position="fixed"
      top={3}
      left={3}
      zIndex={900}
      color={color}
      onClick={openSidebar}
    />
  );
};

export default AppMenuButton;
