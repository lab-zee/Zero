from sqlalchemy.orm import Session
from sqlalchemy import desc
from .. import models
from ..storage import save_file, generate_unique_filename, validate_file_type
from typing import Optional, List
import os

def create_file(
    db: Session,
    user_id: int,
    organization_id: int,
    original_filename: str,
    file_content: bytes,
    content_type: Optional[str] = None,
    skip_validation: bool = False
) -> models.File:
    """Create a file record and save the file to disk"""
    # Validate file type (unless skipped for programmatically generated files)
    if not skip_validation:
        is_valid, error_msg = validate_file_type(original_filename, content_type)
        if not is_valid:
            raise ValueError(error_msg)
    
    # Generate unique filename
    unique_filename = generate_unique_filename(original_filename)
    
    # Save file to storage
    file_path = save_file(file_content, unique_filename)
    
    # Create database record
    db_file = models.File(
        user_id=user_id,
        organization_id=organization_id,
        filename=unique_filename,
        original_filename=original_filename,
        file_path=file_path,
        content_type=content_type,
        file_size=len(file_content)
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def get_file(db: Session, file_id: int) -> Optional[models.File]:
    """Get a file by ID"""
    return db.query(models.File).filter(models.File.id == file_id).first()

def get_files_by_user(
    db: Session,
    user_id: int,
    organization_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.File]:
    """Get files uploaded by a user, optionally filtered by organization"""
    query = db.query(models.File).filter(models.File.user_id == user_id)
    if organization_id:
        query = query.filter(models.File.organization_id == organization_id)
    return query.order_by(desc(models.File.created_at)).offset(skip).limit(limit).all()

def get_files_by_organization(
    db: Session,
    organization_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[models.File]:
    """Get all files in an organization"""
    return db.query(models.File)\
        .filter(models.File.organization_id == organization_id)\
        .order_by(desc(models.File.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()

def delete_file(db: Session, file_id: int, user_id: int) -> bool:
    """Delete a file (by owner or organization member with write access)"""
    from ..storage import delete_file_from_storage
    from .organizations import check_org_permission
    
    db_file = db.query(models.File).filter(models.File.id == file_id).first()
    if not db_file:
        return False
    
    # Check ownership or organization write access
    if db_file.user_id == user_id:
        # Owner can always delete
        pass
    else:
        # Check if user has write access to the organization
        has_write_access = check_org_permission(db, db_file.organization_id, user_id, require_write=True)
        if not has_write_access:
            return False
    
    # Delete file from storage
    delete_file_from_storage(db_file.file_path)
    
    # Remove from vector store
    try:
        from .vector_store import remove_document_from_store
        remove_document_from_store(db_file.organization_id, file_id)
    except Exception as e:
        print(f"Warning: Failed to remove file from vector store: {e}")
        # Continue with deletion even if vector store removal fails
    
    # Delete database record
    db.delete(db_file)
    db.commit()
    return True

def associate_files_with_query(db: Session, query_id: int, file_ids: List[int]) -> None:
    """Associate files with a chat query"""
    db_query = db.query(models.ChatQuery).filter(models.ChatQuery.id == query_id).first()
    if not db_query:
        return
    
    # Get files
    files = db.query(models.File).filter(models.File.id.in_(file_ids)).all()
    
    # Associate files with query
    db_query.files.extend(files)
    db.commit()

