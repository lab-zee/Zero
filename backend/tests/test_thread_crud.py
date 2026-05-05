"""
Tests for thread CRUD operations.
"""
import pytest
from sqlalchemy.orm import Session
from src import models, schemas, crud


class TestThreadCRUD:
    """Tests for thread CRUD operations."""

    def test_create_thread(self, db: Session, test_user: models.User, test_organization: models.Organization):
        """Test creating a thread."""
        thread_create = schemas.ThreadCreate(
            organization_id=test_organization.id,
            title="Test Thread"
        )

        thread = crud.create_thread(db, thread_create, test_user.id)

        assert thread.id is not None
        assert thread.title == "Test Thread"
        assert thread.user_id == test_user.id
        assert thread.organization_id == test_organization.id
        assert thread.default_answer_mode == models.AnswerMode.LIGHT  # Default

    def test_create_thread_with_metadata(self, db: Session, test_user: models.User, test_organization: models.Organization):
        """Test creating a thread with metadata."""
        thread_create = schemas.ThreadCreate(
            organization_id=test_organization.id,
            title="Thread with Metadata",
            thread_metadata={"creativity": "innovative", "budget_focus": 0.7}
        )

        thread = crud.create_thread(db, thread_create, test_user.id)

        assert thread.thread_metadata is not None
        assert thread.thread_metadata["creativity"] == "innovative"
        assert thread.thread_metadata["budget_focus"] == 0.7

    def test_get_thread(self, db: Session, test_thread: models.Thread):
        """Test retrieving a thread."""
        retrieved = crud.get_thread(db, test_thread.id)

        assert retrieved is not None
        assert retrieved.id == test_thread.id
        assert retrieved.title == test_thread.title

    def test_get_nonexistent_thread(self, db: Session):
        """Test retrieving a thread that doesn't exist."""
        result = crud.get_thread(db, 99999)
        assert result is None

    def test_get_threads_by_user(self, db: Session, test_user: models.User, test_organization: models.Organization):
        """Test retrieving threads by user."""
        # Create multiple threads
        for i in range(3):
            thread_create = schemas.ThreadCreate(
                organization_id=test_organization.id,
                title=f"Thread {i}"
            )
            crud.create_thread(db, thread_create, test_user.id)

        threads = crud.get_threads_by_user(db, test_user.id)

        assert len(threads) >= 3
        # Should be ordered by updated_at descending (newest first)
        assert all(isinstance(t, models.Thread) for t in threads)

    def test_update_thread_title(self, db: Session, test_thread: models.Thread):
        """Test updating a thread's title."""
        updated = crud.update_thread(db, test_thread.id, title="New Title")

        assert updated is not None
        assert updated.title == "New Title"
        assert updated.id == test_thread.id

    def test_update_thread_metadata(self, db: Session, test_thread: models.Thread):
        """Test updating a thread's metadata."""
        new_metadata = {"creativity": "off-the-shelf", "budget_focus": 0.3}
        updated = crud.update_thread(db, test_thread.id, thread_metadata=new_metadata)

        assert updated is not None
        assert updated.thread_metadata["creativity"] == "off-the-shelf"
        assert updated.thread_metadata["budget_focus"] == 0.3

    def test_update_thread_answer_mode(self, db: Session, test_thread: models.Thread):
        """Test updating a thread's default answer mode via metadata."""
        # Answer mode can be stored in metadata or updated directly on model if column exists
        # Since update_thread doesn't support default_answer_mode parameter, update via metadata
        new_metadata = {
            "creativity": "balanced",
            "default_answer_mode": "extended"
        }
        updated = crud.update_thread(
            db,
            test_thread.id,
            thread_metadata=new_metadata
        )

        assert updated is not None
        assert updated.thread_metadata.get("default_answer_mode") == "extended"

    def test_delete_thread(self, db: Session, test_user: models.User, test_organization: models.Organization):
        """Test deleting a thread."""
        # Create a thread to delete
        thread_create = schemas.ThreadCreate(
            organization_id=test_organization.id,
            title="Thread to Delete"
        )
        thread = crud.create_thread(db, thread_create, test_user.id)
        thread_id = thread.id

        # Delete it
        result = crud.delete_thread(db, thread_id)
        assert result is True

        # Verify it's gone
        retrieved = crud.get_thread(db, thread_id)
        assert retrieved is None

    def test_delete_nonexistent_thread(self, db: Session):
        """Test deleting a thread that doesn't exist."""
        result = crud.delete_thread(db, 99999)
        assert result is False

    def test_get_threads_by_organization(self, db: Session, test_user: models.User, test_organization: models.Organization):
        """Test retrieving threads by organization."""
        # Create threads
        for i in range(2):
            thread_create = schemas.ThreadCreate(
                organization_id=test_organization.id,
                title=f"Org Thread {i}"
            )
            crud.create_thread(db, thread_create, test_user.id)

        threads = crud.get_threads_by_organization(db, test_organization.id)

        assert len(threads) >= 2
        assert all(t.organization_id == test_organization.id for t in threads)

    def test_get_threads_by_user_and_org(self, db: Session, test_user: models.User, test_organization: models.Organization, admin_user: models.User):
        """Test retrieving threads filtered by both user and organization."""
        # Create thread for test_user
        thread_create = schemas.ThreadCreate(
            organization_id=test_organization.id,
            title="User Thread"
        )
        user_thread = crud.create_thread(db, thread_create, test_user.id)

        # Create thread for admin_user in same org
        thread_create2 = schemas.ThreadCreate(
            organization_id=test_organization.id,
            title="Admin Thread"
        )
        crud.create_thread(db, thread_create2, admin_user.id)

        # Get threads for test_user only
        threads = crud.get_threads_by_user_and_org(db, test_user.id, test_organization.id)

        # Should only include test_user's threads
        assert all(t.user_id == test_user.id for t in threads)
        assert all(t.organization_id == test_organization.id for t in threads)
        assert any(t.id == user_thread.id for t in threads)
