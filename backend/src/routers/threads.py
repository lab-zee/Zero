from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List

from ..database import get_db
from .. import models, schemas, crud

router = APIRouter(tags=["threads"])


def _check_thread_access(db: Session, thread: models.Thread, user_id: int, require_write: bool = False) -> None:
    """Verify user can access a thread. Raises 403 if not."""
    # Thread owner always has access
    if thread.user_id == user_id:
        return
    # Otherwise check org-level permission
    if not crud.check_org_permission(db, thread.organization_id, user_id, require_write=require_write):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this thread"
        )


@router.post("/api/threads", response_model=schemas.ThreadResponse)
async def create_thread_endpoint(
    thread: schemas.ThreadCreate,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Create a new thread for a user and organization"""
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify organization exists and user has access
    org = crud.get_organization(db, org_id=thread.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Creating a thread is a mutation — require write access
    has_access = crud.check_org_permission(db, thread.organization_id, user_id, require_write=True)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have write access to this organization"
        )

    db_thread = crud.create_thread(db, thread, user_id)
    return db_thread


@router.get("/api/threads", response_model=list[schemas.ThreadResponse])
async def get_threads(
    user_id: int = Query(...),
    organization_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get threads for a user, optionally filtered by organization"""
    # If filtering by org, verify the user has read access
    if organization_id:
        if not crud.check_org_permission(db, organization_id, user_id, require_write=False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this organization"
            )
        # Anyone with org access sees all threads in the org
        threads = crud.get_threads_by_organization(db, org_id=organization_id, skip=skip, limit=limit)
    else:
        threads = crud.get_threads_by_user(db, user_id=user_id, skip=skip, limit=limit)

    # Add message count to each thread
    result = []
    for thread in threads:
        message_count = db.query(func.count(models.ChatQuery.id)).filter(
            models.ChatQuery.thread_id == thread.id
        ).scalar()
        thread_dict = {
            "id": thread.id,
            "user_id": thread.user_id,
            "organization_id": thread.organization_id,
            "title": thread.title,
            "thread_metadata": thread.thread_metadata,
            "selected_agent_ids": thread.selected_agent_ids,
            "created_at": thread.created_at,
            "updated_at": thread.updated_at,
            "message_count": message_count
        }
        result.append(schemas.ThreadResponse(**thread_dict))
    return result


@router.get("/api/threads/{thread_id}", response_model=schemas.ThreadResponse)
async def get_thread(
    thread_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    db_thread = crud.get_thread(db, thread_id=thread_id)
    if not db_thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    _check_thread_access(db, db_thread, user_id)
    return db_thread


@router.put("/api/threads/{thread_id}", response_model=schemas.ThreadResponse)
async def update_thread(
    thread_id: int,
    thread_update: schemas.ThreadUpdate,
    user_id: int = Query(..., description="User ID for permission check"),
    db: Session = Depends(get_db)
):
    """Update thread (title and/or metadata)"""
    db_thread = crud.get_thread(db, thread_id=thread_id)
    if not db_thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )

    _check_thread_access(db, db_thread, user_id, require_write=True)

    # Use model_fields_set to distinguish "field not provided" from "field explicitly set to null"
    # When user clicks "All", frontend sends selected_agent_ids: null, which means "all agents"
    update_kwargs = dict(
        title=thread_update.title,
        thread_metadata=thread_update.thread_metadata,
    )
    if 'selected_agent_ids' in thread_update.model_fields_set:
        update_kwargs['update_selected_agent_ids'] = True
        update_kwargs['selected_agent_ids'] = thread_update.selected_agent_ids

    updated_thread = crud.update_thread(
        db,
        thread_id=thread_id,
        **update_kwargs,
    )
    return updated_thread


@router.delete("/api/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: int,
    user_id: int = Query(..., description="User ID for permission check"),
    db: Session = Depends(get_db)
):
    """Soft delete a thread (requires thread owner or org write access)"""
    db_thread = crud.get_thread(db, thread_id=thread_id)
    if not db_thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )

    _check_thread_access(db, db_thread, user_id, require_write=True)

    crud.delete_thread(db, thread_id=thread_id)
    return None


@router.get("/api/threads/{thread_id}/queries", response_model=list[schemas.ChatQueryResponse])
async def get_thread_queries(
    thread_id: int,
    user_id: int = Query(...),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all queries in a thread"""
    thread = crud.get_thread(db, thread_id=thread_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )

    _check_thread_access(db, thread, user_id)

    queries = crud.get_chat_queries_by_thread(db, thread_id=thread_id, skip=skip, limit=limit)
    # Convert to response models with files and execution traces
    result = []
    for q in queries:
        # Deserialize execution_trace from JSONB
        execution_trace = None
        execution_times = None
        if q.execution_trace:
            try:
                if isinstance(q.execution_trace, dict):
                    # Already a dict (JSONB from PostgreSQL)
                    if "nodes" in q.execution_trace and "edges" in q.execution_trace:
                        execution_trace = schemas.ExecutionTrace(
                            nodes=[schemas.AgentNode(**node) for node in q.execution_trace.get("nodes", [])],
                            edges=[schemas.AgentEdge(**edge) for edge in q.execution_trace.get("edges", [])],
                            metadata=q.execution_trace.get("metadata")  # Include metadata with progress_updates
                        )
                    # Extract execution_times from metadata if present
                    if "metadata" in q.execution_trace and "execution_times" in q.execution_trace["metadata"]:
                        execution_times = q.execution_trace["metadata"]["execution_times"]
            except Exception as e:
                print(f"Error deserializing execution_trace for query {q.id}: {e}")
                execution_trace = None

        result.append(schemas.ChatQueryResponse(
            id=q.id,
            thread_id=q.thread_id,
            user_id=q.user_id,
            organization_id=q.organization_id,
            message=q.message,
            response=q.response,
            answer_mode=q.answer_mode.value if hasattr(q, 'answer_mode') and q.answer_mode else "light",
            reask_of_query_id=q.reask_of_query_id if hasattr(q, 'reask_of_query_id') else None,
            followup_of_query_id=q.followup_of_query_id if hasattr(q, 'followup_of_query_id') else None,
            created_at=q.created_at,
            execution_trace=execution_trace,
            execution_times=execution_times,
            content_structure=q.content_structure if hasattr(q, 'content_structure') else None,
            followup_questions=q.followup_questions if hasattr(q, 'followup_questions') else None,
            files=[
                schemas.FileResponse(
                    id=f.id,
                    user_id=f.user_id,
                    organization_id=f.organization_id,
                    filename=f.filename,
                    original_filename=f.original_filename,
                    content_type=f.content_type,
                    file_size=f.file_size,
                    created_at=f.created_at
                )
                for f in q.files
            ] if q.files else []
        ))
    return result


@router.get("/api/queries", response_model=list[schemas.ChatQueryResponse])
async def get_queries(
    user_id: int = Query(...),
    thread_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get queries — requires user_id, scoped to user's own queries or a specific thread they can access."""
    if thread_id:
        # Verify thread access
        thread = crud.get_thread(db, thread_id=thread_id)
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found"
            )
        _check_thread_access(db, thread, user_id)
        queries = crud.get_chat_queries_by_thread(db, thread_id=thread_id, skip=skip, limit=limit)
    else:
        # Only return the user's own queries
        queries = crud.get_chat_queries_by_user(db, user_id=user_id, skip=skip, limit=limit)
    return queries


@router.get("/api/queries/{query_id}", response_model=schemas.ChatQueryResponse)
async def get_query(
    query_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    db_query = crud.get_chat_query(db, query_id=query_id)
    if db_query is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    # Check access: own query, or org member
    if db_query.user_id != user_id:
        if not crud.check_org_permission(db, db_query.organization_id, user_id, require_write=False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this query"
            )
    return db_query
