from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..database import get_db
from .. import schemas, crud, models

router = APIRouter(tags=["organizations"])


@router.post("/api/organizations", response_model=schemas.OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization: schemas.OrganizationCreate,
    user_id: int = Query(..., description="User ID of the organization owner"),
    db: Session = Depends(get_db)
):
    # Verify user exists
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    created_org = crud.create_organization(db, organization, owner_id=user_id)
    return schemas.OrganizationResponse(
        id=created_org.id,
        name=created_org.name,
        description=created_org.description,
        owner_id=created_org.owner_id,
        created_at=created_org.created_at,
        updated_at=created_org.updated_at,
        metadata=created_org.org_metadata if created_org.org_metadata else None,
    )


@router.get("/api/organizations", response_model=list[schemas.OrganizationResponse])
async def get_my_organizations(
    user_id: int = Query(..., description="User ID to get organizations for"),
    db: Session = Depends(get_db)
):
    """Get all organizations where user is owner or member. Admins see all orgs."""
    user = crud.get_user(db, user_id=user_id)
    if user and user.is_admin:
        organizations = crud.get_all_organizations(db)
    else:
        organizations = crud.get_organizations_by_member(db, user_id=user_id)
    # Manually convert to avoid SQLAlchemy metadata conflict
    return [
        schemas.OrganizationResponse(
            id=org.id,
            name=org.name,
            description=org.description,
            owner_id=org.owner_id,
            created_at=org.created_at,
            updated_at=org.updated_at,
            metadata=org.org_metadata if org.org_metadata else None,
        )
        for org in organizations
    ]


@router.get("/api/organizations/with-stats", response_model=list[schemas.OrganizationWithStats])
async def get_my_organizations_with_stats(
    user_id: int = Query(..., description="User ID to get organizations for"),
    db: Session = Depends(get_db)
):
    """Get all organizations where user is owner or member, with stats. Admins see all orgs."""
    user = crud.get_user(db, user_id=user_id)
    if user and user.is_admin:
        organizations = crud.get_all_organizations(db)
    else:
        organizations = crud.get_organizations_by_member(db, user_id=user_id)

    if not organizations:
        return []

    org_ids = [org.id for org in organizations]

    # Subquery: count non-deleted threads per organization
    thread_counts = (
        db.query(
            models.Thread.organization_id,
            func.count(models.Thread.id).label("thread_count"),
        )
        .filter(
            models.Thread.organization_id.in_(org_ids),
            models.Thread.deleted_at.is_(None),
        )
        .group_by(models.Thread.organization_id)
        .subquery()
    )

    # Subquery: count messages across non-deleted threads per organization
    message_counts = (
        db.query(
            models.Thread.organization_id,
            func.count(models.ChatQuery.id).label("total_message_count"),
        )
        .join(models.ChatQuery, models.ChatQuery.thread_id == models.Thread.id)
        .filter(
            models.Thread.organization_id.in_(org_ids),
            models.Thread.deleted_at.is_(None),
        )
        .group_by(models.Thread.organization_id)
        .subquery()
    )

    # Subquery: count unique users who contributed questions per organization
    user_counts = (
        db.query(
            models.ChatQuery.organization_id,
            func.count(func.distinct(models.ChatQuery.user_id)).label("unique_user_count"),
        )
        .filter(models.ChatQuery.organization_id.in_(org_ids))
        .group_by(models.ChatQuery.organization_id)
        .subquery()
    )

    # Subquery: count files per organization
    file_counts = (
        db.query(
            models.File.organization_id,
            func.count(models.File.id).label("file_count"),
        )
        .filter(models.File.organization_id.in_(org_ids))
        .group_by(models.File.organization_id)
        .subquery()
    )

    # Build a lookup from org_id -> stats
    stats_query = (
        db.query(
            models.Organization.id,
            func.coalesce(thread_counts.c.thread_count, 0).label("thread_count"),
            func.coalesce(message_counts.c.total_message_count, 0).label("total_message_count"),
            func.coalesce(user_counts.c.unique_user_count, 0).label("unique_user_count"),
            func.coalesce(file_counts.c.file_count, 0).label("file_count"),
        )
        .outerjoin(thread_counts, models.Organization.id == thread_counts.c.organization_id)
        .outerjoin(message_counts, models.Organization.id == message_counts.c.organization_id)
        .outerjoin(user_counts, models.Organization.id == user_counts.c.organization_id)
        .outerjoin(file_counts, models.Organization.id == file_counts.c.organization_id)
        .filter(models.Organization.id.in_(org_ids))
        .all()
    )

    stats_map = {
        row.id: {
            "thread_count": row.thread_count,
            "total_message_count": row.total_message_count,
            "unique_user_count": row.unique_user_count,
            "file_count": row.file_count,
        }
        for row in stats_query
    }

    # Build owner username lookup
    owner_ids = list({org.owner_id for org in organizations})
    owners = {u.id: u.username for u in db.query(models.User).filter(models.User.id.in_(owner_ids)).all()}

    return [
        schemas.OrganizationWithStats(
            id=org.id,
            name=org.name,
            description=org.description,
            owner_id=org.owner_id,
            created_at=org.created_at,
            updated_at=org.updated_at,
            metadata=org.org_metadata if org.org_metadata else None,
            thread_count=stats_map.get(org.id, {}).get("thread_count", 0),
            total_message_count=stats_map.get(org.id, {}).get("total_message_count", 0),
            unique_user_count=stats_map.get(org.id, {}).get("unique_user_count", 0),
            file_count=stats_map.get(org.id, {}).get("file_count", 0),
            owner_username=owners.get(org.owner_id),
        )
        for org in organizations
    ]


@router.get("/api/organizations/{org_id}", response_model=schemas.OrganizationWithMembers)
async def get_organization(
    org_id: int,
    user_id: int = Query(..., description="User ID for permission check"),
    db: Session = Depends(get_db)
):
    """Get organization details with members (requires read permission)"""
    # Check permission
    if not crud.check_org_permission(db, org_id, user_id, require_write=False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this organization"
        )

    org = crud.get_organization(db, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Get owner
    owner = crud.get_user(db, org.owner_id)

    # Get members
    members = crud.get_organization_members(db, org_id)

    # Build response
    member_responses = []
    for member in members:
        member_user = crud.get_user(db, member.user_id)
        if member_user:
            member_responses.append(schemas.OrganizationMemberResponse(
                id=member.id,
                organization_id=member.organization_id,
                user_id=member.user_id,
                can_read=member.can_read,
                can_write=member.can_write,
                created_at=member.created_at,
                user=schemas.UserResponse(
                    id=member_user.id,
                    email=member_user.email,
                    username=member_user.username,
                    api_key=member_user.api_key,
                    created_at=member_user.created_at
                )
            ))

    return schemas.OrganizationWithMembers(
        id=org.id,
        name=org.name,
        description=org.description,
        owner_id=org.owner_id,
        created_at=org.created_at,
        updated_at=org.updated_at,
        metadata=org.org_metadata if org.org_metadata else None,
        owner=schemas.UserResponse(
            id=owner.id,
            email=owner.email,
            username=owner.username,
            api_key=owner.api_key,
            created_at=owner.created_at
        ),
        members=member_responses
    )


@router.put("/api/organizations/{org_id}", response_model=schemas.OrganizationResponse)
async def update_organization(
    org_id: int,
    organization: schemas.OrganizationUpdate,
    user_id: int = Query(..., description="User ID for permission check"),
    db: Session = Depends(get_db)
):
    """Update organization (requires owner or write permission)"""
    # Check permission - must be owner or have write permission
    org = crud.get_organization(db, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    if org.owner_id != user_id and not crud.check_org_permission(db, org_id, user_id, require_write=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this organization"
        )

    updated_org = crud.update_organization(db, org_id, organization)
    if not updated_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return schemas.OrganizationResponse(
        id=updated_org.id,
        name=updated_org.name,
        description=updated_org.description,
        owner_id=updated_org.owner_id,
        created_at=updated_org.created_at,
        updated_at=updated_org.updated_at,
        metadata=updated_org.org_metadata if updated_org.org_metadata else None,
    )


@router.delete("/api/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: int,
    user_id: int = Query(..., description="User ID for permission check"),
    db: Session = Depends(get_db)
):
    """Delete organization (requires owner or admin)"""
    org = crud.get_organization(db, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    user = crud.get_user(db, user_id=user_id)
    if org.owner_id != user_id and not (user and user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner or an admin can delete the organization"
        )

    crud.delete_organization(db, org_id)
    return None


@router.post("/api/organizations/scrape-website")
async def scrape_organization_website(
    url: str = Query(..., description="Website URL to scrape"),
    user_id: int = Query(..., description="User ID making the request"),
    db: Session = Depends(get_db)
):
    """Scrape website to extract organization information"""
    # Verify user exists
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    try:
        from ..agents.tools.website_scraper import scrape_website
        result = scrape_website(url)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Scraping failed: {str(e)}",
            "data": None
        }


@router.get("/api/organizations/{org_id}/files", response_model=List[schemas.FileResponse])
async def get_organization_files(
    org_id: int,
    user_id: int = Query(...),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all files in an organization (requires read access)"""
    # Verify organization exists and user has access
    org = crud.get_organization(db, org_id=org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check if user has read access to organization
    has_access = crud.check_org_permission(db, org_id, user_id, require_write=False)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization"
        )

    files = crud.get_files_by_organization(db, organization_id=org_id, skip=skip, limit=limit)
    return [
        schemas.FileResponse(
            id=file.id,
            user_id=file.user_id,
            organization_id=file.organization_id,
            filename=file.filename,
            original_filename=file.original_filename,
            content_type=file.content_type,
            file_size=file.file_size,
            created_at=file.created_at
        )
        for file in files
    ]


# Organization Member endpoints
@router.post("/api/organizations/{org_id}/members", response_model=schemas.OrganizationMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_organization_member(
    org_id: int,
    member: schemas.OrganizationMemberCreate,
    user_id: int = Query(..., description="User ID making the request (must be owner)"),
    db: Session = Depends(get_db)
):
    """Add a member to an organization (requires owner). Can add by user_id or email."""
    org = crud.get_organization(db, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    user = crud.get_user(db, user_id)
    if org.owner_id != user_id and not (user and user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner or an admin can add members"
        )

    # Find user by user_id or email
    target_user = None
    if member.user_id:
        target_user = crud.get_user(db, member.user_id)
    elif member.email:
        target_user = crud.get_user_by_email(db, member.email)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or email must be provided"
        )

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User to add not found"
        )

    # Check if already a member
    existing = crud.get_organization_member(db, org_id, target_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )

    # Create the member record with the found user's ID
    member_create = schemas.OrganizationMemberCreate(
        user_id=target_user.id,
        can_read=member.can_read,
        can_write=member.can_write
    )
    db_member = crud.add_organization_member(db, org_id, member_create)
    member_user = crud.get_user(db, db_member.user_id)

    return schemas.OrganizationMemberResponse(
        id=db_member.id,
        organization_id=db_member.organization_id,
        user_id=db_member.user_id,
        can_read=db_member.can_read,
        can_write=db_member.can_write,
        created_at=db_member.created_at,
        user=schemas.UserResponse(
            id=member_user.id,
            email=member_user.email,
            username=member_user.username,
            api_key=member_user.api_key,
            created_at=member_user.created_at
        )
    )


@router.put("/api/organizations/{org_id}/members/{member_user_id}", response_model=schemas.OrganizationMemberResponse)
async def update_organization_member(
    org_id: int,
    member_user_id: int,
    member_update: schemas.OrganizationMemberUpdate,
    user_id: int = Query(..., description="User ID making the request (must be owner)"),
    db: Session = Depends(get_db)
):
    """Update member permissions (requires owner)"""
    org = crud.get_organization(db, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    user = crud.get_user(db, user_id)
    if org.owner_id != user_id and not (user and user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner or an admin can update member permissions"
        )

    updated_member = crud.update_organization_member(db, org_id, member_user_id, member_update)
    if not updated_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    member_user = crud.get_user(db, updated_member.user_id)
    return schemas.OrganizationMemberResponse(
        id=updated_member.id,
        organization_id=updated_member.organization_id,
        user_id=updated_member.user_id,
        can_read=updated_member.can_read,
        can_write=updated_member.can_write,
        created_at=updated_member.created_at,
        user=schemas.UserResponse(
            id=member_user.id,
            email=member_user.email,
            username=member_user.username,
            api_key=member_user.api_key,
            created_at=member_user.created_at
        )
    )


@router.delete("/api/organizations/{org_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_member(
    org_id: int,
    member_user_id: int,
    user_id: int = Query(..., description="User ID making the request (must be owner)"),
    db: Session = Depends(get_db)
):
    """Remove a member from an organization (requires owner)"""
    org = crud.get_organization(db, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    user = crud.get_user(db, user_id)
    if org.owner_id != user_id and not (user and user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner or an admin can remove members"
        )

    if not crud.remove_organization_member(db, org_id, member_user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return None
