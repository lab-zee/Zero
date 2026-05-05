from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, List

from ..database import get_db
from .. import models, schemas, crud

router = APIRouter(tags=["usage"])


@router.get("/api/usage/stats", response_model=schemas.UserUsageStats)
async def get_my_usage_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    # Support both API key and user_id query param for backward compatibility
    user_id: Optional[int] = Query(None)
):
    """
    Get usage statistics for the authenticated user or specified user_id.
    Supports API key authentication via X-API-Key header or user_id query param.
    """
    from ..api_auth import get_current_user

    # Try to get authenticated user via API key
    try:
        user = await get_current_user(request, None, None, db)
    except HTTPException:
        # If API key auth fails, try user_id query param (backward compatibility)
        if user_id:
            user = crud.get_user(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            # Track usage for this request
            usage_log = models.UsageLog(
                user_id=user.id,
                endpoint="/api/usage/stats",
                method="GET",
                authenticated_via="user_id_param"
            )
            db.add(usage_log)
            db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Provide X-API-Key header or user_id query parameter."
            )

    # Get usage stats
    daily_usage = crud.get_user_usage_stats(db, user.id, days)
    total_count = crud.get_total_usage_count(db, user.id)

    return schemas.UserUsageStats(
        daily_usage=[schemas.DailyUsageStat(**stat) for stat in daily_usage],
        total_count=total_count
    )


@router.get("/api/admin/usage/all", response_model=List[schemas.AllUsersUsageStats])
async def get_all_users_usage_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    # Support both API key and user_id query param for backward compatibility
    user_id: Optional[int] = Query(None)
):
    """
    Get usage statistics for all users (admin endpoint).
    Supports API key authentication via X-API-Key header or user_id query param.
    """
    from ..api_auth import get_current_user

    # Try to get authenticated user
    try:
        user = await get_current_user(request, None, None, db)
    except HTTPException:
        # If API key auth fails, try user_id query param (backward compatibility)
        if user_id:
            user = crud.get_user(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            # Track usage for this request
            usage_log = models.UsageLog(
                user_id=user.id,
                endpoint="/api/admin/usage/all",
                method="GET",
                authenticated_via="user_id_param"
            )
            db.add(usage_log)
            db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Provide X-API-Key header or user_id query parameter."
            )

    # Require admin access
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Get all users usage stats
    all_stats = crud.get_all_users_usage_stats(db, days)

    return [schemas.AllUsersUsageStats(**stat) for stat in all_stats]
