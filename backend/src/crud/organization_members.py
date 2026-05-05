from sqlalchemy.orm import Session
from .. import models, schemas
from typing import Optional, List

def add_organization_member(db: Session, org_id: int, member: schemas.OrganizationMemberCreate) -> models.OrganizationMember:
    db_member = models.OrganizationMember(
        organization_id=org_id,
        user_id=member.user_id,
        can_read=member.can_read,
        can_write=member.can_write
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

def get_organization_member(db: Session, org_id: int, user_id: int) -> Optional[models.OrganizationMember]:
    return db.query(models.OrganizationMember)\
        .filter(
            models.OrganizationMember.organization_id == org_id,
            models.OrganizationMember.user_id == user_id
        ).first()

def get_organization_members(db: Session, org_id: int) -> List[models.OrganizationMember]:
    return db.query(models.OrganizationMember)\
        .filter(models.OrganizationMember.organization_id == org_id)\
        .all()

def update_organization_member(db: Session, org_id: int, user_id: int, member_update: schemas.OrganizationMemberUpdate) -> Optional[models.OrganizationMember]:
    db_member = get_organization_member(db, org_id, user_id)
    if db_member:
        if member_update.can_read is not None:
            db_member.can_read = member_update.can_read
        if member_update.can_write is not None:
            db_member.can_write = member_update.can_write
        db.commit()
        db.refresh(db_member)
    return db_member

def remove_organization_member(db: Session, org_id: int, user_id: int) -> bool:
    db_member = get_organization_member(db, org_id, user_id)
    if db_member:
        db.delete(db_member)
        db.commit()
        return True
    return False

