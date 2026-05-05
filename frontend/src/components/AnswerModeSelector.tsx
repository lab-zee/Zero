import { Box, HStack, Tooltip, Text } from '@chakra-ui/react';
import {
  FiFileText,
  FiFile,
  FiBookOpen,
  FiCalendar,
  FiMap,
} from 'react-icons/fi';
import { AnswerMode } from '../services/api';

interface AnswerModeSelectorProps {
  value: AnswerMode;
  onChange: (mode: AnswerMode) => void;
}

const MODES: {
  key: AnswerMode;
  icon: React.ElementType;
  label: string;
  tooltip: string;
}[] = [
  {
    key: 'summary',
    icon: FiFileText,
    label: 'Summary',
    tooltip: 'Concise 2-3 paragraph executive briefing',
  },
  {
    key: 'light',
    icon: FiFile,
    label: 'One-Pager',
    tooltip: 'One-page memo with balanced analysis',
  },
  {
    key: 'extended',
    icon: FiBookOpen,
    label: 'Report',
    tooltip: 'Comprehensive executive report',
  },
  {
    key: 'project_plan',
    icon: FiCalendar,
    label: '30-60-90',
    tooltip: '30-60-90 day strategic project plan',
  },
  {
    key: 'roadmap',
    icon: FiMap,
    label: 'Roadmap',
    tooltip: 'Strategic framework with actionable roadmap',
  },
];

const AnswerModeSelector = ({ value, onChange }: AnswerModeSelectorProps) => {
  return (
    <HStack spacing={1} px={4} py={2}>
      <Text fontSize="2xs" color="gray.400" fontWeight="500" mr={1} textTransform="uppercase" letterSpacing="0.05em">
        Output
      </Text>
      {MODES.map((mode) => {
        const isActive = value === mode.key;
        const Icon = mode.icon;
        return (
          <Tooltip key={mode.key} label={mode.tooltip} placement="top" hasArrow>
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
              _hover={{
                bg: 'whiteAlpha.100',
                color: isActive ? 'brand.400' : 'gray.300',
              }}
              onClick={() => onChange(mode.key)}
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
