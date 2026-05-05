"""
Tests for organization CRUD operations.
"""
import pytest
from sqlalchemy.orm import Session
from src import models, schemas, crud


class TestOrganizationCRUD:
    """Tests for organization CRUD operations."""

    def test_create_organization(self, db: Session, test_user: models.User):
        """Test creating an organization."""
        org_create = schemas.OrganizationCreate(
            name="Test Company",
            description="A test organization"
        )

        org = crud.create_organization(db, org_create, test_user.id)

        assert org.id is not None
        assert org.name == "Test Company"
        assert org.description == "A test organization"
        assert org.owner_id == test_user.id

    def test_get_organization(self, db: Session, test_organization: models.Organization):
        """Test retrieving an organization."""
        retrieved = crud.get_organization(db, test_organization.id)

        assert retrieved is not None
        assert retrieved.id == test_organization.id
        assert retrieved.name == test_organization.name

    def test_get_nonexistent_organization(self, db: Session):
        """Test retrieving an organization that doesn't exist."""
        result = crud.get_organization(db, 99999)
        assert result is None

    def test_get_organizations_by_owner(self, db: Session, test_user: models.User):
        """Test retrieving organizations by owner."""
        # Create multiple organizations
        for i in range(3):
            org_create = schemas.OrganizationCreate(
                name=f"Company {i}",
                description=f"Description {i}"
            )
            crud.create_organization(db, org_create, test_user.id)

        orgs = crud.get_organizations_by_owner(db, test_user.id)

        assert len(orgs) >= 3
        assert all(o.owner_id == test_user.id for o in orgs)

    def test_update_organization(self, db: Session, test_organization: models.Organization):
        """Test updating an organization."""
        org_update = schemas.OrganizationUpdate(
            name="Updated Name",
            description="Updated Description"
        )
        updated = crud.update_organization(
            db,
            test_organization.id,
            org_update
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated Description"

    def test_update_organization_metadata(self, db: Session, test_organization: models.Organization):
        """Test updating organization metadata."""
        new_metadata = schemas.OrganizationMetadata(
            industry_name="Healthcare",
            org_type="B2C",
            target_market="Healthcare consumers"
        )

        org_update = schemas.OrganizationUpdate(
            metadata=new_metadata
        )
        updated = crud.update_organization(
            db,
            test_organization.id,
            org_update
        )

        assert updated is not None
        assert updated.org_metadata["industry_name"] == "Healthcare"
        assert updated.org_metadata["org_type"] == "B2C"

    def test_delete_organization(self, db: Session, test_user: models.User):
        """Test deleting an organization."""
        # Create an organization to delete
        org_create = schemas.OrganizationCreate(
            name="Org to Delete",
            description="Will be deleted"
        )
        org = crud.create_organization(db, org_create, test_user.id)
        org_id = org.id

        # Delete it
        result = crud.delete_organization(db, org_id)
        assert result is True

        # Verify it's gone
        retrieved = crud.get_organization(db, org_id)
        assert retrieved is None

    def test_delete_nonexistent_organization(self, db: Session):
        """Test deleting an organization that doesn't exist."""
        result = crud.delete_organization(db, 99999)
        assert result is False

    def test_check_org_permission_owner(self, db: Session, test_user: models.User, test_organization: models.Organization):
        """Test that organization owner has permission."""
        has_permission = crud.check_org_permission(
            db,
            test_organization.id,
            test_user.id,
            require_write=True
        )

        assert has_permission is True

    def test_check_org_permission_admin_bypass(self, db: Session, admin_user: models.User, test_organization: models.Organization):
        """Test that system admin has permission even without membership."""
        has_permission = crud.check_org_permission(
            db,
            test_organization.id,
            admin_user.id,
            require_write=True
        )
        assert has_permission is True

    def test_check_org_permission_nonmember(self, db: Session, test_organization: models.Organization):
        """Test that non-member non-admin doesn't have permission."""
        from src import auth
        other_user = models.User(
            email="other@example.com",
            username="otheruser",
            password_hash=auth.hash_password("pass"),
            is_admin=False,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        has_permission = crud.check_org_permission(
            db,
            test_organization.id,
            other_user.id,
            require_write=False
        )
        assert has_permission is False

    def test_check_org_permission_read_member(self, db: Session, test_organization: models.Organization):
        """Test that a read-only member has read but not write permission."""
        from src import auth
        member = models.User(
            email="member@example.com",
            username="memberuser",
            password_hash=auth.hash_password("pass"),
            is_admin=False,
        )
        db.add(member)
        db.commit()
        db.refresh(member)

        membership = models.OrganizationMember(
            organization_id=test_organization.id,
            user_id=member.id,
            can_read=True,
            can_write=False,
        )
        db.add(membership)
        db.commit()

        assert crud.check_org_permission(db, test_organization.id, member.id, require_write=False) is True
        assert crud.check_org_permission(db, test_organization.id, member.id, require_write=True) is False

    def test_check_org_permission_write_member(self, db: Session, test_organization: models.Organization):
        """Test that a write member has both read and write permission."""
        from src import auth
        member = models.User(
            email="writer@example.com",
            username="writeruser",
            password_hash=auth.hash_password("pass"),
            is_admin=False,
        )
        db.add(member)
        db.commit()
        db.refresh(member)

        membership = models.OrganizationMember(
            organization_id=test_organization.id,
            user_id=member.id,
            can_read=True,
            can_write=True,
        )
        db.add(membership)
        db.commit()

        assert crud.check_org_permission(db, test_organization.id, member.id, require_write=False) is True
        assert crud.check_org_permission(db, test_organization.id, member.id, require_write=True) is True

    def test_organization_with_minimal_data(self, db: Session, test_user: models.User):
        """Test creating organization with minimal required fields."""
        org_create = schemas.OrganizationCreate(
            name="Minimal Org"
            # No description or metadata
        )

        org = crud.create_organization(db, org_create, test_user.id)

        assert org.id is not None
        assert org.name == "Minimal Org"
        assert org.owner_id == test_user.id
