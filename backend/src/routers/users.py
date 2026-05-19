from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..api_auth import authenticated_user_id, require_admin_user
from .. import models, schemas, crud

router = APIRouter(tags=["users"])


@router.post("/api/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    return crud.create_user(db=db, user=user)


@router.get("/api/users", response_model=list[schemas.UserPublicResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin_id: int = Depends(require_admin_user),
):
    """List all users (admin only). Returns public fields only — never api_keys."""
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@router.get("/api/users/{user_id}", response_model=schemas.UserPublicResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _caller_id: int = Depends(authenticated_user_id),
):
    """Fetch a user's public profile. Never returns api_key — owners read their own key from login."""
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return db_user


# Admin session management endpoints (must be before parameterized {target_user_id} routes)
@router.post("/api/admin/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    user: schemas.AdminUserCreate,
    admin_user_id: int = Query(..., description="ID of the admin creating the user"),
    db: Session = Depends(get_db)
):
    """
    Create a user account on behalf of someone (admin only).
    Sets email, username, password, and optionally admin status.
    """
    from ..admin_auth import require_admin
    require_admin(admin_user_id, db)

    # Check if user already exists
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    return crud.admin_create_user(db=db, user=user)


@router.post("/api/admin/users/invalidate-all-sessions", response_model=schemas.SessionInvalidationResponse)
async def invalidate_all_sessions(
    admin_user_id: int = Query(..., description="ID of the admin performing the invalidation"),
    db: Session = Depends(get_db)
):
    """
    Invalidate ALL user sessions by rotating every API key (admin only).
    All users (including the admin) will be logged out and must re-authenticate.
    """
    from ..admin_auth import require_admin
    require_admin(admin_user_id, db)

    count = crud.rotate_all_api_keys(db)

    return schemas.SessionInvalidationResponse(
        message=f"All sessions invalidated. {count} user(s) affected. You will also be logged out.",
        affected_user_count=count
    )


@router.post("/api/admin/users/{target_user_id}/invalidate-session", response_model=schemas.SessionInvalidationResponse)
async def invalidate_user_session(
    target_user_id: int,
    admin_user_id: int = Query(..., description="ID of the admin performing the invalidation"),
    db: Session = Depends(get_db)
):
    """
    Invalidate a specific user's session by rotating their API key (admin only).
    The target user will be logged out and must re-authenticate.
    """
    from ..admin_auth import require_admin
    require_admin(admin_user_id, db)

    updated_user = crud.rotate_user_api_key(db, target_user_id)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return schemas.SessionInvalidationResponse(
        message=f"Session invalidated for user '{updated_user.username}'",
        affected_user_count=1
    )


@router.post("/api/admin/users/{target_user_id}/password-reset-token", response_model=schemas.PasswordResetTokenResponse)
async def generate_password_reset_token(
    target_user_id: int,
    admin_user_id: int = Query(..., description="ID of the admin generating the token"),
    db: Session = Depends(get_db)
):
    """
    Generate a password reset token for a user (admin only).
    The admin shares this token (or the reset URL) with the user out-of-band.
    Token expires in 1 hour.
    """
    from ..admin_auth import require_admin
    require_admin(admin_user_id, db)

    target_user = crud.get_user(db, target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    expires_hours = 1
    token = crud.generate_password_reset_token(db, target_user_id, expires_hours)

    return schemas.PasswordResetTokenResponse(
        token=token,
        expires_in_hours=expires_hours,
        reset_url=f"/reset-password?token={token}",
        message=f"Password reset token generated for '{target_user.username}'. Share the reset URL with the user."
    )


# Admin user management endpoints
@router.patch("/api/admin/users/{target_user_id}", response_model=schemas.UserResponse)
async def update_user_admin(
    target_user_id: int,
    user_update: schemas.UserUpdate,
    admin_user_id: int = Query(..., description="ID of the admin performing the update"),
    db: Session = Depends(get_db)
):
    """
    Update user properties (admin only).
    Allows admins to toggle admin status or ban/unban users.
    """
    from ..admin_auth import require_admin

    # Verify the requesting user is an admin
    require_admin(admin_user_id, db)

    # Prevent admins from disabling themselves
    if target_user_id == admin_user_id and user_update.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot disable your own account"
        )

    # Update the target user
    updated_user = crud.update_user(db, target_user_id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return updated_user


@router.get("/api/admin/users/{target_user_id}/threads", response_model=List[schemas.ThreadResponse])
async def get_user_threads_admin(
    target_user_id: int,
    admin_user_id: int = Query(..., description="ID of the admin requesting data"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all threads for a specific user (admin only).
    Allows admins to view user conversations for support/moderation.
    """
    from ..admin_auth import require_admin

    # Verify the requesting user is an admin
    require_admin(admin_user_id, db)

    # Get the target user
    target_user = crud.get_user(db, target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get threads for the target user
    threads = crud.get_threads_by_user(db, target_user_id, skip=skip, limit=limit)

    # Add message counts
    thread_responses = []
    for thread in threads:
        message_count = db.query(models.ChatQuery).filter(
            models.ChatQuery.thread_id == thread.id
        ).count()

        thread_dict = {
            "id": thread.id,
            "user_id": thread.user_id,
            "organization_id": thread.organization_id,
            "title": thread.title,
            "thread_metadata": thread.thread_metadata,
            "created_at": thread.created_at,
            "updated_at": thread.updated_at,
            "message_count": message_count
        }
        thread_responses.append(schemas.ThreadResponse(**thread_dict))

    return thread_responses


@router.get("/api/admin/users/{target_user_id}/queries", response_model=List[schemas.ChatQueryResponse])
async def get_user_queries_admin(
    target_user_id: int,
    admin_user_id: int = Query(..., description="ID of the admin requesting data"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get recent chat queries for a specific user (admin only).
    Allows admins to view user conversations for support/moderation.
    """
    from ..admin_auth import require_admin

    # Verify the requesting user is an admin
    require_admin(admin_user_id, db)

    # Get the target user
    target_user = crud.get_user(db, target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get queries for the target user
    queries = crud.get_chat_queries_by_user(db, target_user_id, skip=skip, limit=limit)
    return queries
