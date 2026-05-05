from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File as FastAPIFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import json
import asyncio
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import os
from dotenv import load_dotenv

from .database import get_db, engine, Base
from . import models, schemas, crud, auth
from .llm import (
    build_strategy_prompt,
    build_organization_context,
    build_conversation_context,
    build_generic_prompt,
    build_analytical_prompt,
    build_creative_prompt,
    build_executive_prompt,
    AGENT_REGISTRY
)
from .agents import Crew, AgentRegistry
from .agents.tools.document import set_document_search_func
from .agents.tools.knowledge_base import set_knowledge_base_search_func
from .agents.base import ExecutionTrace, AgentNode, AgentEdge
from .llm.response_parser import parse_response
from .error_handlers import register_error_handlers
from .auth_middleware import AuthMiddleware
from .routers import auth as auth_router
from .routers import users as users_router
from .routers import threads as threads_router
from .routers import organizations as organizations_router
from .routers import files as files_router
from .routers import agents as agents_router
from .routers import usage as usage_router
from datetime import timedelta
from openai import OpenAI

load_dotenv()

app = FastAPI(title="LabZ API", version="1.0.0")

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)

# CORS middleware
# Get allowed origins from environment (comma-separated) or allow all in dev
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register error handlers
register_error_handlers(app)

# Auth middleware - validates API key on all /api/ routes except public ones
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(threads_router.router)
app.include_router(organizations_router.router)
app.include_router(files_router.router)
app.include_router(agents_router.router)
app.include_router(usage_router.router)

# Serve uploaded/generated files (images, etc.) as static assets
from .storage import UPLOAD_DIR
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Health check
@app.get("/health", response_model=schemas.HealthResponse)
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }

# API routes
@app.get("/api")
async def api_root():
    return {"message": "LabZ API is running!"}

# SSE endpoint for real-time execution trace updates
@app.post("/api/llm/chat/stream")
async def chat_with_llm_stream(
    request: schemas.ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Stream chat response with real-time execution trace updates via Server-Sent Events (SSE).
    """
    async def event_generator():
        event_queue = asyncio.Queue()
        final_response = None
        error_occurred = None
        done = False
        current_query_id = None  # Track query ID for incremental updates
        progress_updates = []  # Collect progress updates for persistence

        def event_callback(event_type: str, data: dict):
            """Callback to emit events during agent execution."""
            nonlocal current_query_id, progress_updates
            # Use thread-safe put_nowait since we're in sync context
            try:
                timestamp = datetime.now().isoformat()
                event_queue.put_nowait({
                    "type": event_type,
                    "data": data,
                    "timestamp": timestamp
                })

                # Collect progress updates for database persistence
                if event_type == "progress_update":
                    progress_updates.append({
                        **data,
                        "timestamp": timestamp
                    })

                # Force immediate flush for trace updates to show in real-time
                if event_type == "trace_update":
                    # Wake up the event loop to process this immediately
                    # Also persist trace update to database if query exists
                    if current_query_id and data.get("trace"):
                        try:
                            # Only update trace, don't touch other fields
                            crud.update_chat_query(
                                db, current_query_id,
                                execution_trace=data["trace"]
                            )
                        except Exception as e:
                            # Don't fail execution if trace update fails
                            print(f"Error updating trace in database: {e}")
            except:
                # Queue full or error - skip this event
                pass
        
        def run_agent_execution_sync():
            """Run agent execution synchronously (will be called in thread)."""
            nonlocal final_response, error_occurred, current_query_id, progress_updates
            import time
            execution_start_time = time.time()
            db_query = None  # Track the query for updates
            try:
                # Require user_id for authenticated requests
                if request.user_id is None:
                    error_occurred = "User ID required. Please login first."
                    event_queue.put_nowait({"type": "error", "data": {"message": error_occurred}})
                    return
                
                # Require organization_id
                if request.organization_id is None:
                    error_occurred = "Organization ID required. Please select an organization."
                    event_queue.put_nowait({"type": "error", "data": {"message": error_occurred}})
                    return
                
                # Verify user exists
                user = crud.get_user(db, user_id=request.user_id)
                if not user:
                    error_occurred = "User not found"
                    event_queue.put_nowait({"type": "error", "data": {"message": error_occurred}})
                    return
                
                user_id = request.user_id
                
                # Verify organization exists and user has access
                org = crud.get_organization(db, org_id=request.organization_id)
                if not org:
                    error_occurred = "Organization not found"
                    event_queue.put_nowait({"type": "error", "data": {"message": error_occurred}})
                    return
                
                # Sending a query is a mutation — require write access
                has_access = crud.check_org_permission(db, request.organization_id, user_id, require_write=True)
                if not has_access:
                    error_occurred = "You do not have write access to this organization"
                    event_queue.put_nowait({"type": "error", "data": {"message": error_occurred}})
                    return
                
                # Create thread if thread_id is not provided
                thread_id = request.thread_id
                if thread_id is None:
                    thread_create = schemas.ThreadCreate(
                        organization_id=request.organization_id,
                        title=None
                    )
                    db_thread = crud.create_thread(db, thread_create, user_id)
                    thread_id = db_thread.id
                    event_queue.put_nowait({
                        "type": "thread_created",
                        "data": {"thread_id": thread_id}
                    })
                
                # Verify thread exists
                thread = crud.get_thread(db, thread_id=thread_id)
                if not thread:
                    error_occurred = "Thread not found"
                    event_queue.put_nowait({"type": "error", "data": {"message": error_occurred}})
                    return
                
                # Gather context
                org_metadata = org.org_metadata if org.org_metadata else {}
                org_context = build_organization_context(org, org_metadata)
                previous_queries = crud.get_chat_queries_by_thread(db, thread_id=thread_id, skip=0, limit=20)
                conversation_context = build_conversation_context(previous_queries)
                
                # Get thread preferences
                thread_metadata = thread.thread_metadata if thread.thread_metadata else {}

                # Determine answer mode (per-question override or thread default)
                from .models import AnswerMode
                answer_mode_str = request.answer_mode or (thread.default_answer_mode.value if hasattr(thread, 'default_answer_mode') and thread.default_answer_mode else "light")
                # Validate answer mode
                try:
                    answer_mode = AnswerMode(answer_mode_str)
                except ValueError:
                    answer_mode = AnswerMode.LIGHT  # Fallback to default

                # Handle file attachments
                file_content = None
                if request.file_ids:
                    db_files = []
                    for file_id in request.file_ids:
                        db_file = crud.get_file(db, file_id=file_id)
                        if db_file:
                            if db_file.user_id != user_id:
                                has_file_access = crud.check_org_permission(db, db_file.organization_id, user_id, require_write=False)
                                if not has_file_access:
                                    continue
                            db_files.append(db_file)
                    
                    if db_files:
                        from .file_extraction import extract_files_content
                        try:
                            extracted_content, _ = extract_files_content(db_files)
                            if extracted_content:
                                file_content = extracted_content
                        except Exception as e:
                            print(f"File extraction exception: {str(e)}")
                
                # Create query in database immediately (before execution starts)
                # This ensures the query is persisted even if an error occurs
                from .models import AnswerMode
                query_create = schemas.ChatQueryCreate(
                    thread_id=thread_id,
                    user_id=user_id,
                    organization_id=request.organization_id,
                    message=request.message,
                    answer_mode=answer_mode.value,
                    reask_of_query_id=request.reask_of_query_id,
                    followup_of_query_id=request.followup_of_query_id
                )
                db_query = crud.create_chat_query(
                    db, query_create,
                    response="",  # Empty response initially
                    execution_trace=None,
                    content_structure=None,
                    followup_questions=None
                )

                # Set current_query_id for incremental updates during execution
                current_query_id = db_query.id

                # Associate files with query immediately if provided
                if request.file_ids:
                    crud.associate_files_with_query(db, db_query.id, request.file_ids)

                # Emit query_created event so frontend knows which query is being processed
                event_queue.put_nowait({
                    "type": "query_created",
                    "data": {"query_id": db_query.id}
                })

                # Check for slash command - direct tool execution
                from .slash_command_parser import parse_slash_command
                slash_command_result = parse_slash_command(request.message)

                if slash_command_result:
                    # Direct tool execution (bypasses agentic crew)
                    tool_name, tool_arguments = slash_command_result

                    # Create a simple trace for the tool execution
                    from .agents.base import ExecutionTrace
                    tool_trace = ExecutionTrace()

                    # Add query node
                    query_node_id = tool_trace.add_node(
                        type="query",
                        name="User Query",
                        metadata={"query": request.message}
                    )

                    # Emit initial trace
                    event_queue.put_nowait({
                        "type": "trace_update",
                        "data": {"trace": tool_trace.to_dict()}
                    })

                    # Execute tool directly
                    from .agents.tools import execute_tool, TOOL_IMPLEMENTATIONS

                    # Set up document and knowledge base search functions
                    # (these tools need database access)
                    def document_search_func(query: str, file_ids: list = None):
                        if not request.file_ids and not file_ids:
                            return "No documents available for search. Please attach files to your message."
                        search_file_ids = file_ids or request.file_ids or []
                        db_files = []
                        for file_id in search_file_ids:
                            db_file = crud.get_file(db, file_id=file_id)
                            if db_file:
                                db_files.append(db_file)
                        if not db_files:
                            return "No matching documents found."
                        from .file_extraction import extract_files_content
                        try:
                            extracted_content, _ = extract_files_content(db_files)
                            if extracted_content:
                                query_lower = query.lower()
                                if query_lower in extracted_content.lower():
                                    idx = extracted_content.lower().find(query_lower)
                                    start = max(0, idx - 200)
                                    end = min(len(extracted_content), idx + len(query) + 200)
                                    return f"Found in documents:\n{extracted_content[start:end]}"
                                return f"Document content available. Query '{query}' not explicitly found, but here's the document content:\n{extracted_content[:1000]}"
                            return "Could not extract content from documents."
                        except Exception as e:
                            return f"Error searching documents: {str(e)}"

                    def knowledge_base_search_func(query: str):
                        """Semantic search across organization's document corpus using vector embeddings"""
                        from .vector_store import search_documents
                        try:
                            results = search_documents(
                                organization_id=request.organization_id,
                                query=query,
                                n_results=5
                            )
                            if not results:
                                return "No relevant documents found in the organization's knowledge base."
                            formatted_results = []
                            for i, result in enumerate(results, 1):
                                formatted_results.append(
                                    f"**Result {i}** (from {result['filename']}):\n{result['content']}\n"
                                )
                            return "\n".join(formatted_results)
                        except Exception as e:
                            return f"Error searching knowledge base: {str(e)}"

                    set_document_search_func(document_search_func)
                    set_knowledge_base_search_func(knowledge_base_search_func)

                    # Build tool registry with special functions if needed
                    tool_registry = TOOL_IMPLEMENTATIONS.copy()

                    # Add tool node to trace
                    tool_node_id = tool_trace.add_node(
                        type="tool",
                        name=tool_name,
                        metadata={"arguments": tool_arguments}
                    )
                    tool_trace.add_edge(query_node_id, tool_node_id, label="executes")

                    # Emit trace with tool node
                    event_queue.put_nowait({
                        "type": "trace_update",
                        "data": {"trace": tool_trace.to_dict()}
                    })

                    # Execute the tool
                    import time
                    tool_start_time = time.time()
                    tool_result = execute_tool(tool_name, tool_arguments, tool_registry)
                    tool_execution_time = time.time() - tool_start_time

                    # Update tool node with result
                    for node in tool_trace.nodes:
                        if node.id == tool_node_id:
                            node.metadata["result_preview"] = tool_result[:500] if len(tool_result) > 500 else tool_result
                            node.metadata["execution_time"] = tool_execution_time
                            break

                    # Format the response
                    response_text = f"**Tool: {tool_name}**\n\n{tool_result}"

                    # Add response node
                    response_node_id = tool_trace.add_node(
                        type="response",
                        name="Tool Result",
                        metadata={"response": response_text}
                    )
                    tool_trace.add_edge(tool_node_id, response_node_id, label="produces")

                    # Calculate total execution time
                    total_execution_time = time.time() - execution_start_time

                    # Add execution time metadata to trace
                    tool_trace.metadata = {
                        "execution_times": {
                            "total_time": total_execution_time,
                            "agent_time": 0,  # No agent involved
                            "tool_time": tool_execution_time
                        },
                        "progress_updates": progress_updates if progress_updates else []
                    }

                    # Emit final trace
                    event_queue.put_nowait({
                        "type": "trace_update",
                        "data": {"trace": tool_trace.to_dict()}
                    })

                    # Stream the response text
                    for char in response_text:
                        event_queue.put_nowait({
                            "type": "token",
                            "data": {"token": char}
                        })

                    # Update database with result
                    crud.update_chat_query(
                        db, db_query.id,
                        response=response_text,
                        execution_trace=tool_trace.to_dict(),
                        execution_times={
                            "total_time": total_execution_time,
                            "agent_time": 0,
                            "tool_time": tool_execution_time
                        }
                    )

                    # Emit done event
                    event_queue.put_nowait({
                        "type": "done",
                        "data": {
                            "query_id": db_query.id,
                            "response": response_text,
                            "execution_trace": tool_trace.to_dict()
                        }
                    })

                    final_response = response_text
                    return  # Skip agentic execution

                # Use agentic framework
                chat_mode = request.chat_mode or "agentic"
                if chat_mode == "agentic":
                    openai_api_key = os.getenv("OPENAI_API_KEY")
                    if not openai_api_key:
                        error_occurred = "OpenAI API key not configured"
                        event_queue.put_nowait({"type": "error", "data": {"message": error_occurred}})
                        return
                    
                    # Handle proxy vars
                    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
                    original_proxies = {}
                    for var in proxy_vars:
                        if var in os.environ:
                            original_proxies[var] = os.environ.pop(var)
                    
                    try:
                        # Use LLMClient factory to support both OpenAI and Gemini
                        from .llm_client import get_llm_client, LLMClient
                        model = os.getenv("LLM_MODEL", "gemini-3-flash-preview")
                        llm_client = get_llm_client(model=model)
                        # For backward compatibility, also create OpenAI client if needed
                        if llm_client.provider == "openai":
                            client = llm_client.client
                        else:
                            # For Gemini, we still need OpenAI for some operations (like embeddings)
                            client = OpenAI(api_key=openai_api_key) if openai_api_key else None
                        
                        # Set up search functions (same as regular endpoint)
                        def document_search_func(query: str, file_ids: list = None):
                            if not request.file_ids and not file_ids:
                                return "No documents available for search."
                            search_file_ids = file_ids or request.file_ids or []
                            db_files = []
                            for file_id in search_file_ids:
                                db_file = crud.get_file(db, file_id=file_id)
                                if db_file:
                                    db_files.append(db_file)
                            if not db_files:
                                return "No matching documents found."
                            from .file_extraction import extract_files_content
                            try:
                                extracted_content, _ = extract_files_content(db_files)
                                if extracted_content:
                                    query_lower = query.lower()
                                    if query_lower in extracted_content.lower():
                                        idx = extracted_content.lower().find(query_lower)
                                        start = max(0, idx - 200)
                                        end = min(len(extracted_content), idx + len(query) + 200)
                                        return f"Found in documents:\n{extracted_content[start:end]}"
                                    return f"Document content available. Query '{query}' not explicitly found, but here's the document content:\n{extracted_content[:1000]}"
                                return "Could not extract content from documents."
                            except Exception as e:
                                return f"Error searching documents: {str(e)}"
                        
                        def knowledge_base_search_func(query: str):
                            """Semantic search across organization's document corpus using vector embeddings"""
                            from .vector_store import search_documents
                            
                            try:
                                # Use semantic search with vector embeddings
                                results = search_documents(
                                    organization_id=request.organization_id,
                                    query=query,
                                    n_results=5
                                )
                                
                                if not results:
                                    return "No relevant documents found in the organization's knowledge base."
                                
                                # Format results for LLM
                                formatted_results = []
                                for result in results:
                                    chunk = result.get('chunk', '')
                                    metadata = result.get('metadata', {})
                                    filename = metadata.get('filename', 'Unknown')
                                    similarity = result.get('similarity', 0)
                                    
                                    # Only include results with reasonable similarity
                                    if similarity > 0.3:  # Threshold for relevance
                                        formatted_results.append(
                                            f"--- From {filename} (relevance: {similarity:.2f}) ---\n{chunk}\n"
                                        )
                                
                                if formatted_results:
                                    return "Found relevant information in knowledge base:\n\n" + "\n".join(formatted_results)
                                else:
                                    return "No highly relevant documents found. The knowledge base may not contain information related to your query."
                                    
                            except Exception as e:
                                # Fallback to simple text search if vector store fails
                                print(f"Vector store search failed, falling back to text search: {e}")
                                org_files = crud.get_files_by_user(db, user_id=user_id, organization_id=request.organization_id, skip=0, limit=100)
                                if not org_files:
                                    return "No documents in organization knowledge base."
                                from .file_extraction import extract_files_content
                                try:
                                    extracted_content, _ = extract_files_content(org_files)
                                    if extracted_content:
                                        query_lower = query.lower()
                                        query_words = query_lower.split()
                                        content_lower = extracted_content.lower()
                                        matches = [word for word in query_words if word in content_lower]
                                        if matches:
                                            idx = content_lower.find(matches[0])
                                            start = max(0, idx - 300)
                                            end = min(len(extracted_content), idx + 500)
                                            return f"Found in knowledge base:\n{extracted_content[start:end]}"
                                        return f"Knowledge base content available. Query '{query}' not explicitly found, but here's relevant content:\n{extracted_content[:1000]}"
                                    return "Could not extract content from knowledge base."
                                except Exception as fallback_error:
                                    return f"Error searching knowledge base: {str(fallback_error)}"
                        
                        set_document_search_func(document_search_func)
                        set_knowledge_base_search_func(knowledge_base_search_func)
                        
                        # Initialize agent registry and crew
                        config_dir = Path(__file__).parent / "agents" / "config"
                        # Pass LLMClient to registry with default model
                        # Agents can override this in their YAML configs for cost/performance optimization
                        default_model = llm_client.model if isinstance(llm_client, LLMClient) else None
                        registry = AgentRegistry(config_dir, llm_client, tool_registry={}, default_model=default_model)

                        # Register custom agentic agents for this user/org
                        custom_agentic_agents = crud.get_custom_agents_for_crew(db, user_id, request.organization_id)
                        context_custom_agents_info = None
                        for ca in custom_agentic_agents:
                            registry.register_custom_agent(ca)

                        # Determine agent selection: per-query override > thread default > all agents
                        selected_agent_ids = request.agent_ids
                        if selected_agent_ids is None and thread.selected_agent_ids is not None:
                            selected_agent_ids = thread.selected_agent_ids

                        # Apply agent selection filter
                        if selected_agent_ids is not None:
                            registry = registry.get_filtered_registry(selected_agent_ids)

                        # Update director's delegation list to match available agents
                        director = registry.get_director()
                        if director:
                            available_ids = [aid for aid in registry.agents.keys() if aid != "director"]
                            director.config.can_delegate_to = available_ids

                            # Inject custom agent descriptions into context so director knows about them
                            if custom_agentic_agents:
                                custom_desc = "\n".join([
                                    f"  - **{ca.name}** (custom_{ca.id}): {ca.role or ca.description or ''}"
                                    for ca in custom_agentic_agents
                                    if f"custom_{ca.id}" in registry.agents
                                ])
                                if custom_desc:
                                    context_custom_agents_info = custom_desc

                        crew = Crew(registry)

                        # Calculate question_count (number of clarification rounds in this query chain)
                        question_count = 0
                        if previous_queries:
                            # Check if the most recent query was a clarification (has reask_of_query_id)
                            # Count how many times we've reasked in this chain
                            for query in reversed(previous_queries):
                                if hasattr(query, 'reask_of_query_id') and query.reask_of_query_id is not None:
                                    question_count += 1
                                else:
                                    # Stop at the first non-reask query (the original question)
                                    break

                        # Build parent analysis context for deep-dive follow-ups
                        parent_analysis_context = None
                        if request.followup_of_query_id:
                            parent_query = crud.get_chat_query(db, request.followup_of_query_id)
                            if parent_query and parent_query.execution_trace:
                                from .agents.trace_summarizer import summarize_execution_trace
                                trace_summary = summarize_execution_trace(
                                    parent_query.execution_trace, max_length=5000
                                )
                                parent_analysis_context = (
                                    f"PARENT QUESTION: {parent_query.message}\n"
                                    f"PARENT ANSWER SUMMARY: {(parent_query.response or '')[:2000]}\n"
                                    f"PARENT ANALYSIS PROCESS:\n{trace_summary}"
                                )

                        # Execute through crew with event callback
                        context = {
                            "organization": org_context,
                            "conversation_history": conversation_context,
                            "file_content": file_content,
                            "thread_preferences": thread_metadata,  # Thread-level preferences (budget-conscious vs outcome-conscious)
                            "answer_mode": answer_mode.value,  # Verbosity level for this query
                            "question_count": question_count,  # Number of clarification rounds in this chain
                            "custom_agents_info": context_custom_agents_info,  # Custom agent descriptions for director
                            "parent_analysis_context": parent_analysis_context,  # Deep-dive follow-up context from parent query
                        }

                        # Debug logging for answer mode
                        agent_ids_used = list(registry.agents.keys())
                        print(f"[ANSWER_MODE] Executing query with answer_mode={answer_mode.value}, agents={agent_ids_used}")

                        response_text, final_trace, llm_call_records = crew.execute(request.message, context, event_callback=event_callback)
                        
                        # Calculate total execution time
                        total_execution_time = time.time() - execution_start_time
                        
                        # Calculate total agent thinking time and tool usage time from trace
                        total_agent_time = 0.0
                        total_tool_time = 0.0
                        cached_tool_calls = 0
                        total_tool_calls = 0
                        for node in final_trace.nodes:
                            if node.type == "agent" and node.metadata and "execution_time" in node.metadata:
                                total_agent_time += node.metadata.get("execution_time", 0.0)
                            elif node.type == "tool" and node.metadata and "execution_time" in node.metadata:
                                total_tool_time += node.metadata.get("execution_time", 0.0)
                                total_tool_calls += 1
                                if node.metadata.get("cache_hit"):
                                    cached_tool_calls += 1
                        
                        # Final trace update (with response node)
                        trace_dict = final_trace.to_dict()
                        event_queue.put_nowait({
                            "type": "trace_update",
                            "data": {"trace": trace_dict}
                        })
                        
                        # Parse response
                        parsed = parse_response(response_text)
                        cleaned_response = parsed[0]
                        is_clarification = parsed[1]
                        clarification_questions = parsed[2] if len(parsed) > 2 else None
                        citations = parsed[3] if len(parsed) > 3 else None
                        recommendations = parsed[4] if len(parsed) > 4 else None
                        visualizations = parsed[5] if len(parsed) > 5 else None
                        final_response = cleaned_response

                        # Debug logging for response analysis
                        word_count = len(cleaned_response.split())
                        print(f"[ANSWER_MODE] Response generated with {word_count} words (mode={answer_mode.value}, visualizations={len(visualizations) if visualizations else 0}, citations={len(citations) if citations else 0})")

                        # Generate follow-up questions (only for non-clarification responses)
                        followup_questions_data = None
                        if not is_clarification and cleaned_response:
                            try:
                                from .agents.tools.followup_generator import generate_followup_questions
                                from .agents.trace_summarizer import summarize_execution_trace

                                execution_summary = summarize_execution_trace(trace_dict)

                                followup_questions_data = generate_followup_questions(
                                    original_question=request.message,
                                    answer=cleaned_response,
                                    org_context=org_context,
                                    execution_summary=execution_summary
                                )
                            except Exception as e:
                                print(f"Error generating follow-up questions: {e}")
                                followup_questions_data = None

                        # Build content_structure for tabbed display
                        content_structure = None
                        if visualizations or citations:
                            content_structure = {
                                "summary": cleaned_response
                            }

                            # Add visualizations if present
                            if visualizations:
                                print(f"[CONTENT_STRUCTURE] Building visualizations for content_structure: {len(visualizations)} visualizations found")
                                content_structure["visualizations"] = [
                                    {
                                        "type": viz.get("chart_type", "bar"),
                                        "data": viz.get("echarts_config"),
                                        "caption": viz.get("title")
                                    }
                                    for viz in visualizations
                                ]

                            # Add citations as references if present
                            if citations:
                                print(f"[CONTENT_STRUCTURE] Adding {len(citations)} citations to content_structure")
                                content_structure["references"] = citations
                        else:
                            print(f"[CONTENT_STRUCTURE] No visualizations or citations found - content_structure will be None")

                        # Link visualizations to visualizer tool nodes in the trace
                        if visualizations and len(visualizations) > 0:
                            # Find all visualizer tool nodes in the trace
                            visualizer_nodes = [node for node in final_trace.nodes if node.type == "tool" and node.name == "visualizer"]
                            # Link the first visualization to the first visualizer node (simple 1:1 mapping)
                            # In the future, we could match by title or other metadata
                            for i, viz in enumerate(visualizations):
                                if i < len(visualizer_nodes):
                                    viz_node = visualizer_nodes[i]
                                    if viz.get("echarts_config"):
                                        if not viz_node.metadata:
                                            viz_node.metadata = {}
                                        viz_node.metadata["echarts_config"] = viz["echarts_config"]
                                        viz_node.metadata["visualization_title"] = viz.get("title", "Visualization")
                                        viz_node.metadata["chart_type"] = viz.get("chart_type", "unknown")
                            
                            # Update trace dict with the linked visualizations
                            trace_dict = final_trace.to_dict()
                            
                            # Emit updated trace with visualization configs linked
                            event_queue.put_nowait({
                                "type": "trace_update",
                                "data": {"trace": trace_dict}
                            })
                        
                        # Update query in database with final results
                        # (query was already created at the start of execution)
                        execution_times_data = {
                            "total_time": total_execution_time,
                            "agent_time": total_agent_time,
                            "tool_time": total_tool_time,
                            "cached_tool_calls": cached_tool_calls,
                            "total_tool_calls": total_tool_calls,
                        }

                        # Add progress_updates to trace metadata for persistence
                        if progress_updates:
                            if "metadata" not in trace_dict:
                                trace_dict["metadata"] = {}
                            trace_dict["metadata"]["progress_updates"] = progress_updates

                        # Add LLM prompt logs to trace metadata for traceability
                        if llm_call_records:
                            if "metadata" not in trace_dict:
                                trace_dict["metadata"] = {}
                            trace_dict["metadata"]["llm_prompts"] = [r.to_dict() for r in llm_call_records]

                        db_query = crud.update_chat_query(
                            db, db_query.id,
                            response=cleaned_response,
                            execution_trace=trace_dict,
                            execution_times=execution_times_data,
                            content_structure=content_structure,
                            followup_questions=followup_questions_data,
                            agent_ids_used=agent_ids_used,
                        )
                        
                        # Process generated images from execution trace
                        crud.process_generated_images_from_trace(
                            db, db_query.id, trace_dict, user_id, request.organization_id
                        )
                        
                        # Auto-generate thread title from first query if thread has no title
                        thread = crud.get_thread(db, thread_id=thread_id)
                        if thread and not thread.title:
                            # Check if this is the first query in the thread
                            all_queries = crud.get_chat_queries_by_thread(db, thread_id=thread_id, skip=0, limit=2)
                            if len(all_queries) == 1:  # This is the first query
                                try:
                                    # Generate a concise title from the query
                                    title_prompt = f"""Generate a concise, professional thread title (3-6 words max) based on this user query. The title should summarize the main topic or question.

User Query: "{request.message}"

Respond with ONLY the title, nothing else. Examples:
- "What are ways I can grow my business" -> "Business Growth Opportunities"
- "How to improve customer retention" -> "Customer Retention Strategies"
- "Budget planning for Q4" -> "Q4 Budget Planning"

Title:"""
                                    
                                    title_response = client.chat.completions.create(
                                        model="gpt-4o-mini",  # Use cheaper model for title generation
                                        messages=[
                                            {"role": "system", "content": "You are a helpful assistant that generates concise, professional titles."},
                                            {"role": "user", "content": title_prompt}
                                        ],
                                        max_tokens=20,
                                        temperature=0.3
                                    )
                                    generated_title = title_response.choices[0].message.content.strip()
                                    # Clean up the title (remove quotes if present, limit length)
                                    generated_title = generated_title.strip('"\'')
                                    if len(generated_title) > 60:
                                        generated_title = generated_title[:57] + "..."
                                    if generated_title:
                                        crud.update_thread(db, thread_id, title=generated_title)
                                except Exception as e:
                                    # If title generation fails, just continue without a title
                                    print(f"Error generating thread title: {e}")
                        
                        # Update thread's updated_at timestamp by touching it (only if we didn't set a title)
                        # The updated_at is auto-updated by SQLAlchemy on commit, so we just need to ensure the thread is refreshed
                        if thread:
                            db.refresh(thread)
                        
                        # Convert citations to schema format
                        citation_schemas = None
                        if citations:
                            citation_schemas = [schemas.Citation(**c) for c in citations if isinstance(c, dict)]
                        
                        # Emit final response
                        event_queue.put_nowait({
                            "type": "response",
                            "data": {
                                "response": cleaned_response,
                                "query_id": db_query.id,
                                "is_clarification": is_clarification,
                                "clarification_questions": clarification_questions,
                                "execution_trace": trace_dict,
                                "citations": [c.dict() for c in citation_schemas] if citation_schemas else None,
                                "recommendations": recommendations,
                                "visualizations": visualizations,
                                "content_structure": content_structure,
                                "followup_questions": followup_questions_data,
                                "execution_times": {
                                    "total_time": total_execution_time,
                                    "agent_time": total_agent_time,
                                    "tool_time": total_tool_time,
                                    "cached_tool_calls": cached_tool_calls,
                                    "total_tool_calls": total_tool_calls,
                                }
                            }
                        })
                        event_queue.put_nowait({"type": "done", "data": {}})
                        
                    finally:
                        for var, value in original_proxies.items():
                            os.environ[var] = value
                else:
                    error_occurred = "Streaming only supported for agentic mode"
                    event_queue.put_nowait({"type": "error", "data": {"message": error_occurred}})
                    
            except Exception as e:
                error_occurred = str(e)
                event_queue.put_nowait({"type": "error", "data": {"message": error_occurred}})
                import traceback
                traceback.print_exc()

                # Persist error to database if query was created
                if db_query:
                    try:
                        crud.update_chat_query(
                            db, db_query.id,
                            error=error_occurred
                        )
                    except Exception as update_error:
                        print(f"Error updating query with error message: {update_error}")
        
        # Run agent execution in executor to avoid blocking (agent execution is sync)
        import concurrent.futures
        import threading
        executor = concurrent.futures.ThreadPoolExecutor()
        task = executor.submit(run_agent_execution_sync)
        
        # Stream events - prioritize trace updates for real-time display
        while not done:
            try:
                # Check for events with shorter timeout to be more responsive
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
                    continue
                
                # Send event immediately
                yield f"data: {json.dumps(event)}\n\n"
                
                # Flush immediately for trace updates
                if event.get("type") == "trace_update":
                    # Force immediate send
                    pass
                
                if event.get("type") == "done":
                    done = True
                    break
                if event.get("type") == "error":
                    done = True
                    break
                    
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"
                break
        
        # Wait for task to complete
        try:
            await task
        except:
            pass
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

# LLM endpoint with database integration
@app.post("/api/llm/chat", response_model=schemas.ChatResponse)
async def chat_with_llm(
    fastapi_request: Request,
    request: schemas.ChatRequest,
    db: Session = Depends(get_db)
):
    try:
        # Support API key authentication OR user_id in request body (backward compatibility)
        user_id = None
        authenticated_via = None
        
        # Try API key authentication first
        from .api_auth import get_current_user
        try:
            user = await get_current_user(fastapi_request, None, None, db)
            user_id = user.id
            authenticated_via = "api_key_or_bearer"
        except HTTPException:
            # Fall back to user_id in request body (backward compatibility)
            if request.user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required. Provide either X-API-Key header, Authorization Bearer token, or user_id in request body."
                )
            user = crud.get_user(db, user_id=request.user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            user_id = request.user_id
            authenticated_via = "user_id_body"
            # Track usage for backward-compatible requests
            from . import models
            usage_log = models.UsageLog(
                user_id=user_id,
                endpoint="/api/llm/chat",
                method="POST",
                authenticated_via=authenticated_via
            )
            db.add(usage_log)
            db.commit()
        
        # Require organization_id
        if request.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization ID required. Please select an organization."
            )
        
        # Verify organization exists and user has access
        org = crud.get_organization(db, org_id=request.organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Sending a query is a mutation — require write access
        has_access = crud.check_org_permission(db, request.organization_id, user_id, require_write=True)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have write access to this organization"
            )
        
        # Create thread if thread_id is not provided
        thread_id = request.thread_id
        if thread_id is None:
            thread_create = schemas.ThreadCreate(
                organization_id=request.organization_id,
                title=None  # Can be set later or auto-generated from first message
            )
            db_thread = crud.create_thread(db, thread_create, user_id)
            thread_id = db_thread.id
        
        # Verify thread exists and belongs to user and organization
        thread = crud.get_thread(db, thread_id=thread_id)
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found"
            )
        if thread.user_id != user_id or thread.organization_id != request.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Thread does not belong to this user and organization"
            )
        
        # Gather organization context (including metadata)
        org_metadata = org.org_metadata if org.org_metadata else {}
        org_context = build_organization_context(org, org_metadata)
        
        # Gather conversation context (previous messages in thread)
        previous_queries = crud.get_chat_queries_by_thread(db, thread_id=thread_id, skip=0, limit=20)
        conversation_context = build_conversation_context(previous_queries)
        
        # Get thread preferences
        thread_metadata = thread.thread_metadata if thread.thread_metadata else {}

        # Determine answer mode (per-question override or thread default)
        from .models import AnswerMode
        answer_mode_str = request.answer_mode or (thread.default_answer_mode.value if hasattr(thread, 'default_answer_mode') and thread.default_answer_mode else "light")
        # Validate answer mode
        try:
            answer_mode = AnswerMode(answer_mode_str)
        except ValueError:
            answer_mode = AnswerMode.LIGHT  # Fallback to default

        # Handle file attachments - use OpenAI Files API for PDFs, extract text for other formats
        file_content = None
        openai_file_ids = []
        if request.file_ids:
            db_files = []
            for file_id in request.file_ids:
                db_file = crud.get_file(db, file_id=file_id)
                if db_file:
                    # Verify user has access to the file
                    if db_file.user_id != user_id:
                        has_file_access = crud.check_org_permission(db, db_file.organization_id, user_id, require_write=False)
                        if not has_file_access:
                            continue  # Skip files user doesn't have access to
                    db_files.append(db_file)
            
            if db_files:
                # Separate PDFs from other files
                pdf_files = []
                other_files = []
                for db_file in db_files:
                    file_ext = Path(db_file.original_filename).suffix.lower()
                    if file_ext == '.pdf':
                        pdf_files.append(db_file)
                    else:
                        other_files.append(db_file)
                
                # Extract text from non-PDF files first (doesn't need OpenAI client)
                if other_files:
                    from .file_extraction import extract_files_content
                    try:
                        extracted_content, extraction_errors = extract_files_content(other_files)
                        if extracted_content:
                            file_content = extracted_content
                        if extraction_errors:
                            print(f"File extraction errors: {extraction_errors}")
                    except Exception as e:
                        print(f"File extraction exception: {str(e)}")
                        import traceback
                        traceback.print_exc()
        
        # Build prompt based on chat mode (before we upload PDFs, so we can modify messages after)
        chat_mode = request.chat_mode or "agentic"  # Default to agentic mode
        
        # Use agentic framework for agentic mode
        if chat_mode == "agentic":
            # Initialize OpenAI client
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="OpenAI API key not configured"
                )
            
            # Handle proxy vars
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
            original_proxies = {}
            for var in proxy_vars:
                if var in os.environ:
                    original_proxies[var] = os.environ.pop(var)
            
            try:
                # Use LLMClient factory to support both OpenAI and Gemini
                from .llm_client import get_llm_client, LLMClient
                model = os.getenv("LLM_MODEL", "gemini-3-flash-preview")
                llm_client = get_llm_client(model=model)
                # For backward compatibility, also create OpenAI client if needed
                if llm_client.provider == "openai":
                    client = llm_client.client
                else:
                    # For Gemini, we still need OpenAI for some operations (like embeddings)
                    client = OpenAI(api_key=openai_api_key) if openai_api_key else None
                
                # Set up document and knowledge base search functions
                def document_search_func(query: str, file_ids: list = None):
                    """Search in uploaded documents."""
                    if not request.file_ids and not file_ids:
                        return "No documents available for search."
                    
                    search_file_ids = file_ids or request.file_ids or []
                    db_files = []
                    for file_id in search_file_ids:
                        db_file = crud.get_file(db, file_id=file_id)
                        if db_file:
                            db_files.append(db_file)
                    
                    if not db_files:
                        return "No matching documents found."
                    
                    # Extract content from files
                    from .file_extraction import extract_files_content
                    try:
                        extracted_content, _ = extract_files_content(db_files)
                        if extracted_content:
                            # Simple text search in extracted content
                            query_lower = query.lower()
                            if query_lower in extracted_content.lower():
                                # Return relevant excerpt
                                idx = extracted_content.lower().find(query_lower)
                                start = max(0, idx - 200)
                                end = min(len(extracted_content), idx + len(query) + 200)
                                return f"Found in documents:\n{extracted_content[start:end]}"
                            return f"Document content available. Query '{query}' not explicitly found, but here's the document content:\n{extracted_content[:1000]}"
                        return "Could not extract content from documents."
                    except Exception as e:
                        return f"Error searching documents: {str(e)}"
                
                def knowledge_base_search_func(query: str):
                    """Semantic search across organization's document corpus using vector embeddings"""
                    from .vector_store import search_documents
                    
                    try:
                        # Use semantic search with vector embeddings
                        results = search_documents(
                            organization_id=request.organization_id,
                            query=query,
                            n_results=5
                        )
                        
                        if not results:
                            return "No relevant documents found in the organization's knowledge base."
                        
                        # Format results for LLM
                        formatted_results = []
                        for result in results:
                            chunk = result.get('chunk', '')
                            metadata = result.get('metadata', {})
                            filename = metadata.get('filename', 'Unknown')
                            similarity = result.get('similarity', 0)
                            
                            # Only include results with reasonable similarity
                            if similarity > 0.3:  # Threshold for relevance
                                formatted_results.append(
                                    f"--- From {filename} (relevance: {similarity:.2f}) ---\n{chunk}\n"
                                )
                        
                        if formatted_results:
                            return "Found relevant information in knowledge base:\n\n" + "\n".join(formatted_results)
                        else:
                            return "No highly relevant documents found. The knowledge base may not contain information related to your query."
                            
                    except Exception as e:
                        # Fallback to simple text search if vector store fails
                        print(f"Vector store search failed, falling back to text search: {e}")
                        org_files = crud.get_files_by_user(db, user_id=user_id, organization_id=request.organization_id, skip=0, limit=100)
                        if not org_files:
                            return "No documents in organization knowledge base."
                        from .file_extraction import extract_files_content
                        try:
                            extracted_content, _ = extract_files_content(org_files)
                            if extracted_content:
                                query_lower = query.lower()
                                query_words = query_lower.split()
                                content_lower = extracted_content.lower()
                                matches = [word for word in query_words if word in content_lower]
                                if matches:
                                    idx = content_lower.find(matches[0])
                                    start = max(0, idx - 300)
                                    end = min(len(extracted_content), idx + 500)
                                    return f"Found in knowledge base:\n{extracted_content[start:end]}"
                                return f"Knowledge base content available. Query '{query}' not explicitly found, but here's relevant content:\n{extracted_content[:1000]}"
                            return "Could not extract content from knowledge base."
                        except Exception as fallback_error:
                            return f"Error searching knowledge base: {str(fallback_error)}"
                
                set_document_search_func(document_search_func)
                set_knowledge_base_search_func(knowledge_base_search_func)
                
                # Initialize agent registry and crew
                config_dir = Path(__file__).parent / "agents" / "config"
                # Pass LLMClient to registry with default model
                # Agents can override this in their YAML configs for cost/performance optimization
                default_model = llm_client.model if isinstance(llm_client, LLMClient) else None
                registry = AgentRegistry(config_dir, llm_client, tool_registry={}, default_model=default_model)

                # Register custom agentic agents for this user/org
                custom_agentic_agents = crud.get_custom_agents_for_crew(db, user_id, request.organization_id)
                context_custom_agents_info = None
                for ca in custom_agentic_agents:
                    registry.register_custom_agent(ca)

                # Determine agent selection: per-query override > thread default > all agents
                selected_agent_ids = request.agent_ids
                if selected_agent_ids is None and thread.selected_agent_ids is not None:
                    selected_agent_ids = thread.selected_agent_ids

                # Apply agent selection filter
                if selected_agent_ids is not None:
                    registry = registry.get_filtered_registry(selected_agent_ids)

                # Update director's delegation list to match available agents
                director = registry.get_director()
                if director:
                    available_ids = [aid for aid in registry.agents.keys() if aid != "director"]
                    director.config.can_delegate_to = available_ids

                    # Inject custom agent descriptions so director knows about them
                    if custom_agentic_agents:
                        custom_desc = "\n".join([
                            f"  - **{ca.name}** (custom_{ca.id}): {ca.role or ca.description or ''}"
                            for ca in custom_agentic_agents
                            if f"custom_{ca.id}" in registry.agents
                        ])
                        if custom_desc:
                            context_custom_agents_info = custom_desc

                crew = Crew(registry)

                # Execute through crew with timing
                import time
                execution_start_time = time.time()

                agent_ids_used = list(registry.agents.keys())

                # Build parent analysis context for deep-dive follow-ups (non-streaming)
                parent_analysis_context_ns = None
                if request.followup_of_query_id:
                    parent_query_ns = crud.get_chat_query(db, request.followup_of_query_id)
                    if parent_query_ns and parent_query_ns.execution_trace:
                        from .agents.trace_summarizer import summarize_execution_trace
                        trace_summary_ns = summarize_execution_trace(
                            parent_query_ns.execution_trace, max_length=5000
                        )
                        parent_analysis_context_ns = (
                            f"PARENT QUESTION: {parent_query_ns.message}\n"
                            f"PARENT ANSWER SUMMARY: {(parent_query_ns.response or '')[:2000]}\n"
                            f"PARENT ANALYSIS PROCESS:\n{trace_summary_ns}"
                        )

                context = {
                    "organization": org_context,
                    "conversation_history": conversation_context,
                    "file_content": file_content,
                    "thread_preferences": thread_metadata,  # Thread-level preferences (budget-conscious vs outcome-conscious)
                    "answer_mode": answer_mode.value,  # Verbosity level for this query
                    "custom_agents_info": context_custom_agents_info,  # Custom agent descriptions for director
                    "parent_analysis_context": parent_analysis_context_ns,  # Deep-dive follow-up context
                }

                # Debug logging for answer mode
                print(f"[ANSWER_MODE] Executing query (non-streaming) with answer_mode={answer_mode.value}, agents={agent_ids_used}")

                response_text, execution_trace, llm_call_records = crew.execute(request.message, context)
                
                # Calculate total execution time
                total_execution_time = time.time() - execution_start_time
                
                # Calculate total agent thinking time and tool usage time from trace
                total_agent_time = 0.0
                total_tool_time = 0.0
                cached_tool_calls = 0
                total_tool_calls = 0
                for node in execution_trace.nodes:
                    if node.type == "agent" and node.metadata and "execution_time" in node.metadata:
                        total_agent_time += node.metadata.get("execution_time", 0.0)
                    elif node.type == "tool" and node.metadata and "execution_time" in node.metadata:
                        total_tool_time += node.metadata.get("execution_time", 0.0)
                        total_tool_calls += 1
                        if node.metadata.get("cache_hit"):
                            cached_tool_calls += 1
                
                # Convert execution trace to schema format
                trace_dict = execution_trace.to_dict()
                print(f"Execution trace created: {len(trace_dict['nodes'])} nodes, {len(trace_dict['edges'])} edges")

                # Add LLM prompt logs to trace metadata for traceability
                if llm_call_records:
                    if "metadata" not in trace_dict:
                        trace_dict["metadata"] = {}
                    trace_dict["metadata"]["llm_prompts"] = [r.to_dict() for r in llm_call_records]
                execution_trace_schema = schemas.ExecutionTrace(
                    nodes=[schemas.AgentNode(**node) for node in trace_dict["nodes"]],
                    edges=[schemas.AgentEdge(**edge) for edge in trace_dict["edges"]],
                    metadata=trace_dict.get("metadata")  # Include metadata with progress_updates
                )
                
                # Parse response to identify clarifications
                parsed = parse_response(response_text)
                cleaned_response = parsed[0]
                is_clarification = parsed[1]
                clarification_questions = parsed[2] if len(parsed) > 2 else None
                citations = parsed[3] if len(parsed) > 3 else None
                recommendations = parsed[4] if len(parsed) > 4 else None
                visualizations = parsed[5] if len(parsed) > 5 else None

                # Debug logging for response analysis
                word_count = len(cleaned_response.split())
                print(f"[ANSWER_MODE] Response generated (non-streaming) with {word_count} words (mode={answer_mode.value}, visualizations={len(visualizations) if visualizations else 0}, citations={len(citations) if citations else 0})")

                # Build content_structure for tabbed display
                content_structure = None
                if visualizations or citations:
                    content_structure = {
                        "summary": cleaned_response
                    }

                    # Add visualizations if present
                    if visualizations:
                        print(f"[CONTENT_STRUCTURE] Building visualizations (non-streaming) for content_structure: {len(visualizations)} visualizations found")
                        content_structure["visualizations"] = [
                            {
                                "type": viz.get("chart_type", "bar"),
                                "data": viz.get("echarts_config"),
                                "caption": viz.get("title")
                            }
                            for viz in visualizations
                        ]

                    # Add citations as references if present
                    if citations:
                        print(f"[CONTENT_STRUCTURE] Adding {len(citations)} citations (non-streaming) to content_structure")
                        content_structure["references"] = citations
                else:
                    print(f"[CONTENT_STRUCTURE] No visualizations or citations found (non-streaming) - content_structure will be None")

                # Save query to database with execution trace
                query_create = schemas.ChatQueryCreate(
                    thread_id=thread_id,
                    user_id=user_id,
                    organization_id=request.organization_id,
                    message=request.message,
                    answer_mode=answer_mode.value
                )
                execution_times_data = {
                    "total_time": total_execution_time,
                    "agent_time": total_agent_time,
                    "tool_time": total_tool_time,
                    "cached_tool_calls": cached_tool_calls,
                    "total_tool_calls": total_tool_calls,
                }
                db_query = crud.create_chat_query(
                    db, query_create, cleaned_response,
                    execution_trace=trace_dict,
                    execution_times=execution_times_data,
                    content_structure=content_structure,
                    agent_ids_used=agent_ids_used,
                )

                # Associate files with query if provided
                if request.file_ids:
                    crud.associate_files_with_query(db, db_query.id, request.file_ids)
                
                # Process generated images from execution trace
                crud.process_generated_images_from_trace(
                    db, db_query.id, trace_dict, user_id, request.organization_id
                )
                
                # Update thread's updated_at timestamp
                # Refresh thread to update updated_at timestamp
                thread = crud.get_thread(db, thread_id=thread_id)
                if thread:
                    db.refresh(thread)
                
                # Convert citations to schema format
                citation_schemas = None
                if citations:
                    citation_schemas = [schemas.Citation(**c) for c in citations if isinstance(c, dict)]
                
                return schemas.ChatResponse(
                    response=cleaned_response,
                    query_id=db_query.id,
                    is_clarification=is_clarification,
                    clarification_questions=clarification_questions,
                    execution_trace=execution_trace_schema,
                    citations=citation_schemas,
                    recommendations=recommendations
                )
            finally:
                # Restore proxy env vars if they were set
                for var, value in original_proxies.items():
                    os.environ[var] = value
        
        # Check if this is a custom agent (format: "custom_123")
        elif chat_mode.startswith("custom_"):
            try:
                custom_agent_id = int(chat_mode.split("_")[1])
                custom_agent = crud.get_custom_agent(db, custom_agent_id, user_id)
                if not custom_agent:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Custom agent not found"
                    )
                
                # Build custom prompt using the custom agent's system prompt
                content_parts = [f"""ORGANIZATION CONTEXT:
{org_context}

CONVERSATION HISTORY:
{conversation_context}"""]
                
                if file_content:
                    if file_content.startswith("[Error:"):
                        content_parts.append(f"""
IMPORTANT: The user mentioned attached files, but there was an error extracting the content:
{file_content}

Please inform the user about this issue and ask them to provide the information in another format.""")
                    else:
                        content_parts.append(f"""
═══════════════════════════════════════════════════════════════
ATTACHED FILE(S) CONTENT (EXTRACTED TEXT):
═══════════════════════════════════════════════════════════════
The user has attached one or more files with their query. The extracted text content from these files is provided below. You MUST analyze this content and use it to answer their question.

{file_content}

═══════════════════════════════════════════════════════════════
END OF ATTACHED FILE CONTENT
═══════════════════════════════════════════════════════════════""")
                
                content_parts.append(f"""
CURRENT QUERY:
{request.message}

INSTRUCTIONS:
- The user's query is above. {'**IMPORTANT: The user has attached file(s) with this query. The file content has been extracted and provided above. You MUST analyze the attached file content and use it to answer their question.**' if file_content and not file_content.startswith('[Error:') else ''}
- Follow the system instructions provided to you.
- Use the organization context, conversation history, {'and the attached file content' if file_content and not file_content.startswith('[Error:') else ''} to inform your response.""")
                
                messages = [
                    {"role": "system", "content": custom_agent.system_prompt},
                    {"role": "user", "content": "\n".join(content_parts)}
                ]
            except (ValueError, IndexError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid custom agent ID format"
                )
        # Route to appropriate prompt builder based on mode
        elif chat_mode == "generic":
            messages = build_generic_prompt(request.message, org_context, conversation_context, file_content)
        elif chat_mode == "analytical":
            messages = build_analytical_prompt(request.message, org_context, conversation_context, file_content)
        elif chat_mode == "creative":
            messages = build_creative_prompt(request.message, org_context, conversation_context, file_content)
        elif chat_mode == "executive":
            messages = build_executive_prompt(request.message, org_context, conversation_context, file_content)
        else:  # Default to strategy
            messages = build_strategy_prompt(request.message, org_context, conversation_context, file_content)
        
        # Call OpenAI API
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI API key not configured"
            )
        
        # Initialize OpenAI client
        # Handle potential proxy environment variables that might cause issues
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
        original_proxies = {}
        for var in proxy_vars:
            if var in os.environ:
                original_proxies[var] = os.environ.pop(var)
        
        try:
            client = OpenAI(api_key=openai_api_key)
            
            # Upload PDFs to OpenAI Files API if we have PDF files
            if request.file_ids and db_files:
                pdf_files = [f for f in db_files if Path(f.original_filename).suffix.lower() == '.pdf']
                for db_file in pdf_files:
                    try:
                        from .storage import get_file
                        from .openai_files import upload_file_to_openai
                        file_content_bytes = get_file(db_file.file_path)
                        openai_file_id = upload_file_to_openai(
                            client, 
                            file_content_bytes, 
                            db_file.original_filename,
                            purpose="user_data"
                        )
                        openai_file_ids.append(openai_file_id)
                        print(f"Uploaded PDF {db_file.original_filename} to OpenAI, file_id: {openai_file_id}")
                    except Exception as e:
                        print(f"Error uploading PDF {db_file.original_filename} to OpenAI: {str(e)}")
                        import traceback
                        traceback.print_exc()
            
            # Get model from environment or use default
            # For PDF support, we need a vision-capable model like gpt-4o
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
            
            # Add file attachments to messages if we have PDFs uploaded to OpenAI
            # According to OpenAI docs, files are attached to message content as an array
            if openai_file_ids and messages:
                # Find the user message (last message is typically the user's query)
                user_message = None
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        user_message = msg
                        break
                
                if user_message:
                    # Convert string content to array format with text and file attachments
                    original_content = user_message["content"]
                    user_message["content"] = [
                        {
                            "type": "text",
                            "text": original_content
                        }
                    ]
                    
                    # Add file attachments
                    # Format: {"type": "file", "file": {"file_id": "..."}}
                    for file_id in openai_file_ids:
                        user_message["content"].append({
                            "type": "file",
                            "file": {
                                "file_id": file_id
                            }
                        })
                    
                    print(f"Added {len(openai_file_ids)} PDF file attachment(s) to user message")
            
            # Prepare the request
            request_params = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            llm_response = client.chat.completions.create(**request_params)
            response_text = llm_response.choices[0].message.content
        except Exception as openai_error:
            print(f"OpenAI API error: {openai_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get response from OpenAI: {str(openai_error)}"
            )
        finally:
            # Restore proxy env vars if they were set
            for var, value in original_proxies.items():
                os.environ[var] = value
        
        # Parse response to identify clarifications
        parsed = parse_response(response_text)
        cleaned_response = parsed[0]
        is_clarification = parsed[1]
        clarification_questions = parsed[2] if len(parsed) > 2 else None
        citations = parsed[3] if len(parsed) > 3 else None
        recommendations = parsed[4] if len(parsed) > 4 else None
        
        # Save query to database
        query_create = schemas.ChatQueryCreate(
            thread_id=thread_id,
            user_id=user_id,
            organization_id=request.organization_id,
            message=request.message
        )
        db_query = crud.create_chat_query(db, query_create, cleaned_response)
        
        # Associate files with query if provided
        if request.file_ids:
            crud.associate_files_with_query(db, db_query.id, request.file_ids)
        
        # Clean up OpenAI files after use (optional - files persist in OpenAI storage)
        # Uncomment if you want to delete files from OpenAI after processing
        # for file_id in openai_file_ids:
        #     try:
        #         from .openai_files import cleanup_openai_file
        #         cleanup_openai_file(client, file_id)
        #     except Exception as e:
        #         print(f"Error cleaning up OpenAI file {file_id}: {str(e)}")
        
        # Auto-generate thread title from first query if thread has no title
        thread = crud.get_thread(db, thread_id=thread_id)
        if thread and not thread.title:
            # Check if this is the first query in the thread
            all_queries = crud.get_chat_queries_by_thread(db, thread_id=thread_id, skip=0, limit=2)
            if len(all_queries) == 1:  # This is the first query
                try:
                    # Generate a concise title from the query
                    title_prompt = f"""Generate a concise, professional thread title (3-6 words max) based on this user query. The title should summarize the main topic or question.

User Query: "{request.message}"

Respond with ONLY the title, nothing else. Examples:
- "What are ways I can grow my business" -> "Business Growth Opportunities"
- "How to improve customer retention" -> "Customer Retention Strategies"
- "Budget planning for Q4" -> "Q4 Budget Planning"

Title:"""
                    
                    title_response = client.chat.completions.create(
                        model="gpt-4o-mini",  # Use cheaper model for title generation
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that generates concise, professional titles."},
                            {"role": "user", "content": title_prompt}
                        ],
                        max_tokens=20,
                        temperature=0.3
                    )
                    generated_title = title_response.choices[0].message.content.strip()
                    # Clean up the title (remove quotes if present, limit length)
                    generated_title = generated_title.strip('"\'')
                    if len(generated_title) > 60:
                        generated_title = generated_title[:57] + "..."
                    if generated_title:
                        crud.update_thread(db, thread_id, title=generated_title)
                except Exception as e:
                    # If title generation fails, just continue without a title
                    print(f"Error generating thread title: {e}")
        
        # Update thread's updated_at timestamp by refreshing it
        if thread:
            db.refresh(thread)
        
        # Convert citations to schema format
        citation_schemas = None
        if citations:
            citation_schemas = [schemas.Citation(**c) for c in citations if isinstance(c, dict)]
        
        return schemas.ChatResponse(
            response=cleaned_response,
            query_id=db_query.id,
            is_clarification=is_clarification,
            clarification_questions=clarification_questions,
            citations=citation_schemas,
            recommendations=recommendations
        )
    except HTTPException:
        raise
    except Exception as error:
        print(f"LLM error: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process LLM request: {str(error)}"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3001))
    uvicorn.run(app, host="0.0.0.0", port=port)
