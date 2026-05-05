import { Button, Menu, MenuButton, MenuList, MenuItem, Badge, HStack, Text } from '@chakra-ui/react';
import { RepeatIcon, ChevronDownIcon } from '@chakra-ui/icons';
import { AnswerMode } from '../services/api';

interface ReAskButtonProps {
  queryId: number;
  currentMode: AnswerMode | null | undefined;
  onReAsk: (queryId: number, newMode: AnswerMode) => void;
  isDisabled?: boolean;
}

const MODE_LABELS: Record<AnswerMode, string> = {
  summary: 'Exec Summary',
  light: 'One-Pager',
  extended: 'Exec Report',
  project_plan: '30-60-90 Plan',
  roadmap: 'Roadmap',
};

const MODE_DESCRIPTIONS: Record<AnswerMode, string> = {
  summary: 'Quick 2-3 paragraph executive briefing',
  light: 'One-page memo with balanced analysis',
  extended: 'Comprehensive executive report',
  project_plan: '30-60-90 day strategic project plan',
  roadmap: 'Strategic framework with actionable roadmap',
};

export const ReAskButton = ({ queryId, currentMode, onReAsk, isDisabled }: ReAskButtonProps) => {
  const modes: AnswerMode[] = ['summary', 'light', 'extended', 'project_plan', 'roadmap'];

  // Filter out the current mode
  const availableModes = modes.filter(mode => mode !== currentMode);

  return (
    <Menu>
      <MenuButton
        as={Button}
        size="sm"
        leftIcon={<RepeatIcon />}
        rightIcon={<ChevronDownIcon />}
        variant="outline"
        colorScheme="blue"
        isDisabled={isDisabled}
      >
        Re-ask
      </MenuButton>
      <MenuList>
        <MenuItem isDisabled py={1} px={3} fontSize="xs" color="gray.400" fontWeight="bold">
          Re-generate answer in different mode:
        </MenuItem>
        {availableModes.map((mode) => (
          <MenuItem
            key={mode}
            onClick={() => onReAsk(queryId, mode)}
            py={2}
            px={3}
          >
            <HStack spacing={2} width="100%">
              <Badge
                colorScheme={
                  mode === 'summary' ? 'green' :
                  mode === 'light' ? 'blue' :
                  mode === 'extended' ? 'purple' :
                  mode === 'project_plan' ? 'orange' :
                  mode === 'roadmap' ? 'teal' :
                  'gray'
                }
                fontSize="xs"
              >
                {MODE_LABELS[mode]}
              </Badge>
              <Text fontSize="sm" color="gray.400">
                {MODE_DESCRIPTIONS[mode]}
              </Text>
            </HStack>
          </MenuItem>
        ))}
      </MenuList>
    </Menu>
  );
};

export default ReAskButton;
