import sys
import types

from app.agents.concierge import ConciergeAgent
from app.models.trip_state import TripState, UserPrefs


def test_concierge_uses_google_genai_sdk(monkeypatch):
    captured = {}

    class FakeResponse:
        text = "hello from model"

    class FakeModels:
        def generate_content(self, model, contents):
            captured["model"] = model
            captured["contents"] = contents
            return FakeResponse()

    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.models = FakeModels()

    fake_google = types.ModuleType("google")
    fake_google_genai = types.ModuleType("google.genai")
    fake_google_genai.Client = FakeClient
    fake_google.genai = fake_google_genai

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_google_genai)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    state = TripState(
        trip_id="AI-TEST-1",
        user_prefs=UserPrefs(destination="Tokyo", total_budget=2000.0),
    )

    reply = ConciergeAgent().respond("hello", state)

    assert reply == "hello from model"
    assert captured["model"] == "gemini-2.5-flash"
    assert "hello" in captured["contents"]
