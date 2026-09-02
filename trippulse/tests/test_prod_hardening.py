import os
import tempfile

from fastapi.testclient import TestClient

from app.api.main import app
from app.models.trip_state import TripState, UserPrefs
from app.orchestrator import SessionStore


def test_session_store_persists_to_disk():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = SessionStore(base_dir=tmp_dir)
        state = TripState(trip_id="PERSIST-1", user_prefs=UserPrefs(destination="Tokyo", total_budget=1500.0))

        store.save("PERSIST-1", state)
        loaded = store.load("PERSIST-1")

        assert loaded is not None
        assert loaded.trip_id == "PERSIST-1"
        assert loaded.user_prefs.destination == "Tokyo"


def test_api_requires_auth_when_api_key_is_configured(monkeypatch):
    monkeypatch.setenv("TRIPPULSE_API_KEY", "super-secret")
    client = TestClient(app)

    response = client.get("/api/health")
    assert response.status_code == 401

    response = client.get("/api/health", headers={"Authorization": "Bearer super-secret"})
    assert response.status_code == 200
