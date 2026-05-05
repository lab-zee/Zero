import React, { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Button,
  VStack,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Text,
  useToast,
  Box,
  HStack,
  Progress,
  Alert,
  AlertIcon,
  AlertDescription,
  Select,
  FormHelperText,
} from '@chakra-ui/react';
import { organizationAPI } from '../services/api';

interface OrganizationWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  userId: number;
}

interface ScrapedData {
  name?: string;
  description?: string;
  industry?: string;
  org_type?: string;
  purpose?: string;
  goals_missions?: string;
  website_url?: string;
  social_media_links?: Record<string, string>;
  key_products_services?: string[];
  target_market?: string;
  leadership_info?: string;
}

const OrganizationWizard: React.FC<OrganizationWizardProps> = ({
  isOpen,
  onClose,
  onSuccess,
  userId,
}) => {
  const toast = useToast();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [scrapingError, setScrapingError] = useState<string | null>(null);

  // Form data
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [scrapedData, setScrapedData] = useState<ScrapedData>({});

  // Editable org data
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [industry, setIndustry] = useState('');
  const [orgType, setOrgType] = useState('');
  const [purpose, setPurpose] = useState('');
  const [goalsMissions, setGoalsMissions] = useState('');
  const [targetMarket, setTargetMarket] = useState('');
  const [leadershipInfo, setLeadershipInfo] = useState('');

  const resetForm = () => {
    setStep(1);
    setWebsiteUrl('');
    setScrapedData({});
    setName('');
    setDescription('');
    setIndustry('');
    setOrgType('');
    setPurpose('');
    setGoalsMissions('');
    setTargetMarket('');
    setLeadershipInfo('');
    setScrapingError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleScrapeWebsite = async () => {
    if (!websiteUrl.trim()) {
      toast({
        title: 'Website URL required',
        description: 'Please enter a website URL to scrape',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setIsLoading(true);
    setScrapingError(null);

    try {
      const result = await organizationAPI.scrapeWebsite(websiteUrl, userId);

      if (result.success && result.data) {
        // Populate form with scraped data
        setScrapedData(result.data);
        // Only set name if user didn't manually enter one
        if (!name.trim()) {
          setName(result.data.name || '');
        }
        setDescription(result.data.description || '');
        setIndustry(result.data.industry || '');
        setOrgType(result.data.org_type || '');
        setPurpose(result.data.purpose || '');
        setGoalsMissions(result.data.goals_missions || '');
        setTargetMarket(result.data.target_market || '');
        setLeadershipInfo(result.data.leadership_info || '');

        toast({
          title: 'Website scraped successfully',
          description: `Extracted information for ${result.data.name || 'organization'}`,
          status: 'success',
          duration: 3000,
        });

        setStep(3); // Move to review step
      } else {
        setScrapingError(result.error || 'Failed to scrape website');
        toast({
          title: 'Scraping failed',
          description: result.error || 'Could not extract information from website',
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error: any) {
      setScrapingError(error.message || 'An error occurred');
      toast({
        title: 'Error',
        description: 'Failed to scrape website',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateOrganization = async () => {
    if (!name.trim()) {
      toast({
        title: 'Organization name required',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setIsLoading(true);

    try {
      await organizationAPI.createOrganization(
        {
          name: name.trim(),
          description: description.trim() || undefined,
          metadata: {
            industry_name: industry || undefined,
            org_type: orgType || undefined,
            purpose: purpose || undefined,
            goals_missions: goalsMissions || undefined,
            website_url: websiteUrl || undefined,
            social_media_links: scrapedData.social_media_links || undefined,
            key_products_services: scrapedData.key_products_services || undefined,
            target_market: targetMarket || undefined,
            leadership_info: leadershipInfo || undefined,
          },
        },
        userId
      );

      toast({
        title: 'Organization created',
        description: `${name} has been created successfully`,
        status: 'success',
        duration: 3000,
      });

      handleClose();
      onSuccess();
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to create organization',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderStep1 = () => (
    <VStack spacing={4} align="stretch">
      <Text fontSize="md" color="gray.400">
        Start by entering your organization's website URL. We'll automatically extract company information to help you get started quickly.
      </Text>

      <FormControl isRequired>
        <FormLabel>Website URL</FormLabel>
        <Input
          placeholder="https://example.com"
          value={websiteUrl}
          onChange={(e) => setWebsiteUrl(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && websiteUrl.trim()) {
              setStep(2);
            }
          }}
        />
        <FormHelperText>We'll extract company information from this website</FormHelperText>
      </FormControl>

      <FormControl>
        <FormLabel>Organization Name (Optional)</FormLabel>
        <Input
          placeholder="Acme Corporation"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <FormHelperText>Provide the business name if known, or leave blank to extract from website</FormHelperText>
      </FormControl>

      <HStack spacing={3} pt={4}>
        <Button variant="outline" onClick={handleClose}>
          Cancel
        </Button>
        <Button
          colorScheme="blue"
          onClick={() => setStep(2)}
          isDisabled={!websiteUrl.trim()}
          flex={1}
        >
          Continue
        </Button>
      </HStack>

      <Box pt={2}>
        <Button
          variant="link"
          size="sm"
          onClick={() => {
            // Skip to manual entry
            setStep(3);
          }}
        >
          Or create manually without website scraping
        </Button>
      </Box>
    </VStack>
  );

  const renderStep2 = () => (
    <VStack spacing={4} align="stretch">
      <Text fontSize="md" color="gray.400">
        Click the button below to automatically extract company information from the website.
      </Text>

      <Box>
        <Text fontWeight="semibold" mb={2}>Website URL:</Text>
        <Text color="blue.600">{websiteUrl}</Text>
      </Box>

      {scrapingError && (
        <Alert status="error">
          <AlertIcon />
          <AlertDescription>{scrapingError}</AlertDescription>
        </Alert>
      )}

      <HStack spacing={3} pt={4}>
        <Button variant="outline" onClick={() => setStep(1)} isDisabled={isLoading}>
          Back
        </Button>
        <Button
          colorScheme="blue"
          onClick={handleScrapeWebsite}
          isLoading={isLoading}
          loadingText="Scraping website..."
          flex={1}
        >
          {scrapingError ? 'Retry Scraping' : 'Scrape Website'}
        </Button>
      </HStack>

      {scrapingError && (
        <Box pt={2}>
          <Button
            variant="link"
            size="sm"
            onClick={() => setStep(3)}
          >
            Continue with manual entry
          </Button>
        </Box>
      )}
    </VStack>
  );

  const renderStep3 = () => (
    <VStack spacing={4} align="stretch" maxH="60vh" overflowY="auto" pr={2}>
      <Text fontSize="md" color="gray.400">
        Review and edit the organization information below.
      </Text>

      <FormControl isRequired>
        <FormLabel>Organization Name</FormLabel>
        <Input
          placeholder="Acme Corporation"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </FormControl>

      <FormControl>
        <FormLabel>Description</FormLabel>
        <Textarea
          placeholder="Brief description of your organization"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />
      </FormControl>

      <HStack spacing={4}>
        <FormControl>
          <FormLabel>Industry</FormLabel>
          <Input
            placeholder="e.g., Technology, Healthcare"
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
          />
        </FormControl>

        <FormControl>
          <FormLabel>Organization Type</FormLabel>
          <Select
            placeholder="Select type"
            value={orgType}
            onChange={(e) => setOrgType(e.target.value)}
          >
            <option value="startup">Startup</option>
            <option value="enterprise">Enterprise</option>
            <option value="smb">Small/Medium Business</option>
            <option value="nonprofit">Nonprofit</option>
            <option value="government">Government</option>
            <option value="consulting">Consulting</option>
          </Select>
        </FormControl>
      </HStack>

      <FormControl>
        <FormLabel>Purpose</FormLabel>
        <Textarea
          placeholder="Core purpose or mission statement"
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
          rows={2}
        />
      </FormControl>

      <FormControl>
        <FormLabel>Goals & Missions</FormLabel>
        <Textarea
          placeholder="Key goals, objectives, or mission details"
          value={goalsMissions}
          onChange={(e) => setGoalsMissions(e.target.value)}
          rows={3}
        />
      </FormControl>

      <FormControl>
        <FormLabel>Target Market</FormLabel>
        <Input
          placeholder="e.g., B2B SaaS companies, Healthcare providers"
          value={targetMarket}
          onChange={(e) => setTargetMarket(e.target.value)}
        />
      </FormControl>

      <FormControl>
        <FormLabel>Leadership Information</FormLabel>
        <Textarea
          placeholder="CEO, founders, key executives"
          value={leadershipInfo}
          onChange={(e) => setLeadershipInfo(e.target.value)}
          rows={2}
        />
      </FormControl>

      <HStack spacing={3} pt={4} position="sticky" bottom={0} bg="surface.800" py={2}>
        <Button variant="outline" onClick={websiteUrl ? () => setStep(2) : () => setStep(1)} isDisabled={isLoading}>
          Back
        </Button>
        <Button
          colorScheme="blue"
          onClick={handleCreateOrganization}
          isLoading={isLoading}
          loadingText="Creating..."
          flex={1}
          isDisabled={!name.trim()}
        >
          Create Organization
        </Button>
      </HStack>
    </VStack>
  );

  const getStepTitle = () => {
    switch (step) {
      case 1:
        return 'Enter Website URL';
      case 2:
        return 'Scrape Website';
      case 3:
        return 'Review & Edit Information';
      default:
        return 'Create Organization';
    }
  };

  const getProgress = () => {
    switch (step) {
      case 1:
        return 33;
      case 2:
        return 66;
      case 3:
        return 100;
      default:
        return 0;
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl" closeOnOverlayClick={!isLoading}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          <VStack align="stretch" spacing={2}>
            <Text>Create New Organization</Text>
            <Box>
              <HStack justify="space-between" mb={2}>
                <Text fontSize="sm" fontWeight="normal" color="gray.400">
                  {getStepTitle()}
                </Text>
                <Text fontSize="sm" fontWeight="normal" color="gray.400">
                  Step {step} of 3
                </Text>
              </HStack>
              <Progress value={getProgress()} size="sm" colorScheme="blue" borderRadius="full" />
            </Box>
          </VStack>
        </ModalHeader>
        <ModalCloseButton isDisabled={isLoading} />
        <ModalBody pb={6}>
          {step === 1 && renderStep1()}
          {step === 2 && renderStep2()}
          {step === 3 && renderStep3()}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default OrganizationWizard;
