import { Text, Tooltip, useColorModeValue } from '@chakra-ui/react';

interface InlineCitationProps {
  number: number;
  onClick: (number: number) => void;
  isHighlighted?: boolean;
}

const InlineCitation: React.FC<InlineCitationProps> = ({
  number,
  onClick,
  isHighlighted = false,
}) => {
  const citationColor = useColorModeValue('blue.600', 'blue.300');
  const highlightBg = useColorModeValue('yellow.100', 'yellow.900');

  return (
    <Tooltip label={`View reference ${number}`} hasArrow placement="top">
      <Text
        as="sup"
        fontSize="xs"
        fontWeight="semibold"
        color={citationColor}
        cursor="pointer"
        onClick={() => onClick(number)}
        _hover={{ textDecoration: 'underline' }}
        bg={isHighlighted ? highlightBg : 'transparent'}
        px={isHighlighted ? 1 : 0}
        borderRadius="sm"
        transition="all 0.2s"
      >
        [{number}]
      </Text>
    </Tooltip>
  );
};

export default InlineCitation;
