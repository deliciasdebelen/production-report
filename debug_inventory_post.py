
import requests
import json
from datetime import datetime

url = "http://127.0.0.1:8000/inventory/api/full-capture"

# Mimic the frontend payload
payload = {
    "date": datetime.now().strftime("%Y-%m-%d"), # Frontend uses input type="date"
    "notes": "Debug Script | Tipo: Inicio",
    "lines": [
        {
            "article_code": "TEST-01",
            "article_description": "Test Article",
            "batch": "BATCH-001",
            "quantity": 10.5
        }
    ]
}

# Need authentication cookies?
# Usually getting a session might be needed if behind auth. 
# Attempting raw request first, if 401/403 then we'll assume auth issue (but error says "Error al guardar" implies 500 or 422).
# The frontend has cookies. We can try to use a mock user if we were running internal app code, but this is external request.
# Let's try internal test using FastAPI TestClient to bypass auth if possible, or just Login first.

# Using FastAPIs TestClient is better as it runs in-process.

from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_db, get_current_active_user
from app import models

# Override dependency to mock user
async def mock_get_current_active_user():
    return models.User(id=1, username="debug_admin", role=1)

app.dependency_overrides[get_current_active_user] = mock_get_current_active_user

client = TestClient(app)

print(f"Sending Payload: {json.dumps(payload, indent=2)}")

try:
    response = client.post("/inventory/api/full-capture", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
