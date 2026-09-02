from typing import Dict, Any, Optional

from app.models.trip_state import TripState


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
        # Check if Gemini API key is available for AI-powered response
        import os

        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                from google import genai

                client = genai.Client(api_key=api_key)
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
                    model="gemini-2.5-flash",
                    contents=prompt,
                )

                extracted = self._extract_text(response)
                if extracted:
                    return extracted
            except Exception:
                pass

        # Fallback response rules
        msg_lower = message.lower()
        if "weather" in msg_lower or "rain" in msg_lower:
            if state.weather_forecast:
                forecast_text = "\n".join([f"• {wf.date}: {wf.condition} (Rain Risk: {int(wf.rain_probability*100)}%, Temp: {wf.temperature_c}°C)" for wf in state.weather_forecast])
                return f"Here is the weather forecast for your trip to {state.user_prefs.destination}:\n\n{forecast_text}"
            return "Weather details will be available once your trip is planned."

        if "flight" in msg_lower:
            if state.selected_flight:
                f = state.selected_flight
                return f"Your selected flight is **{f.carrier} {f.flight_no}** departing at {f.departure_time}. Ticket price: ${f.price:.2f}. Historical delay risk score is {f.risk_score * 100:.0f}%."
            return "No flight has been selected yet."

        if "budget" in msg_lower or "cost" in msg_lower:
            b = state.budget_ledger
            return f"Your budget summary for {state.user_prefs.destination}:\n• Total Budget: ${b.total_budget:.2f}\n• Flights: ${b.flight_spent:.2f}\n• Hotel: ${b.hotel_spent:.2f}\n• Activities: ${b.activity_spent:.2f}\n• Remaining: ${b.remaining_budget:.2f}"

        return self.generate_trip_summary(state)
