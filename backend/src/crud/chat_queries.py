from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from .. import models, schemas
from ..crud import files as files_crud
from typing import Optional, List, Any
import json
import os
import uuid


def sanitize_for_db(data: Any) -> Any:
    """
    Recursively remove null characters (\u0000) from strings in data structures.
    PostgreSQL doesn't support null characters in text fields.
    """
    if isinstance(data, str):
        # Remove null characters
        return data.replace('\u0000', '')
    elif isinstance(data, dict):
        return {k: sanitize_for_db(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_db(item) for item in data]
    else:
        return data

def create_chat_query(
    db: Session,
    query: schemas.ChatQueryCreate,
    response: str,
    execution_trace: Optional[dict] = None,
    execution_times: Optional[dict] = None,
    content_structure: Optional[dict] = None,
    followup_questions: Optional[list] = None,
    agent_ids_used: Optional[list] = None,
) -> models.ChatQuery:
    # Store execution_times in execution_trace metadata if provided
    if execution_times and execution_trace:
        if not execution_trace.get("metadata"):
            execution_trace["metadata"] = {}
        execution_trace["metadata"]["execution_times"] = execution_times

    # Sanitize all data to remove null characters before DB insertion
    sanitized_message = sanitize_for_db(query.message)
    sanitized_response = sanitize_for_db(response)
    sanitized_trace = sanitize_for_db(execution_trace) if execution_trace else None
    sanitized_content = sanitize_for_db(content_structure) if content_structure else None
    sanitized_followup = sanitize_for_db(followup_questions) if followup_questions else None

    db_query = models.ChatQuery(
        thread_id=query.thread_id,
        user_id=query.user_id,
        organization_id=query.organization_id,
        message=sanitized_message,
        response=sanitized_response,
        answer_mode=query.answer_mode if hasattr(query, 'answer_mode') else "light",
        reask_of_query_id=query.reask_of_query_id if hasattr(query, 'reask_of_query_id') else None,
        followup_of_query_id=query.followup_of_query_id if hasattr(query, 'followup_of_query_id') else None,
        execution_trace=sanitized_trace,
        content_structure=sanitized_content,
        followup_questions=sanitized_followup,
        agent_ids_used=agent_ids_used,
    )
    db.add(db_query)
    db.commit()
    db.refresh(db_query)
    return db_query

def get_chat_queries_by_thread(db: Session, thread_id: int, skip: int = 0, limit: int = 100) -> List[models.ChatQuery]:
    return db.query(models.ChatQuery)\
        .filter(models.ChatQuery.thread_id == thread_id)\
        .options(joinedload(models.ChatQuery.files))\
        .order_by(models.ChatQuery.created_at)\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_chat_queries_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.ChatQuery]:
    return db.query(models.ChatQuery)\
        .filter(models.ChatQuery.user_id == user_id)\
        .order_by(desc(models.ChatQuery.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_chat_queries_by_organization(db: Session, org_id: int, skip: int = 0, limit: int = 100) -> List[models.ChatQuery]:
    return db.query(models.ChatQuery)\
        .filter(models.ChatQuery.organization_id == org_id)\
        .order_by(desc(models.ChatQuery.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_chat_query(db: Session, query_id: int) -> Optional[models.ChatQuery]:
    return db.query(models.ChatQuery).filter(models.ChatQuery.id == query_id).first()

def update_chat_query(
    db: Session,
    query_id: int,
    response: Optional[str] = None,
    execution_trace: Optional[dict] = None,
    execution_times: Optional[dict] = None,
    content_structure: Optional[dict] = None,
    followup_questions: Optional[list] = None,
    error: Optional[str] = None,
    agent_ids_used: Optional[list] = None,
) -> Optional[models.ChatQuery]:
    """Update an existing chat query with new data."""
    db_query = get_chat_query(db, query_id)
    if not db_query:
        return None

    if response is not None:
        db_query.response = sanitize_for_db(response)

    if agent_ids_used is not None:
        db_query.agent_ids_used = agent_ids_used

    if execution_trace is not None:
        # Merge execution_times into trace metadata if provided
        if execution_times:
            if not execution_trace.get("metadata"):
                execution_trace["metadata"] = {}
            execution_trace["metadata"]["execution_times"] = execution_times
        db_query.execution_trace = sanitize_for_db(execution_trace)

    if content_structure is not None:
        db_query.content_structure = sanitize_for_db(content_structure)

    if followup_questions is not None:
        db_query.followup_questions = sanitize_for_db(followup_questions)

    # Store error in execution_trace metadata if provided
    if error is not None:
        if not db_query.execution_trace:
            db_query.execution_trace = {}
        if not db_query.execution_trace.get("metadata"):
            db_query.execution_trace["metadata"] = {}
        db_query.execution_trace["metadata"]["error"] = sanitize_for_db(error)
        # Also set a generic error response if no response exists
        if not db_query.response:
            db_query.response = sanitize_for_db(f"An error occurred while processing your request: {error}")

    db.commit()
    db.refresh(db_query)
    return db_query

def get_all_chat_queries(db: Session, skip: int = 0, limit: int = 100) -> List[models.ChatQuery]:
    return db.query(models.ChatQuery)\
        .order_by(desc(models.ChatQuery.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()

def process_generated_images_from_trace(
    db: Session,
    query_id: int,
    execution_trace: Optional[dict],
    user_id: int,
    organization_id: int
) -> List[int]:
    """
    Process execution trace to find generated images and create File records.
    Returns list of created file IDs.
    """
    if not execution_trace or not execution_trace.get("nodes"):
        return []
    
    file_ids = []
    
    # Find all image_generator tool nodes
    for node in execution_trace.get("nodes", []):
        if node.get("type") == "tool" and node.get("name") == "image_generator":
            metadata = node.get("metadata", {})
            result = metadata.get("result", "")
            
            if not result:
                continue
            
            try:
                # Parse the JSON result from the tool
                result_data = json.loads(result)
                
                if not result_data.get("success"):
                    continue
                
                file_path = result_data.get("file_path")
                if not file_path:
                    continue
                
                # Resolve relative paths to absolute
                if not os.path.isabs(file_path):
                    from ..storage import UPLOAD_DIR
                    file_path = os.path.join(UPLOAD_DIR, file_path) if not file_path.startswith(UPLOAD_DIR) else file_path
                    file_path = os.path.abspath(file_path)
                
                if not os.path.exists(file_path):
                    print(f"[WARNING] Generated image file not found: {file_path}")
                    continue
                
                # Read the file
                with open(file_path, "rb") as f:
                    file_content = f.read()
                
                # Check if file is already in uploads directory (from image_generator tool)
                # If so, we can reuse the existing file path
                from ..storage import UPLOAD_DIR
                # Normalize paths for comparison
                abs_file_path = os.path.abspath(file_path)
                abs_upload_dir = os.path.abspath(UPLOAD_DIR)
                if abs_file_path.startswith(abs_upload_dir):
                    # File is already in uploads, just create the database record
                    # Extract filename from path
                    filename = os.path.basename(file_path)
                    original_filename = result_data.get("original_filename", f"generated_image_{uuid.uuid4().hex[:8]}.png")
                    
                    # Store absolute path in database for reliable file access
                    # FileResponse can handle both absolute and relative paths, but absolute is more reliable
                    db_file = models.File(
                        user_id=user_id,
                        organization_id=organization_id,
                        filename=filename,
                        original_filename=original_filename,
                        file_path=abs_file_path,  # Store absolute path
                        content_type=result_data.get("content_type", "image/png"),
                        file_size=len(file_content)
                    )
                    db.add(db_file)
                    db.commit()
                    db.refresh(db_file)
                    print(f"[INFO] Created file record for generated image: {db_file.id} ({original_filename})")
                else:
                    # File is in a different location (old behavior), save to uploads
                    db_file = files_crud.create_file(
                        db=db,
                        user_id=user_id,
                        organization_id=organization_id,
                        original_filename=result_data.get("original_filename", "generated_image.png"),
                        file_content=file_content,
                        content_type=result_data.get("content_type", "image/png"),
                        skip_validation=True
                    )
                
                file_ids.append(db_file.id)
                
            except (json.JSONDecodeError, IOError, Exception) as e:
                # Log error but continue processing other images
                print(f"Error processing generated image: {e}")
                continue
    
    # Associate all generated images with the query
    if file_ids:
        files_crud.associate_files_with_query(db, query_id, file_ids)
    
    return file_ids

