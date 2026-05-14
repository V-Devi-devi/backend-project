# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db

# Use a separate SQLite file for tests — never touch kuppam.db
TEST_DATABASE_URL = "sqlite:///./test_kuppam.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)

def override_get_db():
    """Replace the real database session with the test database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Tell FastAPI: when a route asks for get_db, use override_get_db instead
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    """
    Creates all tables in the test database before tests run.
    Drops all tables after the module finishes (clean state for next run).
    """
    Base.metadata.create_all(bind=test_engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=test_engine)