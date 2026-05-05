import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Button,
  Container,
  Heading,
  HStack,
  Text,
  Badge,
  useDisclosure,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  IconButton,
} from '@chakra-ui/react';
import { FiTrash2 } from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { organizationAPI, OrganizationWithStats } from '../services/api';
import { useCustomToast } from '../hooks/useToast';
import { NoOrganizationsState } from '../components/EmptyState';
import LoadingSpinner from '../components/LoadingSpinner';
import OrganizationWizard from '../components/OrganizationWizard';

const Organizations = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const toast = useCustomToast();
  const { isOpen: isWizardOpen, onOpen: onWizardOpen, onClose: onWizardClose } = useDisclosure();

  const { data: organizations, isLoading, error } = useQuery({
    queryKey: ['organizations', user?.id],
    queryFn: () => organizationAPI.getMyOrganizationsWithStats(user!.id),
    enabled: !!user,
  });

  const deleteMutation = useMutation({
    mutationFn: ({ orgId, userId }: { orgId: number; userId: number }) =>
      organizationAPI.delete(orgId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations', user?.id] });
      queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', user?.id] });
      toast.success('Organization deleted successfully');
    },
    onError: (error) => {
      toast.error(error);
    },
  });

  if (!user) {
    navigate('/login');
    return null;
  }

  if (isLoading) {
    return <LoadingSpinner fullScreen message="Loading organizations..." />;
  }

  if (error) {
    return (
      <Container maxW="4xl" py={8}>
        <Text color="red.500">
          Error loading organizations. Please try refreshing the page.
        </Text>
      </Container>
    );
  }

  const isOwner = (org: OrganizationWithStats) => org.owner_id === user.id;
  const canDelete = (org: OrganizationWithStats) => isOwner(org) || user.is_admin;

  return (
    <Container maxW="6xl" py={8}>
      <HStack justify="space-between" mb={6}>
        <Heading>{user.is_admin ? 'All Organizations' : 'My Organizations'}</Heading>
        <Button colorScheme="blue" onClick={onWizardOpen}>
          Create Organization
        </Button>
      </HStack>

      {organizations && organizations.length === 0 ? (
        <NoOrganizationsState onCreate={onWizardOpen} />
      ) : (
        <Box overflowX="auto">
          <Table variant="simple">
            <Thead>
              <Tr>
                <Th>Name</Th>
                <Th>Role</Th>
                <Th isNumeric>Threads</Th>
                <Th isNumeric>Messages</Th>
                <Th isNumeric>Contributors</Th>
                <Th isNumeric>Files</Th>
                <Th>Created</Th>
                <Th></Th>
              </Tr>
            </Thead>
            <Tbody>
              {organizations?.map((org) => (
                <Tr
                  key={org.id}
                  cursor="pointer"
                  _hover={{ bg: 'whiteAlpha.50' }}
                  onClick={() => navigate(`/organizations/${org.id}`)}
                >
                  <Td>
                    <Box>
                      <Text fontWeight="semibold">{org.name}</Text>
                      <Text fontSize="xs" color="gray.400" noOfLines={1}>
                        {org.description || 'No description'}
                      </Text>
                    </Box>
                  </Td>
                  <Td>
                    {isOwner(org) ? (
                      <Badge colorScheme="green">Owner</Badge>
                    ) : user.is_admin ? (
                      <Badge colorScheme="purple">Admin</Badge>
                    ) : (
                      <Badge colorScheme="blue">Member</Badge>
                    )}
                  </Td>
                  <Td isNumeric>{org.thread_count}</Td>
                  <Td isNumeric>{org.total_message_count}</Td>
                  <Td isNumeric>{org.unique_user_count}</Td>
                  <Td isNumeric>{org.file_count}</Td>
                  <Td>
                    <Text fontSize="sm" color="gray.400">
                      {new Date(org.created_at).toLocaleDateString()}
                    </Text>
                  </Td>
                  <Td>
                    {canDelete(org) && (
                      <IconButton
                        aria-label="Delete organization"
                        icon={<FiTrash2 />}
                        size="sm"
                        variant="ghost"
                        colorScheme="red"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm('Are you sure you want to delete this organization?')) {
                            deleteMutation.mutate({ orgId: org.id, userId: user.id });
                          }
                        }}
                      />
                    )}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}

      <OrganizationWizard
        isOpen={isWizardOpen}
        onClose={onWizardClose}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['organizations', user.id] });
          queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', user.id] });
        }}
        userId={user.id}
      />
    </Container>
  );
};

export default Organizations;
