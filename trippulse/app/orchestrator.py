import json
import os
from pathlib import Path
from typing import Dict, Optional

from app.models.trip_state import TripState, UserPrefs
from app.agents.flight_hotel_agent import FlightHotelAgent
from app.agents.weather_agent import WeatherAgent
from app.agents.budget_agent import BudgetAgent
from app.agents.concierge import ConciergeAgent


class SessionStore:
    """Persist trip sessions to disk so they survive process restarts."""

    def __init__(self, base_dir: Optional[str] = None):
        default_dir = os.getenv("TRIPPULSE_SESSION_DIR", os.path.join(os.getcwd(), ".trippulse_sessions"))
        self.base_dir = Path(base_dir or default_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, trip_id: str) -> Path:
        return self.base_dir / f"{trip_id}.json"

    def save(self, trip_id: str, state: TripState) -> TripState:
        payload = state.model_dump(mode="json") if hasattr(state, "model_dump") else state.dict()
        path = self._path_for(trip_id)
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return state

    def load(self, trip_id: str) -> Optional[TripState]:
        path = self._path_for(trip_id)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return TripState(**data)
        except Exception:
            return None

    def delete(self, trip_id: str) -> None:
        path = self._path_for(trip_id)
        if path.exists():
            path.unlink(missing_ok=True)


SESSION_STORE = SessionStore()


class TripPulseOrchestrator:
    """Multi-Agent Orchestrator managing parallel discovery & sequential reconciliation."""

    def __init__(self):
        self.session_store = SessionStore()
        self.flight_hotel_agent = FlightHotelAgent()
        self.weather_agent = WeatherAgent()
        self.budget_agent = BudgetAgent()
        self.concierge = ConciergeAgent()

    def get_or_create_session(self, trip_id: str, prefs: Optional[UserPrefs] = None) -> TripState:
        existing = self.session_store.load(trip_id)
        if existing is not None:
            return existing

        initial_prefs = prefs or UserPrefs()
        state = TripState(
            trip_id=trip_id,
            user_prefs=initial_prefs
        )
        self.session_store.save(trip_id, state)
        return state

    def run_pipeline(self, state: TripState) -> TripState:
        """Executes Parallel discovery (Flight/Hotel + Weather) -> Sequential Budget audit -> Concierge synthesis."""

        # 1. Parallel Phase: Flight/Hotel discovery & Weather monitoring
        # (In Python asyncio/threading or sequential execution)
        state = self.flight_hotel_agent.process(state)
        state = self.weather_agent.process(state)

        # 2. Sequential Phase: Financial Ledger & Budget Audit
        state = self.budget_agent.process(state)

        # Update status
        if state.status != "Budget Alert":
            state.status = "Confirmed"

        self.session_store.save(state.trip_id, state)
        return state

    def handle_disruption(self, state: TripState, disruption_type: str, details: str) -> TripState:
        """Triggers automated re-planning pipeline upon event detection."""
        state.status = "Re-planning"

        if disruption_type == "flight_delay":
            # Pick alternative lower-risk flight if available
            if len(state.flight_options) > 1:
                alt = sorted(state.flight_options, key=lambda f: f.risk_score)[0]
                state.selected_flight = alt
                state.budget_ledger.flight_spent = alt.price

        elif disruption_type == "weather_rain":
            # Trigger weather agent re-check
            state = self.weather_agent.process(state)

        # Re-run budget audit
        state = self.budget_agent.process(state)
        self.session_store.save(state.trip_id, state)
        return state

global_orchestrator = TripPulseOrchestrator()
