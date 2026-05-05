import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Button,
  VStack,
  Box,
  FormLabel,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  HStack,
  Text,
  Divider,
  Wrap,
  WrapItem,
  Badge,
  Tooltip,
} from '@chakra-ui/react';
import { AgentInfo } from '../services/api';

interface PreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
  budgetFocus: number;
  responseLength: number;
  creativity: number;
  onBudgetFocusChange: (value: number) => void;
  onBudgetFocusChangeEnd: (value: number) => void;
  onResponseLengthChange: (value: number) => void;
  onResponseLengthChangeEnd: (value: number) => void;
  onCreativityChange: (value: number) => void;
  onCreativityChangeEnd: (value: number) => void;
  availableAgents?: AgentInfo[];
  selectedAgentIds?: string[] | null;
  onAgentSelectionChange?: (agentIds: string[] | null) => void;
}

const PreferencesModal = ({
  isOpen,
  onClose,
  budgetFocus,
  responseLength,
  creativity,
  onBudgetFocusChange,
  onBudgetFocusChangeEnd,
  onResponseLengthChange,
  onResponseLengthChangeEnd,
  onCreativityChange,
  onCreativityChangeEnd,
  availableAgents,
  selectedAgentIds,
  onAgentSelectionChange,
}: PreferencesModalProps) => {
  // Filter to only show selectable agents (not director/synthesizer which are always included)
  const selectableAgents = (availableAgents || []).filter(
    (a) => a.id !== 'director' && a.id !== 'synthesizer'
  );
  const allSelected = selectedAgentIds === null || selectedAgentIds === undefined;
  const selectedCount = allSelected ? selectableAgents.length : selectedAgentIds!.length;

  const handleAgentToggle = (agentId: string) => {
    if (!onAgentSelectionChange) return;

    if (allSelected) {
      // Switching from "all" to specific selection - select all except the toggled one
      const allIds = selectableAgents.map((a) => a.id);
      onAgentSelectionChange(allIds.filter((id) => id !== agentId));
    } else {
      const current = selectedAgentIds || [];
      if (current.includes(agentId)) {
        const newSelection = current.filter((id) => id !== agentId);
        // If removing the last one, keep at least one or revert to all
        onAgentSelectionChange(newSelection.length === 0 ? null : newSelection);
      } else {
        const newSelection = [...current, agentId];
        // If all are selected, switch back to null (= all)
        if (newSelection.length >= selectableAgents.length) {
          onAgentSelectionChange(null);
        } else {
          onAgentSelectionChange(newSelection);
        }
      }
    }
  };

  const handleSelectAll = () => {
    if (!onAgentSelectionChange) return;
    onAgentSelectionChange(null); // null = all agents
  };

  const handleDeselectAll = () => {
    if (!onAgentSelectionChange) return;
    onAgentSelectionChange([]); // empty = no agents (will use director only)
  };
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Thread Preferences</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4} align="stretch">
            <Box>
              <FormLabel fontSize="sm" fontWeight="semibold" mb={3}>
                Budget Focus
              </FormLabel>
              <VStack spacing={2}>
                <HStack justify="space-between" w="100%">
                  <Text fontSize="sm" color="gray.400">
                    Budget-Conscious
                  </Text>
                  <Text fontSize="sm" color="gray.400">
                    Outcome-Conscious
                  </Text>
                </HStack>
                <Slider
                  value={budgetFocus}
                  min={0}
                  max={1}
                  step={0.1}
                  onChange={onBudgetFocusChange}
                  onChangeEnd={onBudgetFocusChangeEnd}
                  size="lg"
                >
                  <SliderTrack>
                    <SliderFilledTrack bg="brand.500" />
                  </SliderTrack>
                  <SliderThumb />
                </Slider>
                <Text fontSize="sm" color="gray.400" textAlign="center">
                  {budgetFocus < 0.3
                    ? 'Very Budget-Conscious'
                    : budgetFocus < 0.7
                    ? 'Balanced'
                    : 'Very Outcome-Conscious'}
                </Text>
                <Text fontSize="xs" color="gray.400" textAlign="center" mt={2}>
                  Influences how the Strategic Director prioritizes cost efficiency vs. maximizing outcomes
                </Text>
              </VStack>
            </Box>

            <Divider />

            {/* Response Length */}
            <Box>
              <FormLabel fontSize="sm" fontWeight="semibold" mb={3}>
                Response Length
              </FormLabel>
              <VStack spacing={2}>
                <HStack justify="space-between" w="100%">
                  <Text fontSize="sm" color="gray.400">
                    Brief
                  </Text>
                  <Text fontSize="sm" color="gray.400">
                    Comprehensive
                  </Text>
                </HStack>
                <Slider
                  value={responseLength}
                  min={0}
                  max={1}
                  step={0.1}
                  onChange={onResponseLengthChange}
                  onChangeEnd={onResponseLengthChangeEnd}
                  size="lg"
                >
                  <SliderTrack>
                    <SliderFilledTrack bg="purple.500" />
                  </SliderTrack>
                  <SliderThumb />
                </Slider>
                <Text fontSize="sm" color="gray.400" textAlign="center">
                  {responseLength < 0.3
                    ? 'One-sentence answers'
                    : responseLength < 0.7
                    ? 'Moderate detail'
                    : 'Full analysis with visuals, charts, and action plans'}
                </Text>
                <Text fontSize="xs" color="gray.400" textAlign="center" mt={2}>
                  Controls response brevity. At maximum, includes text summaries, detailed analysis, action plans, visualizations, and charts
                </Text>
              </VStack>
            </Box>

            <Divider />

            {/* Creativity */}
            <Box>
              <FormLabel fontSize="sm" fontWeight="semibold" mb={3}>
                Creativity
              </FormLabel>
              <VStack spacing={2}>
                <HStack justify="space-between" w="100%">
                  <Text fontSize="sm" color="gray.400">
                    Off-the-Shelf
                  </Text>
                  <Text fontSize="sm" color="gray.400">
                    Innovative
                  </Text>
                </HStack>
                <Slider
                  value={creativity}
                  min={0}
                  max={1}
                  step={0.1}
                  onChange={onCreativityChange}
                  onChangeEnd={onCreativityChangeEnd}
                  size="lg"
                >
                  <SliderTrack>
                    <SliderFilledTrack bg="orange.500" />
                  </SliderTrack>
                  <SliderThumb />
                </Slider>
                <Text fontSize="sm" color="gray.400" textAlign="center">
                  {creativity < 0.3
                    ? 'Standard approaches'
                    : creativity < 0.7
                    ? 'Balanced'
                    : 'Creative and innovative solutions'}
                </Text>
                <Text fontSize="xs" color="gray.400" textAlign="center" mt={2}>
                  Influences how creative vs. conventional the Strategic Director and Synthesizer are in their recommendations
                </Text>
              </VStack>
            </Box>

            {selectableAgents.length > 0 && onAgentSelectionChange && (
              <>
                <Divider />

                <Box>
                  <HStack justify="space-between" mb={2}>
                    <FormLabel fontSize="sm" fontWeight="semibold" mb={0}>
                      Active Agents ({selectedCount} of {selectableAgents.length})
                    </FormLabel>
                    <HStack spacing={2}>
                      <Button size="xs" variant="ghost" onClick={handleSelectAll}>
                        All
                      </Button>
                      <Button size="xs" variant="ghost" onClick={handleDeselectAll}>
                        None
                      </Button>
                    </HStack>
                  </HStack>
                  <Text fontSize="xs" color="gray.400" mb={3}>
                    Choose which specialist agents are available for this thread. The Director and Synthesizer are always active.
                  </Text>
                  <Wrap spacing={2}>
                    {selectableAgents.map((agent) => {
                      const isSelected = allSelected || (selectedAgentIds || []).includes(agent.id);
                      return (
                        <WrapItem key={agent.id}>
                          <Tooltip
                            label={agent.role || agent.description}
                            placement="top"
                            hasArrow
                          >
                            <Badge
                              px={3}
                              py={1}
                              borderRadius="full"
                              cursor="pointer"
                              variant={isSelected ? 'solid' : 'outline'}
                              colorScheme={isSelected ? (agent.is_custom ? 'purple' : 'green') : 'gray'}
                              onClick={() => handleAgentToggle(agent.id)}
                              _hover={{ opacity: 0.8 }}
                              fontSize="xs"
                            >
                              {agent.name}
                              {agent.is_custom && ' *'}
                            </Badge>
                          </Tooltip>
                        </WrapItem>
                      );
                    })}
                  </Wrap>
                </Box>
              </>
            )}
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button colorScheme="brand" onClick={onClose}>
            Done
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default PreferencesModal;





