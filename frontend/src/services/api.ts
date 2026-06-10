import axios from 'axios';

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:3001').replace(/\/+$/, '');

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout for most requests
});

// Request interceptor - add auth token if available
api.interceptors.request.use(
  (config) => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        if (user.api_key) {
          config.headers['X-API-Key'] = user.api_key;
        }
      } catch (e) {
        console.error('Error parsing user from localStorage:', e);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle common errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear user data on auth error
      localStorage.removeItem('user');

      // Redirect to login if not already there
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export type AnswerMode = 'summary' | 'light' | 'extended' | 'project_plan' | 'roadmap';

export interface User {
  id: number;
  email: string;
  username: string;
  api_key: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface ChatMessage {
  message: string;
  user_id?: number;
}

export interface AgentNode {
  id: string;
  type: string;
  name: string;
  metadata?: Record<string, any>;
}

export interface AgentEdge {
  source: string;
  target: string;
  label?: string;
}

export interface ExecutionTrace {
  nodes: AgentNode[];
  edges: AgentEdge[];
  metadata?: {
    error?: string;
    execution_times?: {
      total_time: number;
      agent_time: number;
      tool_time: number;
      cached_tool_calls?: number;
      total_tool_calls?: number;
    };
    [key: string]: any;
  };
}

export interface Citation {
  number?: number;  // For numbered inline citations [1], [2], [3]
  type: string;
  url?: string;
  title?: string;
  author?: string;
  date?: string;
  source?: string;
  description?: string;
}

export interface FollowUpQuestion {
  question: string;
  rationale: string;
  type?: 'related' | 'deep_dive';
}

export interface ChatResponse {
  response: string;
  query_id?: number;
  is_clarification?: boolean;
  clarification_questions?: string[];
  execution_trace?: ExecutionTrace;
  citations?: Citation[];
  recommendations?: string[];
  followup_questions?: FollowUpQuestion[];
}

export const authAPI = {
  register: async (data: RegisterData): Promise<User> => {
    const response = await api.post<User>('/api/auth/register', data);
    return response.data;
  },
  login: async (data: LoginData): Promise<User> => {
    const response = await api.post<User>('/api/auth/login', data);
    return response.data;
  },
  resetPassword: async (token: string, newPassword: string): Promise<User> => {
    const response = await api.post<User>('/api/auth/reset-password', {
      token,
      new_password: newPassword,
    });
    return response.data;
  },
  verify: async (): Promise<User> => {
    const response = await api.get<User>('/api/auth/verify');
    return response.data;
  },
};

export interface Thread {
  id: number;
  user_id: number;
  organization_id: number;
  title?: string;
  thread_metadata?: {
    budget_focus?: number; // 0.0 = very budget-conscious, 1.0 = very outcome-conscious
    response_length?: number; // 0.0 = brief, 1.0 = comprehensive
    creativity?: number; // 0.0 = off-the-shelf, 1.0 = innovative
  };
  selected_agent_ids?: string[] | null; // Agent IDs active for this thread, null = all agents
  created_at: string;
  updated_at?: string;
  message_count?: number; // Number of queries/messages in the thread
}

export interface ThreadCreate {
  organization_id: number;
  title?: string;
  thread_metadata?: {
    budget_focus?: number;
  };
  selected_agent_ids?: string[] | null;
}

export interface ThreadUpdate {
  title?: string;
  thread_metadata?: {
    budget_focus?: number;
    response_length?: number;
    creativity?: number;
  };
  selected_agent_ids?: string[] | null;
}

export interface ChatQuery {
  id: number;
  thread_id: number;
  user_id: number;
  organization_id: number;
  message: string;
  response?: string;
  answer_mode?: AnswerMode;
  reask_of_query_id?: number | null;
  followup_of_query_id?: number | null;
  execution_trace?: ExecutionTrace;
  created_at: string;
  files?: FileInfo[];
  citations?: Citation[];
  recommendations?: string[];
  followup_questions?: FollowUpQuestion[];
  content_structure?: {
    summary?: string;
    visualizations?: Array<{
      type: string;
      url?: string;
      data?: any;
      caption?: string;
    }>;
    raw_data?: Array<{
      label: string;
      value: any;
      type?: string;
    }>;
    references?: Citation[];
  };
  execution_times?: {
    total_time?: number;
    agent_time?: number;
    tool_time?: number;
    cached_tool_calls?: number;
    total_tool_calls?: number;
  };
}

export interface FileInfo {
  id: number;
  user_id: number;
  organization_id: number;
  filename: string;
  original_filename: string;
  content_type?: string;
  file_size: number;
  created_at: string;
}

export const chatAPI = {
  sendMessage: async (message: string, organizationId: number, userId: number, threadId?: number, fileIds?: number[], chatMode?: string, answerMode?: AnswerMode): Promise<ChatResponse> => {
    const payload: any = {
      message,
      organization_id: organizationId,
      user_id: userId,
    };

    if (threadId !== undefined) {
      payload.thread_id = threadId;
    }
    
    // Always include file_ids, even if empty array or undefined
    // This ensures the backend knows we're sending file information
    if (fileIds !== undefined && fileIds.length > 0) {
      payload.file_ids = fileIds;
    }
    
    // Include chat mode (defaults to "strategy" if not provided)
    if (chatMode) {
      payload.chat_mode = chatMode;
    }

    // Include answer mode if provided (backend uses thread default if not specified)
    if (answerMode) {
      payload.answer_mode = answerMode;
    }

    const response = await api.post<ChatResponse>('/api/llm/chat', payload);
    return response.data;
  },
  sendMessageStream: (
    message: string,
    organizationId: number,
    userId: number,
    threadId: number | undefined,
    fileIds: number[] | undefined,
    chatMode: string | undefined,
    answerMode: AnswerMode | undefined,
    reaskOfQueryId: number | null | undefined,
    agentIds: string[] | null | undefined,
    onEvent: (event: { type: string; data: any }) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void,
    followupOfQueryId?: number | null
  ): (() => void) => {
    const payload: any = {
      message,
      organization_id: organizationId,
      user_id: userId,
    };

    if (threadId !== undefined) {
      payload.thread_id = threadId;
    }

    if (fileIds !== undefined && fileIds.length > 0) {
      payload.file_ids = fileIds;
    }

    if (chatMode) {
      payload.chat_mode = chatMode;
    }

    if (answerMode) {
      payload.answer_mode = answerMode;
    }

    if (reaskOfQueryId !== undefined && reaskOfQueryId !== null) {
      payload.reask_of_query_id = reaskOfQueryId;
    }

    if (agentIds !== undefined && agentIds !== null) {
      payload.agent_ids = agentIds;
    }

    if (followupOfQueryId !== undefined && followupOfQueryId !== null) {
      payload.followup_of_query_id = followupOfQueryId;
    }

    // Use EventSource for SSE
    const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:3001').replace(/\/+$/, '');
    const url = `${API_URL}/api/llm/chat/stream`;
    
    // Create a POST request with SSE (EventSource doesn't support POST, so we use fetch)
    const controller = new AbortController();
    
    // For SSE with POST, we need to use fetch with ReadableStream
    // Build headers - include API key from localStorage (same as axios interceptor)
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        if (user.api_key) {
          headers['X-API-Key'] = user.api_key;
        }
      } catch (e) {
        // ignore parse errors
      }
    }

    fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        
        if (!reader) {
          throw new Error('No response body');
        }
        
        let buffer = '';
        
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            break;
          }
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                onEvent(data);
                
                if (data.type === 'done') {
                  onComplete?.();
                  return;
                }
                if (data.type === 'error') {
                  onError?.(new Error(data.data?.message || 'Unknown error'));
                  return;
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
        
        onComplete?.();
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          onError?.(error);
        }
      });
    
    // Return cleanup function
    return () => {
      controller.abort();
    };
  },
  getQueries: async (threadId: number, userId: number) => {
    const response = await api.get<ChatQuery[]>('/api/queries', {
      params: { thread_id: threadId, user_id: userId }
    });
    return response.data;
  },
  createThread: async (thread: ThreadCreate, userId: number): Promise<Thread> => {
    const response = await api.post<Thread>('/api/threads', thread, {
      params: { user_id: userId },
    });
    return response.data;
  },
  getThreads: async (userId: number, organizationId?: number): Promise<Thread[]> => {
    const params: any = { user_id: userId };
    if (organizationId) {
      params.organization_id = organizationId;
    }
    const response = await api.get<Thread[]>('/api/threads', { params });
    return response.data;
  },
  getThread: async (threadId: number, userId: number): Promise<Thread> => {
    const response = await api.get<Thread>(`/api/threads/${threadId}`, {
      params: { user_id: userId },
    });
    return response.data;
  },
  getThreadQueries: async (threadId: number, userId: number): Promise<ChatQuery[]> => {
    const response = await api.get<ChatQuery[]>(`/api/threads/${threadId}/queries`, {
      params: { user_id: userId },
    });
    return response.data;
  },
  updateThread: async (threadId: number, threadUpdate: ThreadUpdate, userId: number): Promise<Thread> => {
    const response = await api.put<Thread>(`/api/threads/${threadId}`, threadUpdate, {
      params: { user_id: userId },
    });
    return response.data;
  },
  deleteThread: async (threadId: number, userId: number): Promise<void> => {
    await api.delete(`/api/threads/${threadId}`, {
      params: { user_id: userId },
    });
  },
};

export interface AgentInfo {
  id: string;
  name: string;
  description: string;
  use_cases: string[];
  style: string;
  system_prompt: string;
  is_custom?: boolean;
  user_id?: number;
  tools?: string[];
  can_delegate_to?: string[];
  role?: string;
  is_agentic?: boolean;
  organization_id?: number;
  shared_with_org?: boolean;
}

export interface AgentRegistryResponse {
  agents: AgentInfo[];
}

export interface CustomAgent {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  role?: string;
  system_prompt: string;
  tools: string[];
  can_delegate_to: string[];
  model?: string;
  use_cases: string[];
  style?: string;
  is_agentic: boolean;
  organization_id?: number;
  shared_with_org: boolean;
  created_at: string;
  updated_at?: string;
}

export interface CustomAgentCreate {
  name: string;
  description?: string;
  role?: string;
  system_prompt: string;
  tools?: string[];
  can_delegate_to?: string[];
  model?: string;
  use_cases?: string[];
  style?: string;
  is_agentic?: boolean;
  organization_id?: number;
  shared_with_org?: boolean;
}

export interface CustomAgentUpdate {
  name?: string;
  description?: string;
  role?: string;
  system_prompt?: string;
  tools?: string[];
  can_delegate_to?: string[];
  model?: string;
  use_cases?: string[];
  style?: string;
  is_agentic?: boolean;
  organization_id?: number;
  shared_with_org?: boolean;
}

export interface ToolInfo {
  id: string;
  name: string;
  description: string;
  parameters: any;
}

export interface ToolsResponse {
  tools: ToolInfo[];
}

export const agentAPI = {
  getAgents: async (userId?: number): Promise<AgentInfo[]> => {
    const params = userId ? { user_id: userId } : {};
    const response = await api.get<AgentRegistryResponse>('/api/agents', { params });
    return response.data.agents;
  },
  getTools: async (): Promise<ToolInfo[]> => {
    const response = await api.get<ToolsResponse>('/api/tools');
    return response.data.tools;
  },
  getCustomAgents: async (userId: number): Promise<CustomAgent[]> => {
    const response = await api.get<CustomAgent[]>('/api/agents/custom', {
      params: { user_id: userId },
    });
    return response.data;
  },
  createCustomAgent: async (agent: CustomAgentCreate, userId: number): Promise<CustomAgent> => {
    const response = await api.post<CustomAgent>('/api/agents/custom', agent, {
      params: { user_id: userId },
    });
    return response.data;
  },
  updateCustomAgent: async (
    agentId: number,
    agent: CustomAgentUpdate,
    userId: number
  ): Promise<CustomAgent> => {
    const response = await api.put<CustomAgent>(`/api/agents/custom/${agentId}`, agent, {
      params: { user_id: userId },
    });
    return response.data;
  },
  deleteCustomAgent: async (agentId: number, userId: number): Promise<void> => {
    await api.delete(`/api/agents/custom/${agentId}`, {
      params: { user_id: userId },
    });
  },
};

export const fileAPI = {
  uploadFile: async (file: File, organizationId: number, userId: number): Promise<FileInfo> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<FileInfo>('/api/files/upload', formData, {
      params: {
        user_id: userId,
        organization_id: organizationId,
      },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  getFiles: async (userId: number, organizationId?: number): Promise<FileInfo[]> => {
    const params: any = { user_id: userId };
    if (organizationId) {
      params.organization_id = organizationId;
    }
    const response = await api.get<FileInfo[]>('/api/files', { params });
    return response.data;
  },
  getOrganizationFiles: async (orgId: number, userId: number): Promise<FileInfo[]> => {
    const response = await api.get<FileInfo[]>(`/api/organizations/${orgId}/files`, {
      params: { user_id: userId },
    });
    return response.data;
  },
  getFileInfo: async (fileId: number, userId: number): Promise<FileInfo> => {
    const response = await api.get<FileInfo>(`/api/files/${fileId}`, {
      params: { user_id: userId },
    });
    return response.data;
  },
  downloadFile: async (fileId: number, userId: number): Promise<Blob> => {
    const response = await api.get(`/api/files/${fileId}/download`, {
      params: { user_id: userId },
      responseType: 'blob',
    });
    return response.data;
  },
  deleteFile: async (fileId: number, userId: number): Promise<void> => {
    await api.delete(`/api/files/${fileId}`, {
      params: { user_id: userId },
    });
  },
};

// Usage statistics types
export interface DailyUsageStat {
  date: string;
  count: number;
}

export interface UserUsageStats {
  daily_usage: DailyUsageStat[];
  total_count: number;
}

export interface AllUsersUsageStats {
  user_id: number;
  username: string;
  email: string;
  daily_usage: DailyUsageStat[];
}

export const usageAPI = {
  getMyUsageStats: async (userId: number, days: number = 30): Promise<UserUsageStats> => {
    const response = await api.get<UserUsageStats>('/api/usage/stats', {
      params: { user_id: userId, days },
    });
    return response.data;
  },
  getAllUsersUsageStats: async (userId: number, days: number = 30): Promise<AllUsersUsageStats[]> => {
    const response = await api.get<AllUsersUsageStats[]>('/api/admin/usage/all', {
      params: { user_id: userId, days },
    });
    return response.data;
  },
};

// Organization Metadata types
export interface OrganizationMetadata {
  industry_name?: string;
  org_type?: string;
  purpose?: string;
  goals_missions?: string;
  current_limitations?: string;
  resources_available?: string;
  // New fields from website scraper
  website_url?: string;
  social_media_links?: Record<string, string>;
  key_products_services?: string[];
  target_market?: string;
  leadership_info?: string;
}

// Organization types
export interface Organization {
  id: number;
  name: string;
  description?: string;
  owner_id: number;
  metadata?: OrganizationMetadata;
  created_at: string;
  updated_at?: string;
}

export interface OrganizationWithStats extends Organization {
  thread_count: number;
  total_message_count: number;
  unique_user_count: number;
  file_count: number;
  owner_username?: string;
}

export interface OrganizationUpdate {
  name?: string;
  description?: string;
  metadata?: OrganizationMetadata;
}

export interface OrganizationWithMembers extends Organization {
  owner: User;
  members: OrganizationMember[];
}

export interface OrganizationMember {
  id: number;
  organization_id: number;
  user_id: number;
  can_read: boolean;
  can_write: boolean;
  created_at: string;
  user: User;
}

export interface OrganizationCreate {
  name: string;
  description?: string;
  metadata?: OrganizationMetadata;
}

export interface OrganizationMemberCreate {
  user_id?: number;
  email?: string;
  can_read?: boolean;
  can_write?: boolean;
}

export interface OrganizationMemberUpdate {
  can_read?: boolean;
  can_write?: boolean;
}

export const organizationAPI = {
  create: async (data: OrganizationCreate, userId: number): Promise<Organization> => {
    const response = await api.post<Organization>('/api/organizations', data, {
      params: { user_id: userId },
    });
    return response.data;
  },
  createOrganization: async (data: OrganizationCreate, userId: number): Promise<Organization> => {
    // Alias for create
    const response = await api.post<Organization>('/api/organizations', data, {
      params: { user_id: userId },
    });
    return response.data;
  },
  scrapeWebsite: async (url: string, userId: number): Promise<any> => {
    const response = await api.post<any>('/api/organizations/scrape-website', null, {
      params: { url, user_id: userId },
    });
    return response.data;
  },
  getMyOrganizations: async (userId: number): Promise<Organization[]> => {
    const response = await api.get<Organization[]>('/api/organizations', {
      params: { user_id: userId },
    });
    return response.data;
  },
  getMyOrganizationsWithStats: async (userId: number): Promise<OrganizationWithStats[]> => {
    const response = await api.get<OrganizationWithStats[]>('/api/organizations/with-stats', {
      params: { user_id: userId },
    });
    return response.data;
  },
  getById: async (orgId: number, userId: number): Promise<OrganizationWithMembers> => {
    const response = await api.get<OrganizationWithMembers>(`/api/organizations/${orgId}`, {
      params: { user_id: userId },
    });
    return response.data;
  },
  update: async (orgId: number, data: OrganizationUpdate, userId: number): Promise<Organization> => {
    const response = await api.put<Organization>(`/api/organizations/${orgId}`, data, {
      params: { user_id: userId },
    });
    return response.data;
  },
  delete: async (orgId: number, userId: number): Promise<void> => {
    await api.delete(`/api/organizations/${orgId}`, {
      params: { user_id: userId },
    });
  },
  addMember: async (orgId: number, member: OrganizationMemberCreate, userId: number): Promise<OrganizationMember> => {
    const response = await api.post<OrganizationMember>(`/api/organizations/${orgId}/members`, member, {
      params: { user_id: userId },
    });
    return response.data;
  },
  updateMember: async (orgId: number, memberUserId: number, update: OrganizationMemberUpdate, userId: number): Promise<OrganizationMember> => {
    const response = await api.put<OrganizationMember>(`/api/organizations/${orgId}/members/${memberUserId}`, update, {
      params: { user_id: userId },
    });
    return response.data;
  },
  removeMember: async (orgId: number, memberUserId: number, userId: number): Promise<void> => {
    await api.delete(`/api/organizations/${orgId}/members/${memberUserId}`, {
      params: { user_id: userId },
    });
  },
};

export interface UserUpdate {
  is_admin?: boolean;
  is_active?: boolean;
}

export interface AdminUserCreate {
  email: string;
  username: string;
  password: string;
  is_admin?: boolean;
}

export const adminAPI = {
  // User management
  createUser: async (adminUserId: number, data: AdminUserCreate): Promise<User> => {
    const response = await api.post<User>('/api/admin/users', data, {
      params: { admin_user_id: adminUserId },
    });
    return response.data;
  },
  getUsers: async (): Promise<User[]> => {
    const response = await api.get<User[]>('/api/users');
    return response.data;
  },
  updateUser: async (targetUserId: number, adminUserId: number, update: UserUpdate): Promise<User> => {
    const response = await api.patch<User>(
      `/api/admin/users/${targetUserId}`,
      update,
      {
        params: { admin_user_id: adminUserId },
      }
    );
    return response.data;
  },
  getUserThreads: async (targetUserId: number, adminUserId: number): Promise<Thread[]> => {
    const response = await api.get<Thread[]>(
      `/api/admin/users/${targetUserId}/threads`,
      {
        params: { admin_user_id: adminUserId },
      }
    );
    return response.data;
  },
  getUserQueries: async (targetUserId: number, adminUserId: number, limit: number = 50): Promise<ChatQuery[]> => {
    const response = await api.get<ChatQuery[]>(
      `/api/admin/users/${targetUserId}/queries`,
      {
        params: { admin_user_id: adminUserId, limit },
      }
    );
    return response.data;
  },
  invalidateUserSession: async (targetUserId: number, adminUserId: number): Promise<{ message: string; affected_user_count: number }> => {
    const response = await api.post(
      `/api/admin/users/${targetUserId}/invalidate-session`,
      null,
      { params: { admin_user_id: adminUserId } }
    );
    return response.data;
  },
  invalidateAllSessions: async (adminUserId: number): Promise<{ message: string; affected_user_count: number }> => {
    const response = await api.post(
      '/api/admin/users/invalidate-all-sessions',
      null,
      { params: { admin_user_id: adminUserId } }
    );
    return response.data;
  },
  generatePasswordResetToken: async (targetUserId: number, adminUserId: number): Promise<{ token: string; expires_in_hours: number; reset_url: string; message: string }> => {
    const response = await api.post(
      `/api/admin/users/${targetUserId}/password-reset-token`,
      null,
      { params: { admin_user_id: adminUserId } }
    );
    return response.data;
  },
};

export default api;

