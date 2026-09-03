from typing import Dict, Any, Optional

from app.models.trip_state import TripState
from app.utils.logger import log_agent_decision


class ConciergeAgent:
    """Root Concierge Agent synthesizing insights, communicating with the user, and orchestrating trip goals."""

    def __init__(self, name: str = "ConciergeAgent"):
        self.name = name

    @staticmethod
    def _extract_text(response: Any) -> str:
        if response is None:
            return ""

        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        if isinstance(response, dict):
            for key in ("text", "output_text"):
                value = response.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        candidates = getattr(response, "candidates", None)
        if candidates:
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None) if content else None
                if parts:
                    for part in parts:
                        text = getattr(part, "text", None)
                        if isinstance(text, str) and text.strip():
                            return text.strip()

        return ""

    def generate_trip_summary(self, state: TripState) -> str:
        log_agent_decision(self.name, state.trip_id, "Generating final trip summary")
        prefs = state.user_prefs
        flight = state.selected_flight
        hotel = state.selected_hotel
        ledger = state.budget_ledger

        summary = []
        summary.append(f"🎯 **Trip Overview for {prefs.destination}** ({prefs.start_date} to {prefs.end_date})")

        if flight:
            summary.append(f"✈️ **Flight:** {flight.carrier} ({flight.flight_no}) — ${flight.price:.2f} (Delay Risk: {int(flight.risk_score*100)}%)")

        if hotel:
            summary.append(f"🏨 **Hotel:** {hotel.name} — ${hotel.total_price:.2f} ({hotel.rating}★)")

        if state.weather_forecast:
            rainy_days = [wf for wf in state.weather_forecast if wf.rain_probability > 0.5]
            if rainy_days:
                summary.append(f"🌧️ **Weather Alert:** Rain predicted on {len(rainy_days)} day(s). Outdoor activities have been automatically swapped for top-rated indoor alternatives!")

        if state.activity_plan:
            summary.append(f"📅 **Itinerary:** {len(state.activity_plan)} curated activities across {len(set(act.day for act in state.activity_plan))} days.")

        summary.append(f"💰 **Budget Summary:** Spent ${state.user_prefs.total_budget - ledger.remaining_budget:.2f} of ${ledger.total_budget:.2f} (Remaining: ${ledger.remaining_budget:.2f})")

        return "\n\n".join(summary)

    def respond(self, message: str, state: TripState) -> str:
        # Use Vertex AI with Service Account credentials (no API key needed)
        log_agent_decision(self.name, state.trip_id, "Processing user query", {"message": message})
        import os
        from google import genai

        project_id = os.getenv("GCP_PROJECT", "trippulse-prod")
        location = os.getenv("GCP_LOCATION", "us-central1")

        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )
        prompt = (
            f"You are TripPulse Concierge, a helpful AI travel assistant.\n"
            f"Current Trip Context: Destination: {state.user_prefs.destination}, "
            f"Budget: ${state.user_prefs.total_budget}, Selected Flight: {state.selected_flight.flight_no if state.selected_flight else 'None'}, "
            f"Selected Hotel: {state.selected_hotel.name if state.selected_hotel else 'None'}, "
            f"Remaining Budget: ${state.budget_ledger.remaining_budget:.2f}.\n\n"
            f"User Query: {message}\n"
            f"Provide a helpful, polite, concise travel concierge answer."
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        extracted = self._extract_text(response)
        if not extracted:
            raise RuntimeError("Gemini returned an empty response")
        log_agent_decision(self.name, state.trip_id, "AI response generated successfully")
        return extracted
