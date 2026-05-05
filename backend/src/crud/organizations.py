from sqlalchemy.orm import Session
from sqlalchemy import desc
from .. import models, schemas
from typing import Optional, List
from .organization_members import get_organization_member
from .users import get_user

def create_organization(db: Session, organization: schemas.OrganizationCreate, owner_id: int) -> models.Organization:
    db_org = models.Organization(
        name=organization.name,
        description=organization.description,
        owner_id=owner_id
    )
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org

def get_organization(db: Session, org_id: int) -> Optional[models.Organization]:
    return db.query(models.Organization).filter(models.Organization.id == org_id).first()

def get_organization_by_uuid(db: Session, org_uuid: str) -> Optional[models.Organization]:
    """Get organization by UUID (for external API access)"""
    import uuid as uuid_lib
    try:
        uuid_obj = uuid_lib.UUID(org_uuid) if isinstance(org_uuid, str) else org_uuid
        return db.query(models.Organization).filter(models.Organization.uuid == uuid_obj).first()
    except (ValueError, AttributeError):
        return None

def get_all_organizations(db: Session, skip: int = 0, limit: int = 100) -> List[models.Organization]:
    """Get all organizations (admin only)"""
    return db.query(models.Organization)\
        .order_by(desc(models.Organization.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_organizations_by_owner(db: Session, owner_id: int, skip: int = 0, limit: int = 100) -> List[models.Organization]:
    return db.query(models.Organization)\
        .filter(models.Organization.owner_id == owner_id)\
        .order_by(desc(models.Organization.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_organizations_by_member(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.Organization]:
    """Get organizations where user is either owner or member"""
    # Organizations owned by user
    owned = db.query(models.Organization)\
        .filter(models.Organization.owner_id == user_id)\
        .all()
    
    # Organizations where user is a member
    member_orgs = db.query(models.Organization)\
        .join(models.OrganizationMember)\
        .filter(models.OrganizationMember.user_id == user_id)\
        .all()
    
    # Combine and deduplicate
    all_orgs = {org.id: org for org in owned + member_orgs}
    return list(all_orgs.values())[skip:skip+limit]

def update_organization(db: Session, org_id: int, organization: schemas.OrganizationUpdate) -> Optional[models.Organization]:
    db_org = get_organization(db, org_id)
    if db_org:
        if organization.name is not None:
            db_org.name = organization.name
        if organization.description is not None:
            db_org.description = organization.description
        if organization.metadata is not None:
            # Convert Pydantic model to dict for JSONB storage
            db_org.org_metadata = organization.metadata.model_dump(exclude_none=True) if organization.metadata else None
        db.commit()
        db.refresh(db_org)
    return db_org

def delete_organization(db: Session, org_id: int) -> bool:
    db_org = get_organization(db, org_id)
    if db_org:
        # Nullify self-referential FK to avoid constraint issues during cascade
        db.query(models.ChatQuery).filter(
            models.ChatQuery.organization_id == org_id,
            models.ChatQuery.reask_of_query_id.isnot(None)
        ).update({models.ChatQuery.reask_of_query_id: None}, synchronize_session=False)

        # Clean up chat_query_files association table entries
        query_ids = [q.id for q in db.query(models.ChatQuery.id).filter(
            models.ChatQuery.organization_id == org_id
        ).all()]
        if query_ids:
            db.execute(
                models.chat_query_files.delete().where(
                    models.chat_query_files.c.chat_query_id.in_(query_ids)
                )
            )

        file_ids = [f.id for f in db.query(models.File.id).filter(
            models.File.organization_id == org_id
        ).all()]
        if file_ids:
            db.execute(
                models.chat_query_files.delete().where(
                    models.chat_query_files.c.file_id.in_(file_ids)
                )
            )

        db.delete(db_org)
        db.commit()
        return True
    return False

def check_org_permission(db: Session, org_id: int, user_id: int, require_write: bool = False) -> bool:
    """Check if user has permission (read or write) for an organization"""
    org = get_organization(db, org_id)
    if not org:
        return False

    # System admins have all permissions
    user = get_user(db, user_id)
    if user and user.is_admin:
        return True

    # Owner has all permissions
    if org.owner_id == user_id:
        return True

    # Check member permissions
    member = get_organization_member(db, org_id, user_id)
    if not member:
        return False

    if require_write:
        return member.can_write
    return member.can_read

