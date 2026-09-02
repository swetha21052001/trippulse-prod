import json
import base64
import os
import asyncio
from typing import Dict, Optional

from app.models.trip_state import TripState, UserPrefs
from app.agents.flight_hotel_agent import FlightHotelAgent
from app.agents.weather_agent import WeatherAgent
from app.agents.budget_agent import BudgetAgent
from app.utils.logger import log_agent_decision
from app.agents.concierge import ConciergeAgent


class SessionStore:
    """Persist trip sessions to Firestore."""

    def __init__(self, collection_name: str = "sessions"):
        self.collection_name = collection_name
        self._db = None

    @property
    def db(self):
        if self._db is None:
            from google.cloud import firestore
            project_id = os.getenv("GCP_PROJECT", "trippulse-prod")
            self._db = firestore.Client(project=project_id)
        return self._db

    def save(self, trip_id: str, state: TripState) -> TripState:
        payload = state.model_dump(mode="json") if hasattr(state, "model_dump") else state.dict()
        self.db.collection(self.collection_name).document(trip_id).set(payload)
        return state

    def load(self, trip_id: str) -> Optional[TripState]:
        doc_ref = self.db.collection(self.collection_name).document(trip_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        try:
            return TripState(**doc.to_dict())
        except Exception:
            return None

    def delete(self, trip_id: str) -> None:
        self.db.collection(self.collection_name).document(trip_id).delete()


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

    async def run_pipeline(self, state: TripState) -> TripState:
        """Executes Parallel discovery (Flight/Hotel + Weather) -> Sequential Budget audit -> Concierge synthesis."""
        log_agent_decision("Orchestrator", state.trip_id, "Starting trip planning pipeline", {"status": state.status})

        # 1. Parallel Phase: Flight/Hotel discovery & Weather monitoring
        # Run agents in separate threads to avoid blocking the event loop
        # Each agent receives a copy of the state and returns a new state with its updates
        flight_hotel_future = asyncio.to_thread(self.flight_hotel_agent.process, state.model_copy(deep=True))
        weather_future = asyncio.to_thread(self.weather_agent.process, state.model_copy(deep=True))

        log_agent_decision("Orchestrator", state.trip_id, "Initiating parallel discovery", {"agents": ["FlightHotelAgent", "WeatherAgent"]})

        # Await both tasks to complete
        # log_agent_decision("Orchestrator", state.trip_id, "Awaiting parallel agent results") # This log would be after starting, before awaiting
        flight_hotel_updated_state, weather_updated_state = await asyncio.gather(flight_hotel_future, weather_future)

        # Merge the results from parallel agents into a single state
        state.flight_options = flight_hotel_updated_state.flight_options
        state.selected_flight = flight_hotel_updated_state.selected_flight
        state.hotel_options = flight_hotel_updated_state.hotel_options
        state.selected_hotel = flight_hotel_updated_state.selected_hotel
        state.budget_ledger.flight_spent = flight_hotel_updated_state.budget_ledger.flight_spent
        state.budget_ledger.hotel_spent = flight_hotel_updated_state.budget_ledger.hotel_spent

        state.weather_forecast = weather_updated_state.weather_forecast
        state.activity_plan = weather_updated_state.activity_plan
        state.budget_ledger.activity_spent = weather_updated_state.budget_ledger.activity_spent

        log_agent_decision("Orchestrator", state.trip_id, "Parallel discovery complete", {"flight_hotel_status": "processed", "weather_status": "processed"})

        # 2. Sequential Phase: Financial Ledger & Budget Audit
        log_agent_decision("Orchestrator", state.trip_id, "Initiating budget audit", {"agent": "BudgetAgent"})
        state = await asyncio.to_thread(self.budget_agent.process, state)
        log_agent_decision("Orchestrator", state.trip_id, "Budget audit complete", {"remaining_budget": state.budget_ledger.remaining_budget})
        if state.status != "Budget Alert":
            state.status = "Confirmed"

        self.session_store.save(state.trip_id, state)
        return state

    async def handle_disruption(self, state: TripState, disruption_type: str, details: str) -> TripState:
        """Triggers automated re-planning pipeline upon event detection."""
        log_agent_decision("Orchestrator", state.trip_id, "Handling disruption", {"type": disruption_type, "details": details, "old_status": state.status})
        state.status = "Re-planning"

        if disruption_type == "flight_delay":
            log_agent_decision("Orchestrator", state.trip_id, "Processing flight delay", {"current_flight": state.selected_flight.flight_no if state.selected_flight else "None"})
            # Pick alternative lower-risk flight if available
            if len(state.flight_options) > 1:
                alt = sorted(state.flight_options, key=lambda f: f.risk_score)[0]
                state.selected_flight = alt
                state.budget_ledger.flight_spent = alt.price
                log_agent_decision("Orchestrator", state.trip_id, "Selected alternative flight", {"new_flight": alt.flight_no, "new_price": alt.price})

        elif disruption_type == "weather_rain":
            log_agent_decision("Orchestrator", state.trip_id, "Processing weather disruption", {"agent": "WeatherAgent"})
            # Trigger weather agent re-check
            state = await asyncio.to_thread(self.weather_agent.process, state)
            log_agent_decision("Orchestrator", state.trip_id, "Weather agent re-processed", {"new_weather_risk": state.weather_forecast[0].risk_level if state.weather_forecast else "N/A"})

        # Re-run budget audit
        log_agent_decision("Orchestrator", state.trip_id, "Re-running budget audit after disruption", {"agent": "BudgetAgent"})
        state = await asyncio.to_thread(self.budget_agent.process, state)
        log_agent_decision("Orchestrator", state.trip_id, "Disruption handling complete", {"new_status": state.status, "remaining_budget": state.budget_ledger.remaining_budget})
        self.session_store.save(state.trip_id, state)
        return state

    async def process_pubsub_event(self, envelope: dict) -> Optional[TripState]:
        """Decodes a Pub/Sub push message and triggers the disruption handling pipeline."""
        if not envelope or "message" not in envelope:
            return None

        try:
            # Pub/Sub data is base64 encoded
            pubsub_message = envelope["message"]
            if "data" not in pubsub_message:
                return None

            data = base64.b64decode(pubsub_message["data"]).decode("utf-8")
            payload = json.loads(data)
        except Exception:
            return None

        trip_id = payload.get("trip_id")
        event_type = payload.get("event_type") or payload.get("disruption_type")
        details = payload.get("details", "")

        if not trip_id or not event_type:
            return None

        log_agent_decision("Orchestrator", trip_id, "Received Pub/Sub event", {"event_type": event_type, "details": details})
        state = self.session_store.load(trip_id)
        if not state:
            return None

        return await self.handle_disruption(state, event_type, details)

global_orchestrator = TripPulseOrchestrator()
