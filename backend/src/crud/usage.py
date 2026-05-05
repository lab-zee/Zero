"""
CRUD operations for usage tracking.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import List, Dict, Any
from .. import models


def get_user_usage_stats(
    db: Session,
    user_id: int,
    days: int = 30
) -> List[Dict[str, Any]]:
    """
    Get daily usage statistics for a user over the specified number of days.
    Returns a list of dicts with 'date' and 'count' keys.
    """
    start_date = datetime.now() - timedelta(days=days)
    
    # Query usage logs grouped by date
    results = db.query(
        func.date(models.UsageLog.created_at).label('date'),
        func.count(models.UsageLog.id).label('count')
    ).filter(
        and_(
            models.UsageLog.user_id == user_id,
            models.UsageLog.created_at >= start_date
        )
    ).group_by(
        func.date(models.UsageLog.created_at)
    ).order_by(
        func.date(models.UsageLog.created_at)
    ).all()
    
    # Convert to list of dicts
    stats = [{"date": str(result.date), "count": result.count} for result in results]
    
    # Fill in missing days with 0
    date_list = []
    current_date = start_date.date()
    end_date = datetime.now().date()
    
    while current_date <= end_date:
        # Find matching stat or use 0
        matching_stat = next((s for s in stats if s["date"] == str(current_date)), None)
        date_list.append({
            "date": str(current_date),
            "count": matching_stat["count"] if matching_stat else 0
        })
        current_date += timedelta(days=1)
    
    return date_list


def get_all_users_usage_stats(
    db: Session,
    days: int = 30
) -> List[Dict[str, Any]]:
    """
    Get usage statistics for all users over the specified number of days.
    Returns a list of dicts with user info and daily usage.
    """
    start_date = datetime.now() - timedelta(days=days)
    
    # Query usage logs with user info, grouped by user and date
    results = db.query(
        models.User.id,
        models.User.username,
        models.User.email,
        func.date(models.UsageLog.created_at).label('date'),
        func.count(models.UsageLog.id).label('count')
    ).join(
        models.UsageLog, models.User.id == models.UsageLog.user_id
    ).filter(
        models.UsageLog.created_at >= start_date
    ).group_by(
        models.User.id,
        models.User.username,
        models.User.email,
        func.date(models.UsageLog.created_at)
    ).order_by(
        models.User.id,
        func.date(models.UsageLog.created_at)
    ).all()
    
    # Group by user
    user_stats = {}
    for result in results:
        user_id = result.id
        if user_id not in user_stats:
            user_stats[user_id] = {
                "user_id": user_id,
                "username": result.username,
                "email": result.email,
                "daily_usage": []
            }
        user_stats[user_id]["daily_usage"].append({
            "date": str(result.date),
            "count": result.count
        })
    
    # Fill in missing days for each user
    end_date = datetime.now().date()
    for user_id, stats in user_stats.items():
        daily_usage = stats["daily_usage"]
        current_date = start_date.date()
        filled_usage = []
        
        while current_date <= end_date:
            matching_stat = next((s for s in daily_usage if s["date"] == str(current_date)), None)
            filled_usage.append({
                "date": str(current_date),
                "count": matching_stat["count"] if matching_stat else 0
            })
            current_date += timedelta(days=1)
        
        stats["daily_usage"] = filled_usage
    
    return list(user_stats.values())


def get_total_usage_count(db: Session, user_id: int) -> int:
    """Get total number of API calls for a user."""
    return db.query(models.UsageLog).filter(models.UsageLog.user_id == user_id).count()

