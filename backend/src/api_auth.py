"""
API authentication supporting both API key and bearer token authentication.
"""
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from .database import get_db
from . import crud, models

security = HTTPBearer(auto_error=False)


def _resolve_authenticated_user(request: Request, db: Session) -> Optional[models.User]:
    """Return the authenticated User for this request.

    Fast path: AuthMiddleware populated `request.state` during API key validation.
    Fallback: look up the `x-api-key` header against the request-scoped DB session.
    The fallback covers test mode (middleware short-circuits on TESTING=1) and
    defends against middleware misconfiguration.
    """
    user_id = getattr(request.state, "authenticated_user_id", None)
    if user_id is not None:
        return crud.get_user(db, user_id)

    api_key = request.headers.get("x-api-key")
    if not api_key:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
    if not api_key:
        return None
    try:
        return crud.get_user_by_api_key(db, uuid.UUID(api_key))
    except (ValueError, TypeError):
        return None


def authenticated_user_id(
    request: Request,
    db: Session = Depends(get_db),
) -> int:
    """Return the user_id bound to this request by AuthMiddleware (from the API key).

    Use this instead of a `user_id` query parameter — query params are attacker-controlled.
    """
    user = _resolve_authenticated_user(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    # Cache for downstream dependencies (e.g., require_admin_user).
    request.state.authenticated_user_id = user.id
    request.state.authenticated_is_admin = user.is_admin
    return user.id


def require_admin_user(
    request: Request,
    db: Session = Depends(get_db),
) -> int:
    """Same as `authenticated_user_id`, but 403s for non-admins."""
    user_id = authenticated_user_id(request, db)
    if not getattr(request.state, "authenticated_is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user_id

async def get_current_user(
    request: Request,
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Authenticate user via API key (X-API-Key header) or Bearer token.
    Returns the authenticated user or raises HTTPException.
    """
    # Try API key first (X-API-Key header)
    # Also check Authorization header with "Bearer" or just the API key
    api_key = x_api_key
    if not api_key and authorization:
        # Check if it's an API key in Authorization header (format: "Bearer <api_key>" or just "<api_key>")
        cred = authorization.credentials if hasattr(authorization, 'credentials') else str(authorization)
        # Try as API key first
        try:
            api_key_uuid = uuid.UUID(cred)
            user = crud.get_user_by_api_key(db, api_key_uuid)
            if user:
                _track_usage(db, user.id, request.url.path, request.method, "api_key")
                return user
        except (ValueError, TypeError):
            pass
    
    if api_key:
        try:
            api_key_uuid = uuid.UUID(x_api_key)
            user = crud.get_user_by_api_key(db, api_key_uuid)
            if user:
                # Track usage
                _track_usage(db, user.id, request.url.path, request.method, "api_key")
                return user
        except (ValueError, TypeError):
            pass  # Invalid UUID format, try bearer token
    
    # Try Bearer token (Authorization header)
    if authorization and authorization.credentials:
        # For now, bearer token is just the user_id as a string
        # In production, you'd decode a JWT token here
        try:
            user_id = int(authorization.credentials)
            user = crud.get_user(db, user_id)
            if user:
                # Track usage
                _track_usage(db, user.id, request.url.path, request.method, "bearer_token")
                return user
        except (ValueError, TypeError):
            pass
    
    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either X-API-Key header or Authorization Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

def _track_usage(db: Session, user_id: int, endpoint: str, method: str, auth_method: str):
    """Track API usage for a user."""
    try:
        from . import models
        usage_log = models.UsageLog(
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            authenticated_via=auth_method
        )
        db.add(usage_log)
        db.commit()
    except Exception:
        # Don't fail the request if usage tracking fails
        db.rollback()
        pass

