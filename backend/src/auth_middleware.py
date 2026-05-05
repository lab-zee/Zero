"""
Auth middleware that validates API keys on all /api/ routes.
Public endpoints (login, register, reset-password, health) are excluded.
"""
import os
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from .database import SessionLocal
from . import crud


# Paths that don't require authentication
PUBLIC_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/reset-password",
    "/api",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Path prefixes that don't require authentication
PUBLIC_PREFIXES = (
    "/uploads/",
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for non-API routes, public paths, and prefixes
        if not path.startswith("/api") and path not in ("/health",):
            return await call_next(request)

        if path in PUBLIC_PATHS:
            return await call_next(request)

        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip API key validation in test mode (test DB is injected separately)
        if os.environ.get("TESTING") == "1":
            return await call_next(request)

        # Validate API key
        api_key = request.headers.get("x-api-key")

        if not api_key:
            # Also check Authorization header
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                api_key = auth_header[7:]

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required."},
            )

        # Validate the API key against the database
        db = SessionLocal()
        try:
            try:
                api_key_uuid = uuid.UUID(api_key)
            except (ValueError, TypeError):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid API key format."},
                )

            user = crud.get_user_by_api_key(db, api_key_uuid)
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or expired API key."},
                )

            if not user.is_active:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Account has been disabled."},
                )

        finally:
            db.close()

        return await call_next(request)
