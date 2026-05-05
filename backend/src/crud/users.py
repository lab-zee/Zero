from sqlalchemy.orm import Session
from .. import models, schemas
from .. import auth
from typing import Optional, List
import uuid
import secrets
from datetime import datetime, timedelta, timezone

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_api_key(db: Session, api_key: uuid.UUID) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.api_key == api_key).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    password_hash = auth.hash_password(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        password_hash=password_hash,
        is_admin=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def admin_create_user(db: Session, user: schemas.AdminUserCreate) -> models.User:
    """Create a user account on behalf of someone (admin only). Uses the is_admin flag from the request."""
    password_hash = auth.hash_password(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        password_hash=password_hash,
        is_admin=user.is_admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    """Update user properties (admin only - for managing users)"""
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    # Update only the fields that are provided
    if user_update.is_admin is not None:
        db_user.is_admin = user_update.is_admin
    if user_update.is_active is not None:
        db_user.is_active = user_update.is_active

    db.commit()
    db.refresh(db_user)
    return db_user


def rotate_user_api_key(db: Session, user_id: int) -> Optional[models.User]:
    """Rotate API key for a single user, invalidating their current session."""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    db_user.api_key = uuid.uuid4()
    db.commit()
    db.refresh(db_user)
    return db_user


def rotate_all_api_keys(db: Session) -> int:
    """Rotate API keys for ALL users, invalidating all sessions. Returns count of affected users."""
    users = db.query(models.User).all()
    count = 0
    for user in users:
        user.api_key = uuid.uuid4()
        count += 1
    db.commit()
    return count


def generate_password_reset_token(db: Session, user_id: int, expires_hours: int = 1) -> Optional[str]:
    """Generate a password reset token for a user. Returns the token string or None if user not found."""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    token = secrets.token_urlsafe(32)
    db_user.password_reset_token = token
    db_user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    db.commit()
    db.refresh(db_user)
    return token


def get_user_by_reset_token(db: Session, token: str) -> Optional[models.User]:
    """Find a user by their password reset token. Returns None if token is invalid or expired."""
    db_user = db.query(models.User).filter(
        models.User.password_reset_token == token
    ).first()
    if not db_user:
        return None
    if db_user.password_reset_expires is None or db_user.password_reset_expires < datetime.now(timezone.utc):
        return None
    return db_user


def reset_password(db: Session, token: str, new_password_hash: str) -> Optional[models.User]:
    """Reset a user's password using a valid token. Also rotates the API key and clears the token."""
    db_user = get_user_by_reset_token(db, token)
    if not db_user:
        return None
    db_user.password_hash = new_password_hash
    db_user.password_reset_token = None
    db_user.password_reset_expires = None
    db_user.api_key = uuid.uuid4()
    db.commit()
    db.refresh(db_user)
    return db_user

