"""
Tests for database models.
"""
import pytest
from sqlalchemy.orm import Session
from src import models, auth


class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, db: Session):
        """Test creating a user."""
        user = models.User(
            email="newuser@example.com",
            username="newuser",
            password_hash=auth.hash_password("password123"),
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.is_admin is False
        assert user.api_key is not None
        assert user.created_at is not None

    def test_new_user_is_not_admin_by_default(self, db: Session):
        """Test that newly created users are not admin by default."""
        from src.crud.users import create_user
        from src.schemas import UserCreate

        user_data = UserCreate(
            email="regular@example.com",
            username="regular_user",
            password="password123"
        )
        user = create_user(db, user_data)

        assert user.is_admin is False

    def test_user_active_by_default(self, db: Session):
        """Test that users are active by default."""
        user = models.User(
            email="active@example.com",
            username="activeuser",
            password_hash=auth.hash_password("password123"),
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.is_active is True

    def test_deactivate_user(self, db: Session):
        """Test deactivating a user."""
        from src.crud.users import create_user, update_user
        from src.schemas import UserCreate, UserUpdate

        user_data = UserCreate(
            email="toban@example.com",
            username="toban_user",
            password="password123"
        )
        user = create_user(db, user_data)
        assert user.is_active is True

        # Deactivate user
        update_data = UserUpdate(is_active=False)
        updated_user = update_user(db, user.id, update_data)

        assert updated_user.is_active is False


class TestOrganizationModel:
    """Tests for Organization model."""

    def test_create_organization(self, db: Session, test_user: models.User):
        """Test creating an organization."""
        org = models.Organization(
            name="Test Org",
            description="Test description",
            owner_id=test_user.id,
            org_metadata={"industry": "Tech"}
        )
        db.add(org)
        db.commit()
        db.refresh(org)

        assert org.id is not None
        assert org.name == "Test Org"
        assert org.owner_id == test_user.id
        assert org.org_metadata == {"industry": "Tech"}
        assert org.created_at is not None

    def test_organization_owner_relationship(self, db: Session, test_user: models.User, test_organization: models.Organization):
        """Test organization-owner relationship."""
        assert test_organization.owner.id == test_user.id
        assert test_organization in test_user.owned_organizations


class TestThreadModel:
    """Tests for Thread model."""

    def test_create_thread(self, db: Session, test_user: models.User, test_organization: models.Organization):
        """Test creating a thread."""
        thread = models.Thread(
            user_id=test_user.id,
            organization_id=test_organization.id,
            title="New Thread",
            default_answer_mode=models.AnswerMode.EXTENDED
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)

        assert thread.id is not None
        assert thread.title == "New Thread"
        assert thread.default_answer_mode == models.AnswerMode.EXTENDED
        assert thread.created_at is not None

    def test_thread_relationships(self, db: Session, test_thread: models.Thread, test_user: models.User, test_organization: models.Organization):
        """Test thread relationships."""
        assert test_thread.user.id == test_user.id
        assert test_thread.organization.id == test_organization.id


class TestChatQueryModel:
    """Tests for ChatQuery model."""

    def test_create_query(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test creating a chat query."""
        query = models.ChatQuery(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="Test question?",
            response="Test answer.",
            answer_mode=models.AnswerMode.SUMMARY
        )
        db.add(query)
        db.commit()
        db.refresh(query)

        assert query.id is not None
        assert query.message == "Test question?"
        assert query.response == "Test answer."
        assert query.answer_mode == models.AnswerMode.SUMMARY
        assert query.created_at is not None

    def test_query_with_content_structure(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test query with content structure."""
        content_structure = {
            "summary": "Test summary",
            "visualizations": [{"type": "bar", "data": {}}],
            "references": [{"number": 1, "title": "Test"}]
        }

        query = models.ChatQuery(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="Test question?",
            content_structure=content_structure
        )
        db.add(query)
        db.commit()
        db.refresh(query)

        assert query.content_structure == content_structure

    def test_query_followup_questions(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test query with follow-up questions."""
        followup_questions = [
            {"question": "What about competitors?", "rationale": "To understand landscape"},
            {"question": "What are the risks?", "rationale": "To assess challenges"}
        ]

        query = models.ChatQuery(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="Test question?",
            followup_questions=followup_questions
        )
        db.add(query)
        db.commit()
        db.refresh(query)

        assert query.followup_questions == followup_questions
        assert len(query.followup_questions) == 2

    def test_reask_query(self, db: Session, test_query: models.ChatQuery, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test re-asking a query with different mode."""
        reask_query = models.ChatQuery(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message=test_query.message,
            answer_mode=models.AnswerMode.EXTENDED,
            reask_of_query_id=test_query.id
        )
        db.add(reask_query)
        db.commit()
        db.refresh(reask_query)

        assert reask_query.reask_of_query_id == test_query.id
        assert reask_query.answer_mode == models.AnswerMode.EXTENDED
        assert reask_query.message == test_query.message


class TestAnswerMode:
    """Tests for AnswerMode enum."""

    def test_answer_mode_values(self):
        """Test AnswerMode enum values."""
        assert models.AnswerMode.SUMMARY.value == "summary"
        assert models.AnswerMode.LIGHT.value == "light"
        assert models.AnswerMode.EXTENDED.value == "extended"

    def test_answer_mode_default(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test default answer mode."""
        query = models.ChatQuery(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="Test"
        )
        db.add(query)
        db.commit()
        db.refresh(query)

        # Default should be LIGHT
        assert query.answer_mode == models.AnswerMode.LIGHT
