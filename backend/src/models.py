from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, UniqueConstraint, Table, Enum as SQLEnum, TypeDecorator
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import CHAR
import uuid
import json
from enum import Enum
from .database import Base

# Custom UUID type that works with both PostgreSQL and SQLite
class GUID(TypeDecorator):
    """Platform-independent GUID type. Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value

# Custom JSON type that works with both PostgreSQL (JSONB) and SQLite (Text)
class JSON(TypeDecorator):
    """Platform-independent JSON type. Uses PostgreSQL's JSONB type, otherwise uses Text, storing as JSON-encoded string."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            return json.loads(value)

# Answer mode enum for controlling response format and depth
class AnswerMode(str, Enum):
    SUMMARY = "summary"  # Executive Summary: Concise, executive-level (2-3 paragraphs max)
    LIGHT = "light"  # One-Pager/Memo: Balanced detail with key evidence (default)
    EXTENDED = "extended"  # Executive Report: Comprehensive, detailed analysis
    PROJECT_PLAN = "project_plan"  # Strategic Project Plan: 30-60-90 day structured timeline
    ROADMAP = "roadmap"  # Strategic Framework/Roadmap: Framework analysis + actionable roadmap

# Association table for many-to-many relationship between ChatQuery and File
chat_query_files = Table(
    'chat_query_files',
    Base.metadata,
    Column('chat_query_id', Integer, ForeignKey('chat_queries.id'), primary_key=True),
    Column('file_id', Integer, ForeignKey('files.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)  # Admin role for user management
    is_active = Column(Boolean, default=True, nullable=False)  # Active status (false = banned/disabled)
    api_key = Column(GUID, unique=True, index=True, nullable=False, default=uuid.uuid4)
    password_reset_token = Column(String, nullable=True, index=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to chat queries
    queries = relationship("ChatQuery", back_populates="user", cascade="all, delete-orphan")
    
    # Relationships for organizations
    owned_organizations = relationship("Organization", back_populates="owner", foreign_keys="Organization.owner_id", cascade="all, delete-orphan")
    organization_memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")
    
    # Relationships for threads
    threads = relationship("Thread", back_populates="user", cascade="all, delete-orphan")
    
    # Relationships for files
    files = relationship("File", back_populates="user", cascade="all, delete-orphan")
    
    # Relationships for custom agents
    custom_agents = relationship("CustomAgent", back_populates="user", cascade="all, delete-orphan")
    
    # Relationships for usage logs
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")

class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(GUID, unique=True, index=True, nullable=False, default=uuid.uuid4)  # External UUID for URLs
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    title = Column(String, nullable=True)  # Optional title for the thread
    thread_metadata = Column(JSON, nullable=True)  # Thread-level preferences (budget-conscious vs outcome-conscious, etc.)
    default_answer_mode = Column(SQLEnum(AnswerMode), default=AnswerMode.LIGHT, nullable=False)  # Default verbosity for new queries in this thread
    selected_agent_ids = Column(JSON, nullable=True)  # List of agent IDs active for this thread, null = all agents
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="threads")
    organization = relationship("Organization", back_populates="threads")
    queries = relationship("ChatQuery", back_populates="thread", cascade="all, delete-orphan")

class ChatQuery(Base):
    __tablename__ = "chat_queries"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)  # Nullable in case of errors
    answer_mode = Column(SQLEnum(AnswerMode), default=AnswerMode.LIGHT, nullable=False)  # Verbosity level used for this query
    reask_of_query_id = Column(Integer, ForeignKey("chat_queries.id"), nullable=True)  # Reference to original query if this is a re-ask
    followup_of_query_id = Column(Integer, ForeignKey("chat_queries.id"), nullable=True)  # Reference to parent query for deep-dive follow-ups
    execution_trace = Column(JSON, nullable=True)  # Store execution trace as JSON
    content_structure = Column(JSON, nullable=True)  # Structured content: {summary, visualizations, raw_data, references}
    followup_questions = Column(JSON, nullable=True)  # Suggested follow-up questions
    agent_ids_used = Column(JSON, nullable=True)  # Which agent IDs were available for this query (audit trail)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="queries")
    thread = relationship("Thread", back_populates="queries")
    organization = relationship("Organization", back_populates="queries")
    files = relationship("File", secondary=chat_query_files, back_populates="chat_queries")

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(GUID, unique=True, index=True, nullable=False, default=uuid.uuid4)  # External UUID for URLs
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    org_metadata = Column(JSON, nullable=True)  # Structured metadata as JSON (renamed from 'metadata' to avoid SQLAlchemy conflict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_organizations")
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    threads = relationship("Thread", back_populates="organization", cascade="all, delete-orphan")
    queries = relationship("ChatQuery", back_populates="organization", cascade="all, delete-orphan")
    files = relationship("File", back_populates="organization", cascade="all, delete-orphan")
    custom_agents = relationship("CustomAgent", back_populates="organization")

class OrganizationMember(Base):
    __tablename__ = "organization_members"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    can_read = Column(Boolean, default=True, nullable=False)
    can_write = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organization_memberships")
    
    # Ensure a user can only be a member once per organization
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_org_member'),
    )

class File(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Path to stored file
    content_type = Column(String, nullable=True)  # MIME type
    file_size = Column(Integer, nullable=False)  # Size in bytes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="files")
    organization = relationship("Organization", back_populates="files")
    chat_queries = relationship("ChatQuery", secondary=chat_query_files, back_populates="files")

class CustomAgent(Base):
    __tablename__ = "custom_agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)  # Optional org scope for sharing
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    role = Column(String, nullable=True)  # Agent role description for director routing
    system_prompt = Column(Text, nullable=False)
    tools = Column(JSON, nullable=True)  # List of tool IDs (e.g. ["web_search", "calculator"])
    can_delegate_to = Column(JSON, nullable=True)  # List of agent IDs this agent can delegate to
    model = Column(String, nullable=True)  # Optional LLM model override
    use_cases = Column(JSON, nullable=True)  # Array of strings stored as JSON
    style = Column(String, nullable=True)
    is_agentic = Column(Boolean, default=False, nullable=False)  # Whether agent participates in crew system
    shared_with_org = Column(Boolean, default=False, nullable=False)  # Whether org members can use it
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="custom_agents")
    organization = relationship("Organization", back_populates="custom_agents")

class ToolCache(Base):
    __tablename__ = "tool_cache"

    key = Column(String, primary_key=True)
    tool_name = Column(String, nullable=False, index=True)
    result = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)


class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    endpoint = Column(String, nullable=False)  # e.g., "/api/llm/chat"
    method = Column(String, nullable=False)  # e.g., "POST"
    authenticated_via = Column(String, nullable=False)  # "api_key" or "bearer_token"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", back_populates="usage_logs")

