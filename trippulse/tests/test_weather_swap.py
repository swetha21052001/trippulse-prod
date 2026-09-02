import unittest
from app.models.trip_state import TripState, UserPrefs
from app.agents.weather_agent import WeatherAgent

class TestWeatherSwap(unittest.TestCase):
    def test_weather_rain_disruption_and_indoor_swap(self):
        prefs = UserPrefs(destination="Tokyo", start_date="2026-09-10", end_date="2026-09-12")
        state = TripState(trip_id="TEST-WEATHER-01", user_prefs=prefs)
        
        agent = WeatherAgent()
        state = agent.process(state)

        self.assertGreater(len(state.weather_forecast), 0)
        self.assertGreater(len(state.activity_plan), 0)

        # Inject heavy rain on Day 1 to force indoor swap validation
        state.weather_forecast[0].rain_probability = 0.85
        state.weather_forecast[0].condition = "Heavy Rain"
        
        state = agent.process(state)
        
        # Verify disruption logged and activity swapped
        disruptions = [d for d in state.disruptions if d.event_type == "weather_rain"]
        self.assertGreater(len(disruptions), 0)
        
        day1_activities = [a for a in state.activity_plan if a.day == 1]
        swapped = [a for a in day1_activities if a.status == "Swapped" or "Indoor" in a.name]
        self.assertGreater(len(swapped), 0)

if __name__ == "__main__":
    unittest.main()
