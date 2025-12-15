from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app, get_db
from app.database import Base
from app import models
import pytest

# Setup Test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

def test_read_main(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Reporte" in response.text

def test_create_planning(client):
    response = client.post(
        "/api/planning",
        json={
            "date": "2025-12-11",
            "article": "Detergente",
            "presentation": "1L",
            "batches": 10,
            "kg": 1000.0,
            "units": 1000,
            "boxes": 100
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["article"] == "Detergente"
    assert "id" in data

def test_create_production_report(client):
    response = client.post(
        "/api/production",
        json={
            "batch_qty": 5,
            "article_type": "Detergente",
            "kg_produced": 500.0,
            "presentation": "1L",
            "pt_units": 450,
            "pt_lab": 1,
            "pt_burned": 0,
            "mp_containers": 500,
            "mp_caps_clean": 10,
            "mp_caps_dirty": 5,
            "cons_type": "None",
            "cons_qty": 0,
            "notes": "Test note"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["article_type"] == "Detergente"
    assert "id" in data

def test_dashboard_stats(client):
    # Depending on previous tests running first
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["total_planned_units"] == 1000
    assert data["total_production_units"] == 450
    assert data["compliance_percentage"] == 45.0
