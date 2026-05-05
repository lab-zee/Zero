from pydantic import BaseModel, EmailStr, model_validator
from datetime import datetime
from typing import Optional, List
import uuid

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    api_key: uuid.UUID
    is_admin: bool = False
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True

class AdminUserCreate(UserCreate):
    """Schema for admin creating a user account on someone's behalf"""
    is_admin: bool = False

class UserUpdate(BaseModel):
    """Schema for updating user properties (admin only)"""
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None

class SessionInvalidationResponse(BaseModel):
    message: str
    affected_user_count: int

class PasswordResetTokenResponse(BaseModel):
    token: str
    expires_in_hours: int
    reset_url: str
    message: str

class PasswordResetRequest(BaseModel):
    token: str
    new_password: str

class UserWithToken(UserResponse):
    access_token: str

# Thread schemas
class ThreadBase(BaseModel):
    title: Optional[str] = None
    thread_metadata: Optional[dict] = None  # Thread-level preferences

class ThreadCreate(ThreadBase):
    organization_id: int
    selected_agent_ids: Optional[list[str]] = None  # Agent IDs active for this thread, null = all agents

class ThreadUpdate(BaseModel):
    title: Optional[str] = None
    thread_metadata: Optional[dict] = None
    selected_agent_ids: Optional[list[str]] = None  # Agent IDs active for this thread, null = all agents

class ThreadResponse(ThreadBase):
    id: int
    user_id: int
    organization_id: int
    selected_agent_ids: Optional[list[str]] = None  # Agent IDs active for this thread
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: Optional[int] = None  # Number of queries/messages in the thread

    class Config:
        from_attributes = True

# File schemas (defined early for forward references)
class FileResponse(BaseModel):
    id: int
    user_id: int
    organization_id: int
    filename: str
    original_filename: str
    content_type: Optional[str] = None
    file_size: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class FileUploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    content_type: Optional[str] = None
    file_size: int
    created_at: datetime

# Execution trace schemas for agent visualization (defined early for use in ChatQueryResponse)
class AgentNode(BaseModel):
    id: str
    type: str  # "agent" | "tool" | "context" | "query" | "response"
    name: str
    metadata: Optional[dict] = None

class AgentEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None

class ExecutionTrace(BaseModel):
    nodes: List[AgentNode]
    edges: List[AgentEdge]
    metadata: Optional[dict] = None  # Contains progress_updates, execution_times, etc.

# Citation schema
class Citation(BaseModel):
    type: str
    url: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    source: Optional[str] = None
    description: Optional[str] = None

# Chat query schemas
class ChatQueryBase(BaseModel):
    message: str

class ChatQueryCreate(ChatQueryBase):
    thread_id: int
    user_id: int
    organization_id: int
    answer_mode: Optional[str] = "light"  # Verbosity level for this query
    reask_of_query_id: Optional[int] = None  # Reference to original query if re-ask
    followup_of_query_id: Optional[int] = None  # Reference to parent query for deep-dive follow-ups

class ChatQueryResponse(BaseModel):
    id: int
    thread_id: int
    user_id: int
    organization_id: int
    message: str
    response: Optional[str]
    answer_mode: Optional[str] = "light"  # Verbosity level used for this query
    reask_of_query_id: Optional[int] = None  # Reference to original query if re-ask
    followup_of_query_id: Optional[int] = None  # Reference to parent query for deep-dive follow-ups
    execution_trace: Optional[ExecutionTrace] = None
    created_at: datetime
    files: Optional[List[FileResponse]] = []
    execution_times: Optional[dict] = None  # Execution times extracted from execution_trace metadata
    content_structure: Optional[dict] = None  # Structured content: {summary, visualizations, raw_data, references}
    followup_questions: Optional[List[dict]] = None  # Suggested follow-up questions
    citations: Optional[List[Citation]] = None  # Citations from sources
    recommendations: Optional[List[str]] = None  # Recommended readings

    class Config:
        from_attributes = True

# Request/Response models for API
class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[int] = None  # If None, creates a new thread
    organization_id: int  # Required - must select an organization
    user_id: Optional[int] = None  # Optional for now, can be from auth later
    file_ids: Optional[list[int]] = None  # Optional list of file IDs to associate with the query
    chat_mode: Optional[str] = "strategy"  # Available modes: "strategy", "generic", "analytical", "creative", "executive"
    answer_mode: Optional[str] = None  # Output format: "summary" (Exec Summary), "light" (One-Pager), "extended" (Exec Report), "project_plan" (30-60-90), "roadmap" (Framework/Roadmap). If None, uses thread default.
    reask_of_query_id: Optional[int] = None  # If provided, this is a response to a clarification question from the specified query
    followup_of_query_id: Optional[int] = None  # If provided, this is a deep-dive follow-up that carries the parent query's full analysis context
    agent_ids: Optional[list[str]] = None  # Per-query agent selection override. null = use thread default or all agents.

class ChatResponse(BaseModel):
    response: str
    query_id: Optional[int] = None
    is_clarification: Optional[bool] = None  # True if response contains clarification questions
    clarification_questions: Optional[list[str]] = None  # Extracted clarification questions if any
    execution_trace: Optional[ExecutionTrace] = None  # Execution trace for agent visualization
    citations: Optional[List[Citation]] = None  # Citations from sources
    recommendations: Optional[List[str]] = None  # Recommended readings

class HealthResponse(BaseModel):
    status: str
    timestamp: str

# Agent registry schemas
class AgentInfo(BaseModel):
    id: str
    name: str
    description: str
    use_cases: list[str]
    style: str
    system_prompt: str
    is_custom: bool = False  # True for user-created agents
    user_id: Optional[int] = None  # Only for custom agents
    tools: list[str] = []  # List of tool IDs this agent can use
    can_delegate_to: list[str] = []  # List of agent IDs this agent can delegate to
    role: Optional[str] = None  # Agent role/description
    is_agentic: bool = False  # Whether agent participates in crew system
    organization_id: Optional[int] = None  # Org scope for sharing
    shared_with_org: bool = False  # Whether org members can use it

class AgentRegistryResponse(BaseModel):
    agents: list[AgentInfo]

# Custom Agent schemas
class CustomAgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    role: Optional[str] = None  # Agent role description for director routing
    system_prompt: str
    tools: Optional[list[str]] = []  # List of tool IDs
    can_delegate_to: Optional[list[str]] = []  # List of agent IDs this agent can delegate to
    model: Optional[str] = None  # Optional LLM model override
    use_cases: Optional[list[str]] = []
    style: Optional[str] = None
    is_agentic: Optional[bool] = False  # Whether agent participates in crew system
    organization_id: Optional[int] = None  # Optional org scope for sharing
    shared_with_org: Optional[bool] = False  # Whether org members can use it

class CustomAgentCreate(CustomAgentBase):
    pass

class CustomAgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: Optional[list[str]] = None
    can_delegate_to: Optional[list[str]] = None
    model: Optional[str] = None
    use_cases: Optional[list[str]] = None
    style: Optional[str] = None
    is_agentic: Optional[bool] = None
    organization_id: Optional[int] = None
    shared_with_org: Optional[bool] = None

class CustomAgentResponse(CustomAgentBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Organization Metadata schema
class OrganizationMetadata(BaseModel):
    industry_name: Optional[str] = None
    org_type: Optional[str] = None  # startup, enterprise, smb, nonprofit, government, consulting
    purpose: Optional[str] = None
    goals_missions: Optional[str] = None
    current_limitations: Optional[str] = None
    resources_available: Optional[str] = None
    # New fields from website scraper
    website_url: Optional[str] = None
    social_media_links: Optional[dict] = None  # {platform: url}
    key_products_services: Optional[list] = None  # List of products/services
    target_market: Optional[str] = None
    leadership_info: Optional[str] = None

# Organization schemas
class OrganizationBase(BaseModel):
    name: str
    description: Optional[str] = None
    metadata: Optional[OrganizationMetadata] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[OrganizationMetadata] = None

class OrganizationResponse(OrganizationBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: Optional[dict] = None  # Store as dict for JSONB (maps from org_metadata column)
    
    class Config:
        from_attributes = False  # Disabled to avoid SQLAlchemy metadata conflict - we manually construct responses
        populate_by_name = True

class OrganizationWithStats(OrganizationResponse):
    thread_count: int = 0
    total_message_count: int = 0
    unique_user_count: int = 0
    file_count: int = 0
    owner_username: Optional[str] = None

class OrganizationWithOwner(OrganizationResponse):
    owner: UserResponse

# Organization Member schemas
class OrganizationMemberBase(BaseModel):
    can_read: bool = True
    can_write: bool = False

class OrganizationMemberCreate(OrganizationMemberBase):
    user_id: Optional[int] = None
    email: Optional[str] = None

class OrganizationMemberUpdate(BaseModel):
    can_read: Optional[bool] = None
    can_write: Optional[bool] = None

class OrganizationMemberResponse(OrganizationMemberBase):
    id: int
    organization_id: int
    user_id: int
    created_at: datetime
    user: UserResponse
    
    class Config:
        from_attributes = True

class OrganizationWithMembers(OrganizationResponse):
    owner: UserResponse
    members: list[OrganizationMemberResponse] = []

# Usage schemas
class DailyUsageStat(BaseModel):
    date: str
    count: int

class UserUsageStats(BaseModel):
    daily_usage: List[DailyUsageStat]
    total_count: int

class AllUsersUsageStats(BaseModel):
    user_id: int
    username: str
    email: str
    daily_usage: List[DailyUsageStat]

