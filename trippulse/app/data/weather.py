import os
import requests
from typing import List, Dict, Any
from app.models.trip_state import WeatherForecast
from app.utils.rate_limiter import global_rate_limiter

DESTINATION_COORDS = {
    "TOKYO": (35.6762, 139.6503),
    "LISBON": (38.7223, -9.1393),
    "PARIS": (48.8566, 2.3522),
    "NEW YORK": (40.7128, -74.0060),
    "LONDON": (51.5074, -0.1278),
    "SINGAPORE": (1.3521, 103.8198),
}

def fetch_google_forecast(lat: float, lon: float, days: int) -> Dict[str, Dict[str, Any]]:
    """Fetches daily forecast data from Google Weather API."""
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        raise RuntimeError("Google Weather API key is not configured")
    if not global_rate_limiter.acquire():
        raise RuntimeError("Weather API rate limit exceeded")

    url = "https://weather.googleapis.com/v1/forecast/days:lookup"
    response = requests.get(
        url,
        params={"key": api_key, "location.latitude": lat, "location.longitude": lon, "days": days},
        timeout=5,
    )
    response.raise_for_status()
    forecast_days = response.json().get("forecastDays", [])
    if not forecast_days:
        raise RuntimeError("Google Weather API returned no forecast data")

    forecast_by_date = {}
    for forecast in forecast_days:
        display_date = forecast.get("displayDate", {})
        forecast_date = "-".join(
            str(display_date.get(field, "")).zfill(2)
            for field in ("year", "month", "day")
        )
        daytime = forecast.get("daytimeForecast", {})
        condition = daytime.get("weatherCondition", {}).get("description", {}).get("text")
        probability = daytime.get("precipitation", {}).get("probability", {}).get("percent")
        temperature = forecast.get("maxTemperature", {}).get("degrees")
        if not condition or probability is None or temperature is None:
            raise RuntimeError(f"Google Weather API returned incomplete data for {forecast_date}")
        forecast_by_date[forecast_date] = {
            "condition": condition,
            "rain_probability": round(float(probability) / 100.0, 2),
            "temperature_c": float(temperature),
        }
    return forecast_by_date

def get_weather_forecast(destination: str, dates: List[str]) -> List[WeatherForecast]:
    """Generates weather forecasts for a list of travel dates."""
    dest_key = destination.upper().strip()
    if dest_key not in DESTINATION_COORDS:
        raise ValueError(f"No coordinates configured for destination: {destination}")
    lat, lon = DESTINATION_COORDS[dest_key]
    forecast_data = fetch_google_forecast(lat, lon, len(dates))
    forecasts = []
    for date in dates:
        if date not in forecast_data:
            raise RuntimeError(f"Google Weather API returned no forecast for {date}")
        day_data = forecast_data[date]
        prob = day_data["rain_probability"]
        if prob >= 0.65:
            risk = "high"
            indoor = True
        elif prob >= 0.40:
            risk = "medium"
            indoor = False
        elif prob >= 0.20:
            risk = "low"
            indoor = False
        else:
            risk = "low"
            indoor = False

        forecasts.append(WeatherForecast(
            date=date,
            condition=day_data["condition"],
            temperature_c=day_data["temperature_c"],
            rain_probability=prob,
            risk_level=risk,
            indoor_recommended=indoor
        ))
    
    return forecasts
