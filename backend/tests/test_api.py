"""
Tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src import models, auth


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_register_user(self, client: TestClient, db: Session):
        """Test user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepass123"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "api_key" in data
        assert data["is_admin"] is False

    def test_register_user_is_not_admin_by_default(self, client: TestClient, db: Session):
        """Test that newly registered users are not admins by default."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "regular@example.com",
                "username": "regularuser",
                "password": "securepass123"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_admin"] is False

    def test_register_duplicate_email(self, client: TestClient, test_user: models.User):
        """Test registration with duplicate email."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_user.email,
                "username": "different",
                "password": "password123"
            }
        )
        assert response.status_code == 400
        error_data = response.json()
        error_message = error_data.get("error") or error_data.get("detail", "")
        assert "already registered" in error_message.lower()

    def test_login_success(self, client: TestClient, test_user: models.User):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username

    def test_login_wrong_password(self, client: TestClient, test_user: models.User):
        """Test login with wrong password."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 401


class TestOrganizationEndpoints:
    """Tests for organization endpoints."""

    def test_create_organization(self, authenticated_client: TestClient, test_user: models.User):
        """Test creating an organization."""
        response = authenticated_client.post(
            f"/api/organizations?user_id={test_user.id}",
            json={
                "name": "New Company",
                "description": "A new test company",
                "org_metadata": {"industry": "Technology"}
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Company"
        assert data["owner_id"] == test_user.id

    def test_get_organizations(self, authenticated_client: TestClient, test_user: models.User, test_organization: models.Organization):
        """Test getting user's organizations."""
        response = authenticated_client.get(f"/api/organizations?user_id={test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(org["id"] == test_organization.id for org in data)

    def test_get_organization_detail(self, authenticated_client: TestClient, test_user: models.User, test_organization: models.Organization):
        """Test getting organization details."""
        response = authenticated_client.get(f"/api/organizations/{test_organization.id}?user_id={test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_organization.id
        assert data["name"] == test_organization.name


class TestThreadEndpoints:
    """Tests for thread endpoints."""

    def test_create_thread(self, authenticated_client: TestClient, test_user: models.User, test_organization: models.Organization):
        """Test creating a thread (owner has write access)."""
        response = authenticated_client.post(
            f"/api/threads?user_id={test_user.id}",
            json={
                "organization_id": test_organization.id,
                "title": "New Thread"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Thread"
        assert data["organization_id"] == test_organization.id

    def test_get_threads(self, authenticated_client: TestClient, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test getting user's threads."""
        response = authenticated_client.get(f"/api/threads?user_id={test_user.id}&organization_id={test_organization.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(thread["id"] == test_thread.id for thread in data)

    def test_get_thread_queries(self, authenticated_client: TestClient, test_user: models.User, test_thread: models.Thread, test_query: models.ChatQuery):
        """Test getting queries for a thread (with user_id for permission check)."""
        response = authenticated_client.get(f"/api/threads/{test_thread.id}/queries?user_id={test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(query["id"] == test_query.id for query in data)


class TestChatEndpoints:
    """Tests for chat endpoints."""

    def test_create_query(self, authenticated_client: TestClient, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread):
        """Test creating a chat query (non-streaming)."""
        pass  # Placeholder - actual implementation would require mocking agents


class TestUserEndpoints:
    """Tests for user endpoints."""

    def test_list_users_requires_admin(self, authenticated_client: TestClient):
        """Non-admin callers cannot list users (would leak the user table)."""
        response = authenticated_client.get("/api/users")
        assert response.status_code == 403

    def test_list_users_as_admin(self, admin_client: TestClient, admin_user: models.User):
        """Admins can list users; response never includes api_key."""
        response = admin_client.get("/api/users")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(user["id"] == admin_user.id for user in data)
        assert all("api_key" not in user for user in data)

    def test_get_user_by_id(self, authenticated_client: TestClient, test_user: models.User):
        """Test getting a specific user — public fields only, no api_key leak."""
        response = authenticated_client.get(f"/api/users/{test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert "api_key" not in data


class TestAdminEndpoints:
    """Tests for admin-only endpoints."""

    def test_update_user_as_admin(self, admin_client: TestClient, admin_user: models.User, test_user: models.User):
        """Test admin can update user properties."""
        response = admin_client.patch(
            f"/api/admin/users/{test_user.id}",
            params={"admin_user_id": admin_user.id},
            json={"is_admin": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] is True

    def test_update_user_as_non_admin(self, authenticated_client: TestClient, test_user: models.User, db: Session):
        """Test non-admin cannot update user properties."""
        other_user = models.User(
            email="other@example.com",
            username="otheruser",
            password_hash="hash",
            is_admin=False
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        response = authenticated_client.patch(
            f"/api/admin/users/{test_user.id}",
            params={"admin_user_id": other_user.id},
            json={"is_admin": True}
        )
        assert response.status_code == 403
        response_json = response.json()
        error_message = response_json.get("detail") or response_json.get("error")
        assert "Admin access required" in error_message

    def test_admin_cannot_disable_self(self, admin_client: TestClient, admin_user: models.User):
        """Test admin cannot disable their own account."""
        response = admin_client.patch(
            f"/api/admin/users/{admin_user.id}",
            params={"admin_user_id": admin_user.id},
            json={"is_active": False}
        )
        assert response.status_code == 400
        response_json = response.json()
        error_message = response_json.get("detail") or response_json.get("error")
        assert "cannot disable your own account" in error_message.lower()

    def test_ban_user(self, admin_client: TestClient, admin_user: models.User, test_user: models.User):
        """Test admin can ban/disable a user."""
        response = admin_client.patch(
            f"/api/admin/users/{test_user.id}",
            params={"admin_user_id": admin_user.id},
            json={"is_active": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_get_user_threads_as_admin(self, admin_client: TestClient, admin_user: models.User, test_user: models.User, test_thread: models.Thread):
        """Test admin can view user's threads."""
        response = admin_client.get(
            f"/api/admin/users/{test_user.id}/threads",
            params={"admin_user_id": admin_user.id}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(thread["id"] == test_thread.id for thread in data)

    def test_get_user_queries_as_admin(self, admin_client: TestClient, admin_user: models.User, test_user: models.User, test_query: models.ChatQuery):
        """Test admin can view user's queries."""
        response = admin_client.get(
            f"/api/admin/users/{test_user.id}/queries",
            params={"admin_user_id": admin_user.id}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(query["id"] == test_query.id for query in data)

    def test_admin_usage_stats_requires_admin(self, authenticated_client: TestClient, test_user: models.User):
        """Test that non-admin cannot access all users usage stats."""
        response = authenticated_client.get(
            "/api/admin/usage/all",
            params={"user_id": test_user.id}
        )
        assert response.status_code == 403


class TestAccessControl:
    """Tests for organization-level access control enforcement."""

    def _create_user(self, db: Session, email: str, username: str, is_admin: bool = False) -> models.User:
        user = models.User(
            email=email,
            username=username,
            password_hash=auth.hash_password("password123"),
            is_admin=is_admin,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def _add_member(self, db: Session, org_id: int, user_id: int, can_read: bool = True, can_write: bool = False):
        member = models.OrganizationMember(
            organization_id=org_id,
            user_id=user_id,
            can_read=can_read,
            can_write=can_write,
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    def _make_client(self, client: TestClient, user: models.User) -> TestClient:
        """Return a client authenticated as the given user."""
        client.headers["x-api-key"] = str(user.api_key)
        return client

    # --- Thread creation (requires write) ---

    def test_read_only_member_cannot_create_thread(self, client: TestClient, db: Session, test_organization: models.Organization):
        """Read-only member should be denied thread creation."""
        reader = self._create_user(db, "reader@test.com", "reader")
        self._add_member(db, test_organization.id, reader.id, can_read=True, can_write=False)
        c = self._make_client(client, reader)

        response = c.post(
            f"/api/threads?user_id={reader.id}",
            json={"organization_id": test_organization.id, "title": "Should fail"}
        )
        assert response.status_code == 403

    def test_write_member_can_create_thread(self, client: TestClient, db: Session, test_organization: models.Organization):
        """Write member should be able to create a thread."""
        writer = self._create_user(db, "writer@test.com", "writer")
        self._add_member(db, test_organization.id, writer.id, can_read=True, can_write=True)
        c = self._make_client(client, writer)

        response = c.post(
            f"/api/threads?user_id={writer.id}",
            json={"organization_id": test_organization.id, "title": "Allowed"}
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Allowed"

    def test_nonmember_cannot_create_thread(self, client: TestClient, db: Session, test_organization: models.Organization):
        """Non-member should be denied thread creation."""
        outsider = self._create_user(db, "outsider@test.com", "outsider")
        c = self._make_client(client, outsider)

        response = c.post(
            f"/api/threads?user_id={outsider.id}",
            json={"organization_id": test_organization.id, "title": "Nope"}
        )
        assert response.status_code == 403

    # --- Thread reading (requires read) ---

    def test_read_member_can_view_threads(self, client: TestClient, db: Session, test_organization: models.Organization, test_thread: models.Thread):
        """Read member can view threads in orgs they can read."""
        reader = self._create_user(db, "reader2@test.com", "reader2")
        self._add_member(db, test_organization.id, reader.id, can_read=True, can_write=False)
        c = self._make_client(client, reader)

        response = c.get(f"/api/threads/{test_thread.id}?user_id={reader.id}")
        assert response.status_code == 200

    def test_nonmember_cannot_view_thread(self, client: TestClient, db: Session, test_thread: models.Thread):
        """Non-member cannot access a thread by ID."""
        outsider = self._create_user(db, "outsider2@test.com", "outsider2")
        c = self._make_client(client, outsider)

        response = c.get(f"/api/threads/{test_thread.id}?user_id={outsider.id}")
        assert response.status_code == 403

    def test_nonmember_cannot_view_thread_queries(self, client: TestClient, db: Session, test_thread: models.Thread, test_query: models.ChatQuery):
        """Non-member cannot access queries in a thread."""
        outsider = self._create_user(db, "outsider3@test.com", "outsider3")
        c = self._make_client(client, outsider)

        response = c.get(f"/api/threads/{test_thread.id}/queries?user_id={outsider.id}")
        assert response.status_code == 403

    # --- Query access ---

    def test_nonmember_cannot_view_query_by_id(self, client: TestClient, db: Session, test_query: models.ChatQuery):
        """Non-member cannot access a query by ID."""
        outsider = self._create_user(db, "outsider4@test.com", "outsider4")
        c = self._make_client(client, outsider)

        response = c.get(f"/api/queries/{test_query.id}?user_id={outsider.id}")
        assert response.status_code == 403

    def test_owner_can_view_own_query(self, client: TestClient, test_user: models.User, test_query: models.ChatQuery):
        """Thread/query owner can access their own query."""
        c = self._make_client(client, test_user)

        response = c.get(f"/api/queries/{test_query.id}?user_id={test_user.id}")
        assert response.status_code == 200
        assert response.json()["id"] == test_query.id

    def test_get_queries_scoped_to_authenticated_user(self, client: TestClient, test_user: models.User):
        """GET /api/queries derives the user from the API key — no user_id param needed."""
        c = self._make_client(client, test_user)
        response = c.get("/api/queries")
        assert response.status_code == 200

    def test_get_queries_rejects_unauthenticated(self, client: TestClient):
        """GET /api/queries rejects callers with no API key."""
        response = client.get("/api/queries")
        assert response.status_code == 401

    # --- Admin bypass ---

    def test_admin_can_access_any_thread(self, client: TestClient, db: Session, admin_user: models.User, test_thread: models.Thread):
        """System admin can access any thread regardless of membership."""
        c = self._make_client(client, admin_user)

        response = c.get(f"/api/threads/{test_thread.id}?user_id={admin_user.id}")
        assert response.status_code == 200

    # --- Org-filtered thread listing ---

    def test_nonmember_cannot_list_org_threads(self, client: TestClient, db: Session, test_organization: models.Organization):
        """Non-member cannot list threads filtered by an org they don't belong to."""
        outsider = self._create_user(db, "outsider5@test.com", "outsider5")
        c = self._make_client(client, outsider)

        response = c.get(f"/api/threads?user_id={outsider.id}&organization_id={test_organization.id}")
        assert response.status_code == 403

    # --- Member management ---

    def test_add_and_update_org_member(self, client: TestClient, db: Session, test_user: models.User, test_organization: models.Organization):
        """Owner can add a member, then update their permissions."""
        c = self._make_client(client, test_user)
        new_user = self._create_user(db, "newmember@test.com", "newmember")

        # Add member with read-only
        response = c.post(
            f"/api/organizations/{test_organization.id}/members?user_id={test_user.id}",
            json={"user_id": new_user.id, "can_read": True, "can_write": False}
        )
        assert response.status_code == 201

        # Update to read-write
        response = c.put(
            f"/api/organizations/{test_organization.id}/members/{new_user.id}?user_id={test_user.id}",
            json={"can_read": True, "can_write": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["can_write"] is True

    def test_remove_org_member_loses_access(self, client: TestClient, db: Session, test_user: models.User, test_organization: models.Organization):
        """After removal from org, user loses access to org threads."""
        member_user = self._create_user(db, "toremove@test.com", "toremove")
        self._add_member(db, test_organization.id, member_user.id, can_read=True, can_write=True)

        thread = models.Thread(
            user_id=test_user.id,
            organization_id=test_organization.id,
            title="Access test",
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)

        # Member can access the thread
        mc = self._make_client(client, member_user)
        response = mc.get(f"/api/threads/{thread.id}?user_id={member_user.id}")
        assert response.status_code == 200

        # Owner removes the member
        oc = self._make_client(client, test_user)
        response = oc.delete(
            f"/api/organizations/{test_organization.id}/members/{member_user.id}?user_id={test_user.id}"
        )
        assert response.status_code in (200, 204)

        # Now member should be denied
        mc2 = self._make_client(client, member_user)
        response = mc2.get(f"/api/threads/{thread.id}?user_id={member_user.id}")
        assert response.status_code == 403
