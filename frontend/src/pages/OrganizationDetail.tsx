import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Button,
  Container,
  Heading,
  VStack,
  HStack,
  Text,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  useToast,
  Spinner,
  Center,
  Switch,
  FormControl,
  FormLabel,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  Input,
  Textarea,
  Select,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
} from '@chakra-ui/react';
import { useAuth } from '../contexts/AuthContext';
import { organizationAPI, OrganizationMetadata, fileAPI, FileInfo } from '../services/api';

const OrganizationDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isOpen: isEditOpen, onOpen: onEditOpen, onClose: onEditClose } = useDisclosure();
  const { isOpen: isUploadOpen, onOpen: onUploadOpen, onClose: onUploadClose } = useDisclosure();
  const [newMemberIdentifier, setNewMemberIdentifier] = useState('');
  const [memberIdentifierType, setMemberIdentifierType] = useState<'email' | 'userid'>('email');
  const [newMemberCanRead, setNewMemberCanRead] = useState(true);
  const [newMemberCanWrite, setNewMemberCanWrite] = useState(false);
  
  // Edit form state
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editMetadata, setEditMetadata] = useState<OrganizationMetadata>({});
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isScraping, setIsScraping] = useState(false);

  const orgId = parseInt(id || '0');

  const { data: organization, isLoading, error } = useQuery({
    queryKey: ['organization', orgId, user?.id],
    queryFn: () => organizationAPI.getById(orgId, user!.id),
    enabled: !!user && !!id,
  });

  const { data: files, isLoading: filesLoading } = useQuery({
    queryKey: ['organizationFiles', orgId, user?.id],
    queryFn: () => fileAPI.getOrganizationFiles(orgId, user!.id),
    enabled: !!user && !!id && !!organization,
  });

  // Populate edit form when organization data loads
  useEffect(() => {
    if (organization) {
      setEditName(organization.name);
      setEditDescription(organization.description || '');
      setEditMetadata(organization.metadata || {});
    }
  }, [organization]);

  const updateMemberMutation = useMutation({
    mutationFn: ({ memberUserId, update }: { memberUserId: number; update: { can_read?: boolean; can_write?: boolean } }) =>
      organizationAPI.updateMember(orgId, memberUserId, update, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization', orgId, user?.id] });
      toast({
        title: 'Member updated',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to update member',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: (memberUserId: number) =>
      organizationAPI.removeMember(orgId, memberUserId, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization', orgId, user?.id] });
      toast({
        title: 'Member removed',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to remove member',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const addMemberMutation = useMutation({
    mutationFn: (data: { user_id?: number; email?: string; can_read: boolean; can_write: boolean }) =>
      organizationAPI.addMember(orgId, data, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization', orgId, user?.id] });
      toast({
        title: 'Member added',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onClose();
      setNewMemberIdentifier('');
      setMemberIdentifierType('email');
      setNewMemberCanRead(true);
      setNewMemberCanWrite(false);
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to add member',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const updateOrgMutation = useMutation({
    mutationFn: (data: { name?: string; description?: string; metadata?: OrganizationMetadata }) =>
      organizationAPI.update(orgId, data, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization', orgId, user?.id] });
      queryClient.invalidateQueries({ queryKey: ['organizations', user?.id] });
      queryClient.invalidateQueries({ queryKey: ['organizationsWithStats', user?.id] });
      toast({
        title: 'Organization updated',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onEditClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to update organization',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const uploadFileMutation = useMutation({
    mutationFn: (file: File) => fileAPI.uploadFile(file, orgId, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizationFiles', orgId, user?.id] });
      toast({
        title: 'File uploaded',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onUploadClose();
      setUploadFile(null);
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to upload file',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const deleteFileMutation = useMutation({
    mutationFn: (fileId: number) => fileAPI.deleteFile(fileId, user!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizationFiles', orgId, user?.id] });
      toast({
        title: 'File deleted',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete file',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const downloadFileMutation = useMutation({
    mutationFn: async (fileId: number) => {
      const blob = await fileAPI.downloadFile(fileId, user!.id);
      const file = files?.find(f => f.id === fileId);
      if (file) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = file.original_filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to download file',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const handleScrapeForEdit = async () => {
    const url = editMetadata.website_url?.trim();
    if (!url) {
      toast({
        title: 'Website URL required',
        description: 'Enter a website URL above, then click Scrape',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setIsScraping(true);
    try {
      const result = await organizationAPI.scrapeWebsite(url, user!.id);
      if (result.success && result.data) {
        setEditMetadata((prev) => ({
          ...prev,
          industry_name: result.data.industry || prev.industry_name,
          org_type: result.data.org_type || prev.org_type,
          purpose: result.data.purpose || prev.purpose,
          goals_missions: result.data.goals_missions || prev.goals_missions,
          target_market: result.data.target_market || prev.target_market,
          leadership_info: result.data.leadership_info || prev.leadership_info,
          key_products_services: result.data.key_products_services || prev.key_products_services,
          social_media_links: result.data.social_media_links || prev.social_media_links,
        }));
        if (result.data.name && !editName.trim()) {
          setEditName(result.data.name);
        }
        if (result.data.description) {
          setEditDescription(result.data.description);
        }
        toast({
          title: 'Website scraped successfully',
          description: `Extracted information for ${result.data.name || 'organization'}. Review the fields below.`,
          status: 'success',
          duration: 4000,
        });
      } else {
        toast({
          title: 'Scraping failed',
          description: result.error || 'Could not extract information from website',
          status: 'error',
          duration: 5000,
        });
      }
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to scrape website',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsScraping(false);
    }
  };

  const handleSaveEdit = () => {
    updateOrgMutation.mutate({
      name: editName,
      description: editDescription,
      metadata: editMetadata,
    });
  };

  const handleAddMember = () => {
    if (!newMemberIdentifier.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Please enter an email or user ID',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    const memberData: any = {
      can_read: newMemberCanRead,
      can_write: newMemberCanWrite,
    };

    if (memberIdentifierType === 'email') {
      memberData.email = newMemberIdentifier.trim();
    } else {
      const userId = parseInt(newMemberIdentifier);
      if (isNaN(userId)) {
        toast({
          title: 'Validation Error',
          description: 'Please enter a valid user ID',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
        return;
      }
      memberData.user_id = userId;
    }

    addMemberMutation.mutate(memberData);
  };

  const handleUploadFile = () => {
    if (!uploadFile) {
      toast({
        title: 'Validation Error',
        description: 'Please select a file',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    uploadFileMutation.mutate(uploadFile);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const canDeleteFile = (file: FileInfo): boolean => {
    if (!organization) return false;
    // Owner can delete any file
    if (organization.owner_id === user?.id) return true;
    // File uploader can delete their own files
    if (file.user_id === user?.id) return true;
    // Members with write access can delete files
    const member = organization.members.find(m => m.user_id === user?.id);
    return member?.can_write || false;
  };

  if (!user) {
    navigate('/login');
    return null;
  }

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  if (error || !organization) {
    return (
      <Container maxW="4xl" py={8}>
        <Text color="red.500">Error loading organization</Text>
        <Button mt={4} onClick={() => navigate('/organizations')}>
          Back to Organizations
        </Button>
      </Container>
    );
  }

  const isOwner = organization.owner_id === user.id;
  const isAdminOrOwner = isOwner || user.is_admin;

  return (
    <Container maxW="6xl" py={8}>
      <HStack justify="space-between" mb={6}>
        <VStack align="start" spacing={1}>
          <HStack>
            <Heading>{organization.name}</Heading>
            {isOwner && <Badge colorScheme="green">Owner</Badge>}
          </HStack>
          <Text color="gray.400">{organization.description || 'No description'}</Text>
        </VStack>
        <HStack>
          <Button
            colorScheme="teal"
            onClick={() => navigate(`/chat?org=${organization.id}`)}
          >
            Start a new thread
          </Button>
          {(isAdminOrOwner || organization.members.some(m => m.user_id === user.id && m.can_write)) && (
            <Button colorScheme="blue" onClick={onEditOpen}>
              Edit Organization
            </Button>
          )}
        </HStack>
      </HStack>

      <Box mb={8}>
        <Text fontSize="sm" color="gray.400">
          Owner: {organization.owner.username} ({organization.owner.email})
        </Text>
        <Text fontSize="sm" color="gray.400">
          Created: {new Date(organization.created_at).toLocaleDateString()}
        </Text>
      </Box>

      <Box>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Members</Heading>
          {isAdminOrOwner && (
            <Button colorScheme="blue" size="sm" onClick={onOpen}>
              Add Member
            </Button>
          )}
        </HStack>

        <Box borderWidth={1} borderRadius="lg" overflow="hidden">
          <Table variant="simple">
            <Thead>
              <Tr>
                <Th>User</Th>
                <Th>Email</Th>
                <Th>Read Access</Th>
                <Th>Write Access</Th>
                {isAdminOrOwner && <Th>Actions</Th>}
              </Tr>
            </Thead>
            <Tbody>
              {organization.members.map((member) => (
                <Tr key={member.id}>
                  <Td>{member.user.username}</Td>
                  <Td>{member.user.email}</Td>
                  <Td>
                    {isAdminOrOwner ? (
                      <Switch
                        isChecked={member.can_read}
                        onChange={(e) => {
                          updateMemberMutation.mutate({
                            memberUserId: member.user_id,
                            update: { can_read: e.target.checked },
                          });
                        }}
                      />
                    ) : (
                      <Badge colorScheme={member.can_read ? 'green' : 'red'}>
                        {member.can_read ? 'Yes' : 'No'}
                      </Badge>
                    )}
                  </Td>
                  <Td>
                    {isAdminOrOwner ? (
                      <Switch
                        isChecked={member.can_write}
                        onChange={(e) => {
                          updateMemberMutation.mutate({
                            memberUserId: member.user_id,
                            update: { can_write: e.target.checked },
                          });
                        }}
                      />
                    ) : (
                      <Badge colorScheme={member.can_write ? 'green' : 'red'}>
                        {member.can_write ? 'Yes' : 'No'}
                      </Badge>
                    )}
                  </Td>
                  {isAdminOrOwner && (
                    <Td>
                      <Button
                        size="sm"
                        colorScheme="red"
                        onClick={() => {
                          if (window.confirm(`Remove ${member.user.username} from this organization?`)) {
                            removeMemberMutation.mutate(member.user_id);
                          }
                        }}
                      >
                        Remove
                      </Button>
                    </Td>
                  )}
                </Tr>
              ))}
              {organization.members.length === 0 && (
                <Tr>
                  <Td colSpan={isAdminOrOwner ? 5 : 4} textAlign="center" color="gray.400">
                    No members yet
                  </Td>
                </Tr>
              )}
            </Tbody>
          </Table>
        </Box>
      </Box>

      {/* Files Section */}
      <Box mt={8}>
        <HStack justify="space-between" mb={4}>
          <Heading size="md">Files</Heading>
          {(isAdminOrOwner || organization.members.some(m => m.user_id === user.id && m.can_write)) && (
            <Button colorScheme="blue" size="sm" onClick={onUploadOpen}>
              Upload File
            </Button>
          )}
        </HStack>

        {filesLoading ? (
          <Center py={8}>
            <Spinner />
          </Center>
        ) : files && files.length > 0 ? (
          <Box borderWidth={1} borderRadius="lg" overflow="hidden">
            <Table variant="simple">
              <Thead>
                <Tr>
                  <Th>Filename</Th>
                  <Th>Type</Th>
                  <Th>Size</Th>
                  <Th>Uploaded</Th>
                  <Th>Actions</Th>
                </Tr>
              </Thead>
              <Tbody>
                {files.map((file) => (
                  <Tr key={file.id}>
                    <Td>{file.original_filename}</Td>
                    <Td>
                      <Badge colorScheme="gray">
                        {file.content_type || 'Unknown'}
                      </Badge>
                    </Td>
                    <Td>{formatFileSize(file.file_size)}</Td>
                    <Td>{new Date(file.created_at).toLocaleDateString()}</Td>
                    <Td>
                      <HStack spacing={2}>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => downloadFileMutation.mutate(file.id)}
                          isLoading={downloadFileMutation.isPending}
                        >
                          Download
                        </Button>
                        {canDeleteFile(file) && (
                          <Button
                            size="sm"
                            colorScheme="red"
                            variant="outline"
                            onClick={() => {
                              if (window.confirm(`Delete ${file.original_filename}?`)) {
                                deleteFileMutation.mutate(file.id);
                              }
                            }}
                            isLoading={deleteFileMutation.isPending}
                          >
                            Delete
                          </Button>
                        )}
                      </HStack>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </Box>
        ) : (
          <Box borderWidth={1} borderRadius="lg" p={8} textAlign="center">
            <Text color="gray.400">No files uploaded yet</Text>
          </Box>
        )}
      </Box>

      {/* Upload File Modal */}
      <Modal isOpen={isUploadOpen} onClose={onUploadClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Upload File</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl>
                <FormLabel>Select File</FormLabel>
                <Input
                  type="file"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setUploadFile(file);
                    }
                  }}
                />
                {uploadFile && (
                  <Text fontSize="sm" color="gray.400" mt={2}>
                    Selected: {uploadFile.name} ({formatFileSize(uploadFile.size)})
                  </Text>
                )}
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onUploadClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleUploadFile}
              isLoading={uploadFileMutation.isPending}
              isDisabled={!uploadFile}
            >
              Upload
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Add Member Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Add Member</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl>
                <FormLabel>Add by</FormLabel>
                <HStack>
                  <Button
                    size="sm"
                    colorScheme={memberIdentifierType === 'email' ? 'blue' : 'gray'}
                    onClick={() => setMemberIdentifierType('email')}
                  >
                    Email
                  </Button>
                  <Button
                    size="sm"
                    colorScheme={memberIdentifierType === 'userid' ? 'blue' : 'gray'}
                    onClick={() => setMemberIdentifierType('userid')}
                  >
                    User ID
                  </Button>
                </HStack>
              </FormControl>
              <FormControl>
                <FormLabel>{memberIdentifierType === 'email' ? 'Email Address' : 'User ID'}</FormLabel>
                <Input
                  type={memberIdentifierType === 'email' ? 'email' : 'number'}
                  value={newMemberIdentifier}
                  onChange={(e) => setNewMemberIdentifier(e.target.value)}
                  placeholder={memberIdentifierType === 'email' ? 'user@example.com' : 'Enter user ID'}
                />
                <Text fontSize="sm" color="gray.400" mt={1}>
                  {memberIdentifierType === 'email' 
                    ? 'Enter the email address of the user to add'
                    : 'Enter the ID of the user to add'}
                </Text>
              </FormControl>
              <FormControl>
                <FormLabel>Permissions</FormLabel>
                <VStack align="start" spacing={2}>
                  <HStack>
                    <Switch
                      isChecked={newMemberCanRead}
                      onChange={(e) => setNewMemberCanRead(e.target.checked)}
                    />
                    <Text>Read Access</Text>
                  </HStack>
                  <HStack>
                    <Switch
                      isChecked={newMemberCanWrite}
                      onChange={(e) => setNewMemberCanWrite(e.target.checked)}
                    />
                    <Text>Write Access</Text>
                  </HStack>
                </VStack>
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleAddMember}
              isLoading={addMemberMutation.isPending}
            >
              Add Member
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Edit Organization Modal */}
      <Modal isOpen={isEditOpen} onClose={onEditClose} size="xl">
        <ModalOverlay />
        <ModalContent maxH="90vh" overflowY="auto">
          <ModalHeader>Edit Organization</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <FormControl>
                <FormLabel>Organization Name</FormLabel>
                <Input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="Organization name"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Description</FormLabel>
                <Textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  placeholder="Brief description of the organization"
                  rows={3}
                />
              </FormControl>

              <Box>
                <Text fontWeight="bold" mb={3}>Organization Details</Text>
                <Accordion allowMultiple defaultIndex={[0]}>
                  <AccordionItem>
                    <AccordionButton>
                      <Box flex="1" textAlign="left">
                        <Text fontWeight="semibold">Basic Information</Text>
                      </Box>
                      <AccordionIcon />
                    </AccordionButton>
                    <AccordionPanel pb={4}>
                      <VStack spacing={4}>
                        <FormControl>
                          <FormLabel>Industry Name</FormLabel>
                          <Input
                            value={editMetadata.industry_name || ''}
                            onChange={(e) => setEditMetadata({ ...editMetadata, industry_name: e.target.value })}
                            placeholder="e.g., Technology, Healthcare, Education"
                          />
                        </FormControl>
                        <FormControl>
                          <FormLabel>Organization Type</FormLabel>
                          <Select
                            value={editMetadata.org_type || ''}
                            onChange={(e) => setEditMetadata({ ...editMetadata, org_type: e.target.value })}
                            placeholder="Select organization type"
                          >
                            <option value="startup">Startup</option>
                            <option value="enterprise">Enterprise</option>
                            <option value="smb">Small/Medium Business</option>
                            <option value="nonprofit">Nonprofit</option>
                            <option value="government">Government</option>
                            <option value="consulting">Consulting</option>
                          </Select>
                        </FormControl>
                        <FormControl>
                          <FormLabel>Website URL</FormLabel>
                          <HStack>
                            <Input
                              value={editMetadata.website_url || ''}
                              onChange={(e) => setEditMetadata({ ...editMetadata, website_url: e.target.value })}
                              placeholder="https://example.com"
                            />
                            <Button
                              colorScheme="blue"
                              size="md"
                              onClick={handleScrapeForEdit}
                              isLoading={isScraping}
                              loadingText="Scraping"
                              isDisabled={!editMetadata.website_url?.trim()}
                              flexShrink={0}
                            >
                              Scrape
                            </Button>
                          </HStack>
                          <Text fontSize="xs" color="gray.400" mt={1}>
                            Scrape will auto-fill organization details from the website
                          </Text>
                        </FormControl>
                        <FormControl>
                          <FormLabel>Number of Members</FormLabel>
                          <Text fontSize="sm" color="gray.400">
                            {organization?.members?.length || 0} member{(organization?.members?.length || 0) !== 1 ? 's' : ''}
                          </Text>
                          <Text fontSize="xs" color="gray.400" mt={1}>
                            (This is automatically calculated from the members list)
                          </Text>
                        </FormControl>
                      </VStack>
                    </AccordionPanel>
                  </AccordionItem>

                  <AccordionItem>
                    <AccordionButton>
                      <Box flex="1" textAlign="left">
                        <Text fontWeight="semibold">Purpose</Text>
                      </Box>
                      <AccordionIcon />
                    </AccordionButton>
                    <AccordionPanel pb={4}>
                      <FormControl>
                        <Textarea
                          value={editMetadata.purpose || ''}
                          onChange={(e) => setEditMetadata({ ...editMetadata, purpose: e.target.value })}
                          placeholder="Describe the purpose of this organization..."
                          rows={5}
                        />
                      </FormControl>
                    </AccordionPanel>
                  </AccordionItem>

                  <AccordionItem>
                    <AccordionButton>
                      <Box flex="1" textAlign="left">
                        <Text fontWeight="semibold">Goals & Missions</Text>
                      </Box>
                      <AccordionIcon />
                    </AccordionButton>
                    <AccordionPanel pb={4}>
                      <FormControl>
                        <Textarea
                          value={editMetadata.goals_missions || ''}
                          onChange={(e) => setEditMetadata({ ...editMetadata, goals_missions: e.target.value })}
                          placeholder="Describe the goals and missions of this organization..."
                          rows={5}
                        />
                      </FormControl>
                    </AccordionPanel>
                  </AccordionItem>

                  <AccordionItem>
                    <AccordionButton>
                      <Box flex="1" textAlign="left">
                        <Text fontWeight="semibold">Current Limitations</Text>
                      </Box>
                      <AccordionIcon />
                    </AccordionButton>
                    <AccordionPanel pb={4}>
                      <FormControl>
                        <Textarea
                          value={editMetadata.current_limitations || ''}
                          onChange={(e) => setEditMetadata({ ...editMetadata, current_limitations: e.target.value })}
                          placeholder="Describe current perceived limitations..."
                          rows={5}
                        />
                      </FormControl>
                    </AccordionPanel>
                  </AccordionItem>

                  <AccordionItem>
                    <AccordionButton>
                      <Box flex="1" textAlign="left">
                        <Text fontWeight="semibold">Resources Available</Text>
                      </Box>
                      <AccordionIcon />
                    </AccordionButton>
                    <AccordionPanel pb={4}>
                      <FormControl>
                        <Textarea
                          value={editMetadata.resources_available || ''}
                          onChange={(e) => setEditMetadata({ ...editMetadata, resources_available: e.target.value })}
                          placeholder="Describe current and future resources available..."
                          rows={5}
                        />
                      </FormControl>
                    </AccordionPanel>
                  </AccordionItem>

                  <AccordionItem>
                    <AccordionButton>
                      <Box flex="1" textAlign="left">
                        <Text fontWeight="semibold">Target Market</Text>
                      </Box>
                      <AccordionIcon />
                    </AccordionButton>
                    <AccordionPanel pb={4}>
                      <FormControl>
                        <Textarea
                          value={editMetadata.target_market || ''}
                          onChange={(e) => setEditMetadata({ ...editMetadata, target_market: e.target.value })}
                          placeholder="e.g., B2B SaaS companies, Healthcare providers, Consumers"
                          rows={3}
                        />
                      </FormControl>
                    </AccordionPanel>
                  </AccordionItem>

                  <AccordionItem>
                    <AccordionButton>
                      <Box flex="1" textAlign="left">
                        <Text fontWeight="semibold">Leadership Information</Text>
                      </Box>
                      <AccordionIcon />
                    </AccordionButton>
                    <AccordionPanel pb={4}>
                      <FormControl>
                        <Textarea
                          value={editMetadata.leadership_info || ''}
                          onChange={(e) => setEditMetadata({ ...editMetadata, leadership_info: e.target.value })}
                          placeholder="CEO, founders, key executives..."
                          rows={3}
                        />
                      </FormControl>
                    </AccordionPanel>
                  </AccordionItem>

                  {editMetadata.key_products_services && editMetadata.key_products_services.length > 0 && (
                    <AccordionItem>
                      <AccordionButton>
                        <Box flex="1" textAlign="left">
                          <Text fontWeight="semibold">Key Products & Services</Text>
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                      <AccordionPanel pb={4}>
                        <VStack align="stretch" spacing={2}>
                          {editMetadata.key_products_services.map((item, idx) => (
                            <Text key={idx} fontSize="sm">• {item}</Text>
                          ))}
                        </VStack>
                      </AccordionPanel>
                    </AccordionItem>
                  )}

                  {editMetadata.social_media_links && Object.keys(editMetadata.social_media_links).length > 0 && (
                    <AccordionItem>
                      <AccordionButton>
                        <Box flex="1" textAlign="left">
                          <Text fontWeight="semibold">Social Media</Text>
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                      <AccordionPanel pb={4}>
                        <VStack align="stretch" spacing={2}>
                          {Object.entries(editMetadata.social_media_links).map(([platform, url]) => (
                            <HStack key={platform}>
                              <Text fontSize="sm" fontWeight="semibold" textTransform="capitalize" minW="100px">
                                {platform}:
                              </Text>
                              <Text fontSize="sm" color="blue.600" as="a" href={url} target="_blank" rel="noopener noreferrer">
                                {url}
                              </Text>
                            </HStack>
                          ))}
                        </VStack>
                      </AccordionPanel>
                    </AccordionItem>
                  )}
                </Accordion>
              </Box>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onEditClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleSaveEdit}
              isLoading={updateOrgMutation.isPending}
            >
              Save Changes
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
};

export default OrganizationDetail;

