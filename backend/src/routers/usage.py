from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..api_auth import get_current_user
from .. import models, schemas, crud

router = APIRouter(tags=["usage"])


@router.get("/api/usage/stats", response_model=schemas.UserUsageStats)
async def get_my_usage_stats(
    days: int = Query(30, ge=1, le=365),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get usage statistics for the authenticated user (identified by API key)."""
    daily_usage = crud.get_user_usage_stats(db, user.id, days)
    total_count = crud.get_total_usage_count(db, user.id)

    return schemas.UserUsageStats(
        daily_usage=[schemas.DailyUsageStat(**stat) for stat in daily_usage],
        total_count=total_count
    )


@router.get("/api/admin/usage/all", response_model=List[schemas.AllUsersUsageStats])
async def get_all_users_usage_stats(
    days: int = Query(30, ge=1, le=365),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get usage statistics for all users (admin only, identified by API key)."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    all_stats = crud.get_all_users_usage_stats(db, days)

    return [schemas.AllUsersUsageStats(**stat) for stat in all_stats]
