import { Box, HStack, Tooltip, Text } from '@chakra-ui/react';
import {
  FiFileText,
  FiFile,
  FiBookOpen,
  FiCalendar,
  FiMap,
} from 'react-icons/fi';
import { AnswerMode } from '../services/api';

const ICONS: Record<string, React.ElementType> = {
  summary: FiFileText,
  light: FiFile,
  extended: FiBookOpen,
  project_plan: FiCalendar,
  roadmap: FiMap,
};

export interface AnswerModeOption {
  id: AnswerMode;
  label: string;
  description: string;
}

interface AnswerModeSelectorProps {
  value: AnswerMode;
  onChange: (mode: AnswerMode) => void;
  modes: AnswerModeOption[];
}

const AnswerModeSelector = ({ value, onChange, modes }: AnswerModeSelectorProps) => {
  if (modes.length === 0) return null;

  return (
    <HStack spacing={1} px={4} py={2} overflowX="auto">
      <Text fontSize="2xs" color="gray.400" fontWeight="500" mr={1} textTransform="uppercase" letterSpacing="0.05em" flexShrink={0}>
        Output
      </Text>
      {modes.map((mode) => {
        const isActive = value === mode.id;
        const Icon = ICONS[mode.id] || FiFile;
        return (
          <Tooltip key={mode.id} label={mode.description} placement="top" hasArrow>
            <HStack
              as="button"
              type="button"
              spacing={1.5}
              px={2.5}
              py={1.5}
              borderRadius="md"
              bg={isActive ? 'whiteAlpha.150' : 'transparent'}
              borderWidth="1px"
              borderColor={isActive ? 'brand.400' : 'transparent'}
              color={isActive ? 'brand.400' : 'gray.500'}
              cursor="pointer"
              transition="all 0.15s"
              flexShrink={0}
              _hover={{
                bg: 'whiteAlpha.100',
                color: isActive ? 'brand.400' : 'gray.300',
              }}
              onClick={() => onChange(mode.id)}
            >
              <Box as={Icon} boxSize="13px" />
              <Text fontSize="xs" fontWeight={isActive ? '500' : '400'}>
                {mode.label}
              </Text>
            </HStack>
          </Tooltip>
        );
      })}
    </HStack>
  );
};

export default AnswerModeSelector;
