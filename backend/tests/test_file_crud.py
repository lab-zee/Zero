"""
Tests for file CRUD operations.
"""
import os
import pytest
from sqlalchemy.orm import Session
from src import models, schemas, crud
from unittest.mock import patch, MagicMock


class TestFileCRUD:
    """Tests for file CRUD operations."""

    @patch('src.crud.files.save_file')
    @patch('src.crud.files.generate_unique_filename')
    @patch('src.crud.files.validate_file_type')
    def test_create_file(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        mock_save: MagicMock,
        db: Session,
        test_user: models.User,
        test_organization: models.Organization
    ):
        """Test creating a file."""
        # Setup mocks
        mock_validate.return_value = (True, None)
        mock_generate.return_value = "unique_test_file.pdf"
        mock_save.return_value = "/uploads/unique_test_file.pdf"

        file_content = b"fake pdf content"

        db_file = crud.create_file(
            db=db,
            user_id=test_user.id,
            organization_id=test_organization.id,
            original_filename="test_file.pdf",
            file_content=file_content,
            content_type="application/pdf"
        )

        assert db_file.id is not None
        assert db_file.original_filename == "test_file.pdf"
        assert db_file.filename == "unique_test_file.pdf"
        assert db_file.file_path == "/uploads/unique_test_file.pdf"
        assert db_file.content_type == "application/pdf"
        assert db_file.file_size == len(file_content)
        assert db_file.user_id == test_user.id
        assert db_file.organization_id == test_organization.id

        # Verify mocks were called
        mock_validate.assert_called_once_with("test_file.pdf", "application/pdf")
        mock_generate.assert_called_once_with("test_file.pdf")
        mock_save.assert_called_once_with(file_content, "unique_test_file.pdf")

    @patch('src.crud.files.save_file')
    @patch('src.crud.files.generate_unique_filename')
    def test_create_file_skip_validation(
        self,
        mock_generate: MagicMock,
        mock_save: MagicMock,
        db: Session,
        test_user: models.User,
        test_organization: models.Organization
    ):
        """Test creating a file with validation skipped (for programmatic files)."""
        mock_generate.return_value = "generated_image.png"
        mock_save.return_value = "/uploads/generated_image.png"

        file_content = b"fake image content"

        db_file = crud.create_file(
            db=db,
            user_id=test_user.id,
            organization_id=test_organization.id,
            original_filename="generated_image.png",
            file_content=file_content,
            content_type="image/png",
            skip_validation=True
        )

        assert db_file.id is not None
        assert db_file.filename == "generated_image.png"

    @patch('src.crud.files.validate_file_type')
    def test_create_file_invalid_type(
        self,
        mock_validate: MagicMock,
        db: Session,
        test_user: models.User,
        test_organization: models.Organization
    ):
        """Test that invalid file types are rejected."""
        mock_validate.return_value = (False, "Invalid file type")

        with pytest.raises(ValueError, match="Invalid file type"):
            crud.create_file(
                db=db,
                user_id=test_user.id,
                organization_id=test_organization.id,
                original_filename="malware.exe",
                file_content=b"malicious content",
                content_type="application/x-msdownload"
            )

    @patch('src.crud.files.save_file')
    @patch('src.crud.files.generate_unique_filename')
    @patch('src.crud.files.validate_file_type')
    def test_get_file(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        mock_save: MagicMock,
        db: Session,
        test_user: models.User,
        test_organization: models.Organization
    ):
        """Test retrieving a file."""
        mock_validate.return_value = (True, None)
        mock_generate.return_value = "test.pdf"
        mock_save.return_value = "/uploads/test.pdf"

        # Create file
        created = crud.create_file(
            db=db,
            user_id=test_user.id,
            organization_id=test_organization.id,
            original_filename="test.pdf",
            file_content=b"content",
            content_type="application/pdf"
        )

        # Retrieve file
        retrieved = crud.get_file(db, created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.filename == "test.pdf"

    def test_get_nonexistent_file(self, db: Session):
        """Test retrieving a file that doesn't exist."""
        result = crud.get_file(db, 99999)
        assert result is None

    @patch('src.crud.files.save_file')
    @patch('src.crud.files.generate_unique_filename')
    @patch('src.crud.files.validate_file_type')
    def test_get_files_by_user(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        mock_save: MagicMock,
        db: Session,
        test_user: models.User,
        test_organization: models.Organization
    ):
        """Test retrieving files by user."""
        mock_validate.return_value = (True, None)
        mock_save.return_value = "/uploads/test.pdf"

        # Create multiple files
        for i in range(3):
            mock_generate.return_value = f"file_{i}.pdf"
            crud.create_file(
                db=db,
                user_id=test_user.id,
                organization_id=test_organization.id,
                original_filename=f"file_{i}.pdf",
                file_content=b"content",
                content_type="application/pdf"
            )

        files = crud.get_files_by_user(db, test_user.id)

        assert len(files) == 3
        assert all(f.user_id == test_user.id for f in files)

    @patch('src.crud.files.save_file')
    @patch('src.crud.files.generate_unique_filename')
    @patch('src.crud.files.validate_file_type')
    def test_get_files_by_organization(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        mock_save: MagicMock,
        db: Session,
        test_user: models.User,
        test_organization: models.Organization
    ):
        """Test retrieving files by organization."""
        mock_validate.return_value = (True, None)
        mock_save.return_value = "/uploads/test.pdf"

        # Create files
        for i in range(2):
            mock_generate.return_value = f"org_file_{i}.pdf"
            crud.create_file(
                db=db,
                user_id=test_user.id,
                organization_id=test_organization.id,
                original_filename=f"org_file_{i}.pdf",
                file_content=b"content",
                content_type="application/pdf"
            )

        files = crud.get_files_by_organization(db, test_organization.id)

        assert len(files) == 2
        assert all(f.organization_id == test_organization.id for f in files)

    @patch('src.vector_store.remove_document_from_store')
    @patch('src.storage.delete_file_from_storage')
    @patch('src.crud.files.save_file')
    @patch('src.crud.files.generate_unique_filename')
    @patch('src.crud.files.validate_file_type')
    def test_delete_file_by_owner(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        mock_save: MagicMock,
        mock_delete_storage: MagicMock,
        mock_remove_vector: MagicMock,
        db: Session,
        test_user: models.User,
        test_organization: models.Organization
    ):
        """Test that file owner can delete their file."""
        mock_validate.return_value = (True, None)
        mock_generate.return_value = "to_delete.pdf"
        mock_save.return_value = "/uploads/to_delete.pdf"

        # Create file
        db_file = crud.create_file(
            db=db,
            user_id=test_user.id,
            organization_id=test_organization.id,
            original_filename="to_delete.pdf",
            file_content=b"content",
            content_type="application/pdf"
        )

        # Delete as owner
        result = crud.delete_file(db, db_file.id, test_user.id)

        assert result is True
        mock_delete_storage.assert_called_once_with("/uploads/to_delete.pdf")

        # Verify file is deleted from database
        deleted = crud.get_file(db, db_file.id)
        assert deleted is None

    @patch('src.storage.delete_file_from_storage')
    @patch('src.crud.files.save_file')
    @patch('src.crud.files.generate_unique_filename')
    @patch('src.crud.files.validate_file_type')
    def test_delete_file_unauthorized(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        mock_save: MagicMock,
        mock_delete_storage: MagicMock,
        db: Session,
        test_user: models.User,
        admin_user: models.User,
        test_organization: models.Organization
    ):
        """Test that non-owner without permissions cannot delete file."""
        mock_validate.return_value = (True, None)
        mock_generate.return_value = "protected.pdf"
        mock_save.return_value = "/uploads/protected.pdf"

        # Create file as test_user
        db_file = crud.create_file(
            db=db,
            user_id=test_user.id,
            organization_id=test_organization.id,
            original_filename="protected.pdf",
            file_content=b"content",
            content_type="application/pdf"
        )

        # Try to delete as admin_user (who is not in the organization)
        result = crud.delete_file(db, db_file.id, admin_user.id)

        assert result is False
        mock_delete_storage.assert_not_called()

        # Verify file still exists
        still_exists = crud.get_file(db, db_file.id)
        assert still_exists is not None

    def test_delete_nonexistent_file(self, db: Session, test_user: models.User):
        """Test deleting a file that doesn't exist."""
        result = crud.delete_file(db, 99999, test_user.id)
        assert result is False

    @patch('src.crud.files.save_file')
    @patch('src.crud.files.generate_unique_filename')
    @patch('src.crud.files.validate_file_type')
    def test_associate_files_with_query(
        self,
        mock_validate: MagicMock,
        mock_generate: MagicMock,
        mock_save: MagicMock,
        db: Session,
        test_user: models.User,
        test_organization: models.Organization,
        test_thread: models.Thread
    ):
        """Test associating files with a chat query."""
        mock_validate.return_value = (True, None)
        mock_save.return_value = "/uploads/test.pdf"

        # Create files
        file_ids = []
        for i in range(2):
            mock_generate.return_value = f"file_{i}.pdf"
            db_file = crud.create_file(
                db=db,
                user_id=test_user.id,
                organization_id=test_organization.id,
                original_filename=f"file_{i}.pdf",
                file_content=b"content",
                content_type="application/pdf"
            )
            file_ids.append(db_file.id)

        # Create query
        query_create = schemas.ChatQueryCreate(
            thread_id=test_thread.id,
            user_id=test_user.id,
            organization_id=test_organization.id,
            message="Test question",
            answer_mode="light"
        )
        db_query = crud.create_chat_query(db, query_create, response="Test answer")

        # Associate files
        crud.associate_files_with_query(db, db_query.id, file_ids)

        # Verify association
        db.refresh(db_query)
        assert len(db_query.files) == 2
        assert db_query.files[0].id in file_ids
        assert db_query.files[1].id in file_ids

    def test_associate_files_nonexistent_query(
        self,
        db: Session
    ):
        """Test associating files with a nonexistent query."""
        # Should not raise an error, just do nothing
        crud.associate_files_with_query(db, 99999, [1, 2, 3])
