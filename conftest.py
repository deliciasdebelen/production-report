"""
conftest.py - Root-level pytest configuration.
Patches the PostgreSQL engine with SQLite BEFORE any app modules are loaded.
"""

import os
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

collect_ignore_glob = ["recovery_temp/*", "scripts/*"]
collect_ignore = ["recovery_temp", "scripts"]

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_SQLALCHEMY_URL = "sqlite:///./test.db"

@pytest.fixture(scope="session", autouse=True)
def patch_database():
    import app.database as db_module
    engine = create_engine(TEST_SQLALCHEMY_URL, connect_args={"check_same_thread": False})
    db_module.engine = engine
    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(patch_database):
    connection = patch_database.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="module")
def seeded_client(patch_database):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db
    from app.models import Role, User, SupportDepartment

    Session = sessionmaker(autocommit=False, autoflush=False, bind=patch_database)
    db = Session()

    if not db.query(Role).filter(Role.name == "admin").first():
        db.add(Role(name="admin", permissions="{}"))
        db.commit()

    if not db.query(SupportDepartment).filter(SupportDepartment.name == "Mantenimiento").first():
        db.add(SupportDepartment(name="Mantenimiento"))
        db.commit()

    role = db.query(Role).filter(Role.name == "admin").first()
    if not db.query(User).filter(User.username == "test_user").first():
        db.add(User(username="test_user", password_hash="fakehash", role=role.id, is_active=1))
        db.commit()

    db.close()

    def override_get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
