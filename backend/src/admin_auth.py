"""
Authorization middleware for admin-only endpoints.
"""
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from . import models, crud
from .database import get_db


def require_admin(user_id: int, db: Session = Depends(get_db)) -> models.User:
    """
    Dependency that verifies the user is an admin.
    Raises 403 Forbidden if user is not an admin or not active.
    """
    user = crud.get_user(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return user


def check_user_active(user_id: int, db: Session) -> None:
    """
    Check if a user is active. Raises exception if user is banned/disabled.
    Used in regular endpoints to prevent disabled users from accessing resources.
    """
    user = crud.get_user(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled. Please contact an administrator."
        )
