"""
Tests for chat query CRUD operations and business logic.
"""
import pytest
from sqlalchemy.orm import Session
from src import models, schemas
from src.crud import chat_queries


class TestChatQueryCRUD:
    """Tests for chat query CRUD operations."""

    def test_create_chat_query(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test creating a chat query."""
        query_create = schemas.ChatQueryCreate(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="What is the meaning of life?",
            answer_mode="light"
        )

        db_query = chat_queries.create_chat_query(
            db,
            query_create,
            response="42",
            execution_trace={"nodes": [], "edges": []},
            content_structure={"summary": "The answer is 42"}
        )

        assert db_query.id is not None
        assert db_query.message == "What is the meaning of life?"
        assert db_query.response == "42"
        assert db_query.answer_mode == "light"
        assert db_query.execution_trace is not None
        assert db_query.content_structure is not None

    def test_update_chat_query(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test updating a chat query."""
        # Create initial query
        query_create = schemas.ChatQueryCreate(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="Initial question",
            answer_mode="light"
        )

        db_query = chat_queries.create_chat_query(
            db,
            query_create,
            response="",  # Empty initially
        )

        # Update with response
        updated_query = chat_queries.update_chat_query(
            db,
            db_query.id,
            response="Updated response",
            execution_trace={"nodes": [{"id": "1", "type": "agent"}], "edges": []},
            content_structure={"summary": "Updated summary"}
        )

        assert updated_query is not None
        assert updated_query.response == "Updated response"
        assert updated_query.execution_trace is not None
        assert updated_query.content_structure is not None

    def test_update_nonexistent_query(self, db: Session):
        """Test updating a query that doesn't exist."""
        result = chat_queries.update_chat_query(
            db,
            99999,  # Non-existent ID
            response="Should not work"
        )

        assert result is None

    def test_sanitize_null_characters(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test that null characters are sanitized before DB insertion."""
        query_create = schemas.ChatQueryCreate(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="Message with \u0000 null char",
            answer_mode="light"
        )

        db_query = chat_queries.create_chat_query(
            db,
            query_create,
            response="Response with \u0000 null char",
            execution_trace={
                "nodes": [],
                "edges": [],
                "metadata": {"data": "value with \u0000 null"}
            }
        )

        # Verify null characters were removed
        assert "\u0000" not in db_query.message
        assert "\u0000" not in db_query.response
        assert "\u0000" not in str(db_query.execution_trace)

    def test_error_persistence(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test that errors are persisted to execution_trace metadata."""
        query_create = schemas.ChatQueryCreate(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="Question that will error",
            answer_mode="light"
        )

        db_query = chat_queries.create_chat_query(
            db,
            query_create,
            response="",
        )

        # Update with error
        updated_query = chat_queries.update_chat_query(
            db,
            db_query.id,
            error="Something went wrong"
        )

        assert updated_query is not None
        assert updated_query.execution_trace is not None
        assert "error" in updated_query.execution_trace["metadata"]
        assert updated_query.execution_trace["metadata"]["error"] == "Something went wrong"
        # Should have auto-generated error response
        assert "An error occurred" in updated_query.response

    def test_get_chat_queries_by_thread(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test retrieving chat queries by thread."""
        # Create multiple queries
        for i in range(3):
            query_create = schemas.ChatQueryCreate(
                thread_id=test_thread.id,
                user_id=test_user.id,
                organization_id=test_organization.id,
                message=f"Question {i}",
                answer_mode="light"
            )
            chat_queries.create_chat_query(
                db,
                query_create,
                response=f"Answer {i}"
            )

        # Retrieve queries
        queries = chat_queries.get_chat_queries_by_thread(db, test_thread.id)

        assert len(queries) == 3
        # Should be ordered by created_at
        assert queries[0].message == "Question 0"
        assert queries[2].message == "Question 2"

    def test_get_chat_query(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test retrieving a single chat query."""
        query_create = schemas.ChatQueryCreate(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="Single question",
            answer_mode="light"
        )

        created = chat_queries.create_chat_query(
            db,
            query_create,
            response="Single answer"
        )

        # Retrieve query
        retrieved = chat_queries.get_chat_query(db, created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.message == "Single question"

    def test_incremental_updates(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test incremental updates during execution (simulating streaming)."""
        query_create = schemas.ChatQueryCreate(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="Question with incremental updates",
            answer_mode="light"
        )

        # Create initial empty query
        db_query = chat_queries.create_chat_query(
            db,
            query_create,
            response="",
        )

        # Update 1: Add trace
        chat_queries.update_chat_query(
            db,
            db_query.id,
            execution_trace={"nodes": [{"id": "1"}], "edges": []}
        )

        # Update 2: Add more trace nodes
        chat_queries.update_chat_query(
            db,
            db_query.id,
            execution_trace={"nodes": [{"id": "1"}, {"id": "2"}], "edges": [{"source": "1", "target": "2"}]}
        )

        # Update 3: Add final response
        final = chat_queries.update_chat_query(
            db,
            db_query.id,
            response="Final answer",
            content_structure={"summary": "Final summary"}
        )

        # Verify all updates persisted
        assert final is not None
        assert final.response == "Final answer"
        assert len(final.execution_trace["nodes"]) == 2
        assert final.content_structure is not None

    def test_execution_times_in_metadata(self, db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test that execution times are stored in trace metadata."""
        query_create = schemas.ChatQueryCreate(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="Question with timing",
            answer_mode="light"
        )

        execution_times = {
            "total_time": 10.5,
            "agent_time": 8.2,
            "tool_time": 2.3
        }

        db_query = chat_queries.create_chat_query(
            db,
            query_create,
            response="Answer",
            execution_trace={"nodes": [], "edges": []},
            execution_times=execution_times
        )

        # Verify execution times are in metadata
        assert "metadata" in db_query.execution_trace
        assert "execution_times" in db_query.execution_trace["metadata"]
        assert db_query.execution_trace["metadata"]["execution_times"]["total_time"] == 10.5
