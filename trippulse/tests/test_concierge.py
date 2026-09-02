import unittest
from app.models.trip_state import TripState, UserPrefs
from app.orchestrator import global_orchestrator

class TestConciergeAgent(unittest.TestCase):
    def test_generate_trip_summary(self):
        prefs = UserPrefs(destination="Tokyo", total_budget=2000.0)
        state = global_orchestrator.get_or_create_session("TEST-SUMMARY-01", prefs)
        state = global_orchestrator.run_pipeline(state)
        
        summary = global_orchestrator.concierge.generate_trip_summary(state)
        self.assertIn("Itinerary", summary)
        self.assertIn("Tokyo", summary)

if __name__ == "__main__":
    unittest.main()
