import json
import os
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

        total_cost = ledger.flight_spent + ledger.hotel_spent + ledger.activity_spent
        summary.append(f"💰 **Total Trip Cost:** ${total_cost:.2f}")

        fallback_summary = "\n\n".join(summary)
        try:
            from google import genai

            client = genai.Client(
                vertexai=True,
                project=os.getenv("GCP_PROJECT", "trippulse-prod"),
                location=os.getenv("GCP_LOCATION", "us-central1"),
            )
            response = client.models.generate_content(
                model=os.getenv("GCP_MODEL", "gemini-2.5-flash"),
                contents=(
                    "Rewrite this trip summary to be concise and useful. Preserve every "
                    "price, date, selected option, warning, and total trip cost. Return plain text only.\n"
                    + json.dumps(fallback_summary)
                ),
            )
            generated = self._extract_text(response)
            if generated:
                log_agent_decision(self.name, state.trip_id, "Gemini trip summary generated successfully")
                return generated
        except Exception as exc:
            log_agent_decision(self.name, state.trip_id, "Gemini summary unavailable; using deterministic summary", {"error": str(exc)})
        return fallback_summary

