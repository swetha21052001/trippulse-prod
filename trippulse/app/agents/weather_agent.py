from datetime import date, timedelta
from typing import List
from app.models.trip_state import TripState, DisruptionEvent, ActivityPlan
from app.data.weather import get_weather_forecast
from app.data.activities import search_activities, get_indoor_alternatives # type: ignore
from app.utils.logger import log_agent_decision

class WeatherAgent:
    """Agent responsible for checking weather forecasts, detecting disruptions, and scheduling activities."""
    def __init__(self, name: str = "WeatherAgent"):
        self.name = name

    def process(self, state: TripState) -> TripState:
        log_agent_decision(self.name, state.trip_id, "Starting weather and activity processing", {"destination": state.user_prefs.destination})
        prefs = state.user_prefs
        start_date = date.fromisoformat(prefs.start_date)
        end_date = date.fromisoformat(prefs.end_date)
        dates = [
            (start_date + timedelta(days=offset)).isoformat()
            for offset in range((end_date - start_date).days + 1)
        ]
        
        # 1. Fetch Forecast if not already set
        if not state.weather_forecast:
            forecasts = get_weather_forecast(prefs.destination, dates)
            log_agent_decision(self.name, state.trip_id, "Fetched weather forecast", {"num_days": len(forecasts)})
            state.weather_forecast = forecasts
        else:
            forecasts = state.weather_forecast

        # 2. Build initial activities if not present
        if not state.activity_plan:
            state.activity_plan = search_activities(prefs.destination, len(dates))
            log_agent_decision(self.name, state.trip_id, "Built initial activity plan", {"num_activities": len(state.activity_plan)})

        # 3. Evaluate rain risks per day
        for forecast in forecasts:
            if forecast.rain_probability > 0.60:
                day_num = dates.index(forecast.date) + 1
                log_agent_decision(self.name, state.trip_id, "High rain probability detected", {"date": forecast.date, "probability": forecast.rain_probability})
                
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
                    log_agent_decision(self.name, state.trip_id, "Logged weather disruption event", {"date": forecast.date})

                # Swap outdoor activities for indoor alternatives
                for act in state.activity_plan:
                    if act.day == day_num and act.is_outdoor and act.status != "Swapped":
                        if act.rain_alternative:
                            act.name = f"{act.rain_alternative} [Indoor Swap]"
                            act.is_outdoor = False
                            act.status = "Swapped"
                            log_agent_decision(self.name, state.trip_id, "Swapped activity with catalog alternative", {"original_activity": act.name, "new_activity": act.rain_alternative})
                        else:
                            alternatives = get_indoor_alternatives(prefs.destination, forecast.date)
                            if alternatives:
                                alt = alternatives[0]
                                act.name = f"{alt['name']} [Indoor Swap]"
                                act.category = alt["category"]
                                act.cost = alt["cost"]
                                act.is_outdoor = False
                                act.status = "Swapped"
                                log_agent_decision(self.name, state.trip_id, "Swapped activity with dynamically generated indoor alternative", {"original_activity": act.name, "new_activity": alt['name']})

        return state
