import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  SimpleGrid,
  Flex,
} from '@chakra-ui/react';
import {
  FiMessageSquare,
  FiCpu,
  FiTrendingUp,
  FiArrowRight,
  FiShield,
  FiZap,
  FiLayers,
} from 'react-icons/fi';
import { APP_CONFIG } from '../config';

const FeatureCard = ({ icon, title, description }: { icon: React.ReactElement; title: string; description: string }) => (
  <Box
    p={6}
    bg="surface.800"
    borderRadius="xl"
    borderWidth="1px"
    borderColor="whiteAlpha.100"
    transition="all 0.2s"
    _hover={{
      borderColor: 'whiteAlpha.200',
      transform: 'translateY(-2px)',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
    }}
  >
    <Box
      w="40px"
      h="40px"
      borderRadius="lg"
      bg="brand.500"
      display="flex"
      alignItems="center"
      justifyContent="center"
      color="white"
      mb={4}
      opacity={0.9}
    >
      {icon}
    </Box>
    <Text fontWeight="600" fontSize="sm" color="gray.100" mb={2}>
      {title}
    </Text>
    <Text fontSize="xs" color="gray.400" lineHeight="tall">
      {description}
    </Text>
  </Box>
);

const Home = () => {
  const navigate = useNavigate();

  return (
    <Box minH="100vh" bg="surface.950">
      {/* Nav */}
      <Flex
        px={8}
        py={4}
        align="center"
        justify="space-between"
        borderBottomWidth="1px"
        borderColor="whiteAlpha.50"
      >
        <Text fontSize="lg" fontWeight="700" color="brand.400" letterSpacing="-0.02em">
          {APP_CONFIG.name}
        </Text>
        <HStack spacing={3}>
          <Button
            variant="ghost"
            size="sm"
            color="gray.400"
            onClick={() => navigate('/login')}
            _hover={{ color: 'gray.100' }}
          >
            Sign In
          </Button>
          <Button
            size="sm"
            bg="brand.500"
            color="white"
            onClick={() => navigate('/register')}
            _hover={{ bg: 'brand.400' }}
          >
            Get Started
          </Button>
        </HStack>
      </Flex>

      {/* Hero */}
      <Container maxW="4xl" pt={{ base: 16, md: 24 }} pb={16} centerContent>
        <VStack spacing={6} textAlign="center" maxW="2xl">
          <Box
            px={3}
            py={1}
            bg="whiteAlpha.50"
            borderRadius="full"
            borderWidth="1px"
            borderColor="whiteAlpha.100"
          >
            <Text fontSize="xs" color="brand.400" fontWeight="500">
              AI-Powered Strategy Engine
            </Text>
          </Box>

          <Heading
            fontSize={{ base: '3xl', md: '5xl' }}
            fontWeight="700"
            color="gray.50"
            lineHeight="1.1"
            letterSpacing="-0.03em"
          >
            Strategy insights{' '}
            <Text as="span" color="brand.400">
              powered by AI agents
            </Text>
          </Heading>

          <Text fontSize={{ base: 'sm', md: 'md' }} color="gray.400" maxW="lg" lineHeight="tall">
            {APP_CONFIG.description}
          </Text>

          <HStack spacing={4} pt={4}>
            <Button
              size="lg"
              bg="brand.500"
              color="white"
              rightIcon={<FiArrowRight />}
              onClick={() => navigate('/register')}
              _hover={{ bg: 'brand.400', transform: 'translateY(-1px)', boxShadow: '0 4px 20px rgba(163, 201, 64, 0.3)' }}
              px={8}
            >
              Get Started
            </Button>
            <Button
              size="lg"
              variant="outline"
              borderColor="whiteAlpha.200"
              color="gray.300"
              onClick={() => navigate('/login')}
              _hover={{ bg: 'whiteAlpha.50', borderColor: 'whiteAlpha.300' }}
              px={8}
            >
              Sign In
            </Button>
          </HStack>
        </VStack>
      </Container>

      {/* Features */}
      <Container maxW="4xl" pb={24}>
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          <FeatureCard
            icon={<FiCpu size={18} />}
            title="Multi-Agent Orchestration"
            description="A Strategic Director coordinates specialist agents, each with unique skillsets for comprehensive analysis."
          />
          <FeatureCard
            icon={<FiLayers size={18} />}
            title="Flexible Output Modes"
            description="From executive summaries to 30-60-90 day plans and strategic roadmaps — choose the depth you need."
          />
          <FeatureCard
            icon={<FiTrendingUp size={18} />}
            title="Actionable Insights"
            description="Get executive-grade deliverables with data-backed analysis, citations, and clear recommendations."
          />
        </SimpleGrid>

        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mt={4}>
          <FeatureCard
            icon={<FiMessageSquare size={18} />}
            title="Conversational Interface"
            description="Interact naturally through a chat interface with real-time streaming responses and follow-up suggestions."
          />
          <FeatureCard
            icon={<FiShield size={18} />}
            title="Organization Management"
            description="Manage teams, knowledge bases, and configurations for targeted, contextual analysis."
          />
          <FeatureCard
            icon={<FiZap size={18} />}
            title="Real-Time Execution"
            description="Watch agents work in real-time with execution graphs and progress tracking."
          />
        </SimpleGrid>
      </Container>

      {/* Footer */}
      <Box borderTopWidth="1px" borderColor="whiteAlpha.50" py={6}>
        <Container maxW="4xl">
          <Text fontSize="xs" color="gray.400" textAlign="center">
            {APP_CONFIG.name} — {APP_CONFIG.tagline}
          </Text>
        </Container>
      </Box>
    </Box>
  );
};

export default Home;
