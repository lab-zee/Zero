from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..api_auth import get_current_user
from .. import schemas, crud, auth, models

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/verify", response_model=schemas.UserResponse)
async def verify_session(current_user: models.User = Depends(get_current_user)):
    """
    Verify the current session is still valid.
    Returns the user if the API key is valid, 401 if it's been rotated/invalidated.
    """
    return current_user


@router.post("/reset-password", response_model=schemas.UserResponse)
async def reset_password(request: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    """
    Reset password using a valid reset token.
    This is a public endpoint - no authentication required.
    After reset, the user's API key is rotated (invalidating old sessions).
    """
    user = crud.get_user_by_reset_token(db, request.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    new_password_hash = auth.hash_password(request.new_password)

    updated_user = crud.reset_password(db, request.token, new_password_hash)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reset password"
        )

    return updated_user


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
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


@router.post("/login", response_model=schemas.UserResponse)
async def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    # Find user by email
    db_user = crud.get_user_by_email(db, email=credentials.email)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    # Verify password
    if not auth.verify_password(credentials.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    return db_user
