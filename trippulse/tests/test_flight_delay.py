import unittest
from app.models.trip_state import TripState, UserPrefs
from app.orchestrator import global_orchestrator
from app.data.flights import flight_risk_score

class TestFlightDelay(unittest.TestCase):
    def test_flight_risk_score_calculation(self):
        score = flight_risk_score("JL 001", "2026-09-10", "SFO", "TYO")
        self.assertTrue(0.0 <= score <= 1.0)

    def test_flight_selection_and_disruption_replan(self):
        prefs = UserPrefs(destination="Tokyo", total_budget=2000.0)
        state = global_orchestrator.get_or_create_session("TEST-FLIGHT-01", prefs)
        state = global_orchestrator.run_pipeline(state)

        self.assertIsNotNone(state.selected_flight)

        # Trigger flight delay disruption
        state = global_orchestrator.handle_disruption(state, "flight_delay", "Flight delayed 3 hrs")
        self.assertIsNotNone(state.selected_flight)

if __name__ == "__main__":
    unittest.main()
