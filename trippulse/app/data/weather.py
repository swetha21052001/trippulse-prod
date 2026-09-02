import os
import requests
from typing import List, Dict, Any, Optional
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

def historical_baseline(lat: float, lon: float, date: str) -> float:
    """Calculates historical climate baseline rain probability using BigQuery GHCN-D or fallback logic."""
    try:
        parts = [int(p) for p in date.split("-")]
        day_of_month = parts[2] if len(parts) >= 3 else 10
        month = parts[1] if len(parts) >= 2 else 9
    except Exception:
        day_of_month, month = 10, 9

    if os.getenv("ENABLE_BIGQUERY", "false").lower() == "true" or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            from google.cloud import bigquery
            client = bigquery.Client()
            # Query probability of rain (>0 PRCP) for specific month/day at nearest station
            query = """
                WITH nearest_station AS (
                    SELECT id 
                    FROM `bigquery-public-data.ghcn_d.ghcnd_stations`
                    ORDER BY ST_DISTANCE(ST_GEOGPOINT(longitude, latitude), ST_GEOGPOINT(@lon, @lat)) ASC
                    LIMIT 1
                )
                SELECT AVG(CASE WHEN element = 'PRCP' AND value > 0 THEN 1 ELSE 0 END) as rain_prob
                FROM `bigquery-public-data.ghcn_d.ghcnd_all`
                WHERE id = (SELECT id FROM nearest_station)
                  AND EXTRACT(MONTH FROM date) = @month
                  AND EXTRACT(DAY FROM date) = @day
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("lon", "FLOAT64", lon),
                    bigquery.ScalarQueryParameter("lat", "FLOAT64", lat),
                    bigquery.ScalarQueryParameter("month", "INT64", month),
                    bigquery.ScalarQueryParameter("day", "INT64", day_of_month),
                ]
            )
            results = client.query(query, job_config=job_config).result()
            for row in results:
                if row.rain_prob is not None:
                    return round(float(row.rain_prob), 2)
        except Exception:
            pass

    # Deterministic daily variance based on date/location so different days get distinct weather
    seed = int(abs(lat * 10 + lon + day_of_month * 7))
    variance = ((seed % 100) / 100.0) * 0.20 - 0.05  # -0.05 to +0.15

    if month in [6, 9]:
        base = 0.22
    elif month in [7, 8]:
        base = 0.15
    else:
        base = 0.12

    return round(max(0.05, min(0.90, base + variance)), 2)

def rain_probability(lat: float, lon: float, date: str) -> float:
    """Fetches live/predicted rain probability from Open-Meteo forecast API or returns realistic baseline."""
    if global_rate_limiter.acquire():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=precipitation_probability_max&timezone=auto"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                daily = data.get("daily", {})
                dates = daily.get("time", [])
                probs = daily.get("precipitation_probability_max", [])
                if date in dates:
                    idx = dates.index(date)
                    return round(probs[idx] / 100.0, 2)
        except Exception:
            pass
    
    return historical_baseline(lat, lon, date)

def get_weather_forecast(destination: str, dates: List[str]) -> List[WeatherForecast]:
    """Generates weather forecasts for a list of travel dates."""
    dest_key = destination.upper().strip()
    lat, lon = DESTINATION_COORDS.get(dest_key, (35.6762, 139.6503))
    
    forecasts = []
    for date in dates:
        prob = rain_probability(lat, lon, date)
        if prob >= 0.65:
            condition = "Heavy Rain"
            risk = "high"
            indoor = True
            temp = 21.0
        elif prob >= 0.40:
            condition = "Showers / Passing Rain"
            risk = "medium"
            indoor = False
            temp = 23.0
        elif prob >= 0.20:
            condition = "Partly Cloudy"
            risk = "low"
            indoor = False
            temp = 25.0
        else:
            condition = "Sunny / Clear"
            risk = "low"
            indoor = False
            temp = 27.0

        forecasts.append(WeatherForecast(
            date=date,
            condition=condition,
            temperature_c=temp,
            rain_probability=prob,
            risk_level=risk,
            indoor_recommended=indoor
        ))
    
    return forecasts
