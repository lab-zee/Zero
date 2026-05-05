"""
Pytest configuration and fixtures for LabZ backend tests.
"""
import os
import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from faker import Faker

# Set test environment
os.environ["TESTING"] = "1"
os.environ["OPENAI_API_KEY"] = "test_key_for_testing"  # Required for vector_store module import

from src.database import Base, get_db
from src.main import app
from src import models, schemas, auth

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

fake = Faker()


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> models.User:
    """Create a test user."""
    user = models.User(
        email="test@example.com",
        username="testuser",
        password_hash=auth.hash_password("testpass123"),
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db: Session) -> models.User:
    """Create an admin user."""
    user = models.User(
        email="admin@example.com",
        username="adminuser",
        password_hash=auth.hash_password("adminpass123"),
        is_admin=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_organization(db: Session, test_user: models.User) -> models.Organization:
    """Create a test organization."""
    org = models.Organization(
        name="Test Company",
        description="A test organization",
        owner_id=test_user.id,
        org_metadata={
            "industry": "Technology",
            "type": "B2B SaaS",
            "purpose": "Testing purposes"
        }
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def test_thread(db: Session, test_user: models.User, test_organization: models.Organization) -> models.Thread:
    """Create a test thread."""
    thread = models.Thread(
        user_id=test_user.id,
        organization_id=test_organization.id,
        title="Test Thread",
        thread_metadata={"creativity": "balanced"},
        default_answer_mode=models.AnswerMode.LIGHT
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


@pytest.fixture
def test_query(db: Session, test_user: models.User, test_organization: models.Organization, test_thread: models.Thread) -> models.ChatQuery:
    """Create a test query."""
    query = models.ChatQuery(
        thread_id=test_thread.id,
        user_id=test_user.id,
        organization_id=test_organization.id,
        message="What is the market opportunity for our product?",
        response="Based on analysis, the market opportunity is significant...",
        answer_mode=models.AnswerMode.LIGHT,
        execution_trace={"nodes": [], "edges": []}
    )
    db.add(query)
    db.commit()
    db.refresh(query)
    return query


@pytest.fixture
def authenticated_client(client: TestClient, test_user: models.User) -> TestClient:
    """Create an authenticated test client with the test user's API key."""
    client.headers["x-api-key"] = str(test_user.api_key)
    return client


@pytest.fixture
def admin_client(client: TestClient, admin_user: models.User) -> TestClient:
    """Create an authenticated test client with admin API key."""
    client.headers["x-api-key"] = str(admin_user.api_key)
    return client


@pytest.fixture
def sample_org_data() -> dict:
    """Generate sample organization data."""
    return {
        "name": fake.company(),
        "description": fake.catch_phrase(),
        "org_metadata": {
            "industry": fake.job(),
            "type": "B2B",
            "purpose": fake.bs(),
            "goals": [fake.bs() for _ in range(3)],
            "key_products_services": [fake.catch_phrase() for _ in range(2)],
            "target_market": fake.job()
        }
    }
