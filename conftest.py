"""
conftest.py – Root-level pytest configuration.

Patches the PostgreSQL engine with an in-memory SQLite engine BEFORE any
app modules are loaded, so tests can run locally without a live database.
Also adds --ignore paths to exclude legacy/utility scripts that call sys.exit().
"""

import os
import sys

# ── 1. Force SQLite before ANY app import ────────────────────────────────────
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

# ── 2. Tell pytest to ignore legacy scripts / recovery dirs ──────────────────
collect_ignore_glob = [
    "recovery_temp/*",
    "scripts/*",
    "test_output.txt",
]

collect_ignore = [
    "recovery_temp",
    "scripts",
    "test_output.txt",
    "test_clicks.py",       # requires playwright browser
    "test_logistics.py",    # hits live server
]

# ── 3. Shared SQLite engine / session fixtures ────────────────────────────────
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_SQLALCHEMY_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session", autouse=True)
def patch_database():
    """Replace the postgres engine with SQLite for the whole test session."""
    import app.database as db_module

    engine = create_engine(
        TEST_SQLALCHEMY_URL, connect_args={"check_same_thread": False}
    )
    db_module.engine = engine
    db_module.SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )

    # Create all tables
    from app.models import Base
    Base.metadata.create_all(bind=engine)

    yield engine

    # Teardown – drop all tables after the session
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(patch_database):
    """Provide a transactional DB session that is rolled back after each test."""
    connection = patch_database.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="module")
def test_client(patch_database):
    """Provide a FastAPI TestClient connected to the SQLite test DB."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db
    from sqlalchemy.orm import sessionmaker

    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=patch_database
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
