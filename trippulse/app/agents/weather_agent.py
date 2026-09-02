from typing import List
from app.models.trip_state import TripState, DisruptionEvent, ActivityPlan
from app.data.weather import get_weather_forecast
from app.data.activities import search_activities, get_indoor_alternatives

class WeatherAgent:
    """Agent responsible for checking weather forecasts, detecting disruptions, and scheduling activities."""
    def __init__(self, name: str = "WeatherAgent"):
        self.name = name

    def process(self, state: TripState) -> TripState:
        prefs = state.user_prefs
        dates = [prefs.start_date, "2026-09-11", prefs.end_date]
        
        # 1. Fetch Forecast if not already set
        if not state.weather_forecast:
            forecasts = get_weather_forecast(prefs.destination, dates)
            state.weather_forecast = forecasts
        else:
            forecasts = state.weather_forecast

        # 2. Build initial activities if not present
        if not state.activity_plan:
            state.activity_plan = search_activities(prefs.destination, len(dates))

        # 3. Evaluate rain risks per day
        for forecast in forecasts:
            if forecast.rain_probability > 0.60:
                day_num = dates.index(forecast.date) + 1
                
                # Check for disruption event
                existing_disruption = any(
                    d.event_type == "weather_rain" and d.affected_day == day_num
                    for d in state.disruptions
                )
                
                if not existing_disruption:
                    state.disruptions.append(DisruptionEvent(
                        event_id=f"DIS-WATH-{day_num}",
                        timestamp=forecast.date,
                        event_type="weather_rain",
                        description=f"High rain probability ({int(forecast.rain_probability*100)}%) on Day {day_num} ({forecast.date}).",
                        affected_day=day_num,
                        severity="high"
                    ))

                # Swap outdoor activities for indoor alternatives
                for act in state.activity_plan:
                    if act.day == day_num and act.is_outdoor and act.status != "Swapped":
                        if act.rain_alternative:
                            act.name = f"{act.rain_alternative} [Indoor Swap]"
                            act.is_outdoor = False
                            act.status = "Swapped"
                        else:
                            alternatives = get_indoor_alternatives(prefs.destination, forecast.date)
                            if alternatives:
                                alt = alternatives[0]
                                act.name = f"{alt['name']} [Indoor Swap]"
                                act.category = alt["category"]
                                act.cost = alt["cost"]
                                act.is_outdoor = False
                                act.status = "Swapped"

        return state
