from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
from .. import models, schemas
from typing import Optional, List

def create_thread(db: Session, thread: schemas.ThreadCreate, user_id: int) -> models.Thread:
    db_thread = models.Thread(
        user_id=user_id,
        organization_id=thread.organization_id,
        title=thread.title,
        thread_metadata=thread.thread_metadata,
        selected_agent_ids=getattr(thread, 'selected_agent_ids', None),
    )
    db.add(db_thread)
    db.commit()
    db.refresh(db_thread)
    return db_thread

def get_thread(db: Session, thread_id: int) -> Optional[models.Thread]:
    return db.query(models.Thread).filter(
        models.Thread.id == thread_id,
        models.Thread.deleted_at.is_(None)
    ).first()

def get_thread_by_uuid(db: Session, thread_uuid: str) -> Optional[models.Thread]:
    """Get thread by UUID (for external API access)"""
    import uuid as uuid_lib
    try:
        uuid_obj = uuid_lib.UUID(thread_uuid) if isinstance(thread_uuid, str) else thread_uuid
        return db.query(models.Thread).filter(
            models.Thread.uuid == uuid_obj,
            models.Thread.deleted_at.is_(None)
        ).first()
    except (ValueError, AttributeError):
        return None

def get_threads_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.Thread]:
    return db.query(models.Thread)\
        .filter(
            models.Thread.user_id == user_id,
            models.Thread.deleted_at.is_(None)
        )\
        .order_by(desc(models.Thread.updated_at))\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_threads_by_organization(db: Session, org_id: int, skip: int = 0, limit: int = 100) -> List[models.Thread]:
    return db.query(models.Thread)\
        .filter(
            models.Thread.organization_id == org_id,
            models.Thread.deleted_at.is_(None)
        )\
        .order_by(desc(models.Thread.updated_at))\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_threads_by_user_and_org(db: Session, user_id: int, org_id: int, skip: int = 0, limit: int = 100) -> List[models.Thread]:
    return db.query(models.Thread)\
        .filter(
            models.Thread.user_id == user_id,
            models.Thread.organization_id == org_id,
            models.Thread.deleted_at.is_(None)
        )\
        .order_by(desc(models.Thread.updated_at))\
        .offset(skip)\
        .limit(limit)\
        .all()

def update_thread(
    db: Session,
    thread_id: int,
    title: Optional[str] = None,
    thread_metadata: Optional[dict] = None,
    selected_agent_ids: Optional[list] = None,
    update_selected_agent_ids: bool = False,
) -> Optional[models.Thread]:
    db_thread = get_thread(db, thread_id)
    if db_thread:
        if title is not None:
            db_thread.title = title
        if thread_metadata is not None:
            db_thread.thread_metadata = thread_metadata
        if update_selected_agent_ids:
            # Explicitly set, even if None (null = all agents)
            db_thread.selected_agent_ids = selected_agent_ids
        elif selected_agent_ids is not None:
            db_thread.selected_agent_ids = selected_agent_ids
        db.commit()
        db.refresh(db_thread)
    return db_thread

def delete_thread(db: Session, thread_id: int) -> bool:
    """Soft delete a thread by setting deleted_at timestamp"""
    db_thread = get_thread(db, thread_id)
    if db_thread:
        db_thread.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_thread)
        return True
    return False

