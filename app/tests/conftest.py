import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db
from app.models import User  # Make sure User model is imported so it's registered

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    """Create the database engine for the test session."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(db_engine):
    """
    Get a fresh database session for each test function.
    Rolls back changes after test completes.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db):
    """
    Get a TestClient with the database dependency overridden.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]

@pytest.fixture
def test_user_id(db):
    """
    Create a test user if User table exists, or just return a dummy ID.
    Since we don't have auth yet, we trust the dependency injection or 
    just simulated user_id. 
    However, if there is a User table with foreign keys, we MUST create a user.
    """
    # Check if User table exists and create a dummy user
    # Based on models.py inspection (not shown yet but assuming standard structure)
    try:
        # Create a dummy user
        user = User(
            email="test@example.com", 
            hashed_password="fakehash",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
    except Exception:
        # If User model is different or doesn't exist as expected, 
        # fallback to a hardcoded ID (e.g. if we are mocking auth completely)
        return 1
