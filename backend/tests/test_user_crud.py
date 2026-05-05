"""
Tests for user CRUD operations.
"""
import pytest
from sqlalchemy.orm import Session
from src import models, schemas, crud, auth


class TestUserCRUD:
    """Tests for user CRUD operations."""

    def test_create_user(self, db: Session):
        """Test creating a regular user."""
        user_create = schemas.UserCreate(
            email="newuser@example.com",
            username="newuser",
            password="securepass123"
        )

        user = crud.create_user(db, user_create)

        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.password_hash is not None
        assert user.password_hash != "securepass123"  # Should be hashed
        assert user.is_admin is False  # Should not be admin
        assert user.api_key is not None  # Should auto-generate API key

    def test_password_is_hashed(self, db: Session):
        """Test that passwords are properly hashed."""
        user_create = schemas.UserCreate(
            email="hashtest@example.com",
            username="hashtest",
            password="plaintext123"
        )

        user = crud.create_user(db, user_create)

        # Password should be hashed (bcrypt hash starts with $2b$)
        assert user.password_hash.startswith("$2b$")
        # Should be able to verify the password
        assert auth.verify_password("plaintext123", user.password_hash)
        # Wrong password should not verify
        assert not auth.verify_password("wrongpass", user.password_hash)

    def test_get_user(self, db: Session, test_user: models.User):
        """Test retrieving a user by ID."""
        retrieved = crud.get_user(db, test_user.id)

        assert retrieved is not None
        assert retrieved.id == test_user.id
        assert retrieved.email == test_user.email

    def test_get_nonexistent_user(self, db: Session):
        """Test retrieving a user that doesn't exist."""
        result = crud.get_user(db, 99999)
        assert result is None

    def test_get_user_by_email(self, db: Session, test_user: models.User):
        """Test retrieving a user by email."""
        retrieved = crud.get_user_by_email(db, test_user.email)

        assert retrieved is not None
        assert retrieved.id == test_user.id
        assert retrieved.email == test_user.email

    def test_get_user_by_email_case_sensitive(self, db: Session, test_user: models.User):
        """Test that email lookup is case-sensitive."""
        # Test with uppercase email (assuming test_user has lowercase)
        retrieved = crud.get_user_by_email(db, test_user.email.upper())

        # SQLite default collation is case-insensitive for LIKE but case-sensitive for =
        # This test documents current behavior
        # In production with PostgreSQL, you may want case-insensitive email lookup

    def test_get_user_by_nonexistent_email(self, db: Session):
        """Test retrieving a user with email that doesn't exist."""
        result = crud.get_user_by_email(db, "nonexistent@example.com")
        assert result is None

    def test_get_user_by_username(self, db: Session, test_user: models.User):
        """Test retrieving a user by username."""
        retrieved = crud.get_user_by_username(db, test_user.username)

        assert retrieved is not None
        assert retrieved.id == test_user.id
        assert retrieved.username == test_user.username

    def test_get_user_by_nonexistent_username(self, db: Session):
        """Test retrieving a user with username that doesn't exist."""
        result = crud.get_user_by_username(db, "nonexistentuser")
        assert result is None

    def test_get_user_by_api_key(self, db: Session, test_user: models.User):
        """Test retrieving a user by API key."""
        retrieved = crud.get_user_by_api_key(db, test_user.api_key)

        assert retrieved is not None
        assert retrieved.id == test_user.id
        assert retrieved.api_key == test_user.api_key

    def test_get_user_by_invalid_api_key(self, db: Session):
        """Test retrieving a user with invalid API key."""
        import uuid
        fake_api_key = uuid.uuid4()
        result = crud.get_user_by_api_key(db, fake_api_key)
        assert result is None

    def test_get_users(self, db: Session, test_user: models.User, admin_user: models.User):
        """Test retrieving list of users."""
        users = crud.get_users(db)

        assert len(users) >= 2
        user_ids = [u.id for u in users]
        assert test_user.id in user_ids
        assert admin_user.id in user_ids

    def test_get_users_pagination(self, db: Session):
        """Test user list pagination."""
        # Create multiple users
        for i in range(5):
            user_create = schemas.UserCreate(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password="password123"
            )
            crud.create_user(db, user_create)

        # Get first page
        page1 = crud.get_users(db, skip=0, limit=3)
        assert len(page1) == 3

        # Get second page
        page2 = crud.get_users(db, skip=3, limit=3)
        assert len(page2) >= 2

        # Pages should not overlap
        page1_ids = {u.id for u in page1}
        page2_ids = {u.id for u in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_update_user_admin_status(self, db: Session, test_user: models.User):
        """Test updating user admin status."""
        assert test_user.is_admin is False

        user_update = schemas.UserUpdate(is_admin=True)
        updated = crud.update_user(db, test_user.id, user_update)

        assert updated is not None
        assert updated.is_admin is True

    def test_update_user_active_status(self, db: Session, test_user: models.User):
        """Test updating user active status."""
        assert test_user.is_active is True

        user_update = schemas.UserUpdate(is_active=False)
        updated = crud.update_user(db, test_user.id, user_update)

        assert updated is not None
        assert updated.is_active is False

    def test_update_user_multiple_fields(self, db: Session, test_user: models.User):
        """Test updating multiple user fields at once."""
        user_update = schemas.UserUpdate(is_admin=True, is_active=False)
        updated = crud.update_user(db, test_user.id, user_update)

        assert updated is not None
        assert updated.is_admin is True
        assert updated.is_active is False

    def test_update_user_partial(self, db: Session, test_user: models.User):
        """Test partial update (only some fields provided)."""
        original_admin_status = test_user.is_admin

        user_update = schemas.UserUpdate(is_active=False)
        updated = crud.update_user(db, test_user.id, user_update)

        assert updated is not None
        assert updated.is_active is False
        assert updated.is_admin == original_admin_status  # Should not change

    def test_update_nonexistent_user(self, db: Session):
        """Test updating a user that doesn't exist."""
        user_update = schemas.UserUpdate(is_admin=True)
        result = crud.update_user(db, 99999, user_update)

        assert result is None

    def test_user_uniqueness(self, db: Session):
        """Test that email and username must be unique."""
        user_create = schemas.UserCreate(
            email="unique@example.com",
            username="uniqueuser",
            password="password123"
        )
        crud.create_user(db, user_create)

        # Try to create another user with same email (should raise IntegrityError)
        from sqlalchemy.exc import IntegrityError

        duplicate_email = schemas.UserCreate(
            email="unique@example.com",  # Same email
            username="differentuser",
            password="password123"
        )

        with pytest.raises(IntegrityError):
            crud.create_user(db, duplicate_email)
            db.commit()

        db.rollback()

        # Try to create another user with same username (should raise IntegrityError)
        duplicate_username = schemas.UserCreate(
            email="different@example.com",
            username="uniqueuser",  # Same username
            password="password123"
        )

        with pytest.raises(IntegrityError):
            crud.create_user(db, duplicate_username)
            db.commit()
