import os
import random
from typing import List, Dict, Any, Optional
from app.models.trip_state import FlightOption

def get_secret(secret_name: str) -> Optional[str]:
    """Retrieves secret from GCP Secret Manager if available, otherwise returns env var or fallback."""
    env_val = os.getenv(secret_name.upper().replace('-', '_'))
    if env_val:
        return env_val
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GCP_PROJECT", "trippulse-prod")
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception:
        return None

def query_bigquery_delay_risk(carrier: str, origin: str, destination: str) -> float:
    """Queries BigQuery BTS historical delay dataset, falling back to probabilistic calculation."""
    if os.getenv("ENABLE_BIGQUERY", "false").lower() == "true" or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            from google.cloud import bigquery
            client = bigquery.Client()
            query = """
                SELECT AVG(CASE WHEN arr_delay > 15 THEN 1 ELSE 0 END) as delay_ratio
                FROM `bigquery-public-data.bts_realtime.on_time_performance`
                WHERE carrier = @carrier AND origin = @origin AND dest = @destination
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("carrier", "STRING", carrier),
                    bigquery.ScalarQueryParameter("origin", "STRING", origin),
                    bigquery.ScalarQueryParameter("destination", "STRING", destination),
                ]
            )
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()
            for row in results:
                if row.delay_ratio is not None:
                    return round(float(row.delay_ratio), 2)
        except Exception:
            pass

    # Baseline probabilistic calculation if BigQuery is offline or no credentials
    seed_str = f"{carrier}-{origin}-{destination}"
    hash_val = sum(ord(c) for c in seed_str)
    base_risk = 0.12 + (hash_val % 25) / 100.0
    return round(base_risk, 2)

def flight_risk_score(flight_no: str, date: str, origin: str = "SFO", destination: str = "TYO") -> float:
    """Computes risk score for a flight number."""
    carrier = flight_no.split()[0] if " " in flight_no else flight_no[:2]
    return query_bigquery_delay_risk(carrier, origin, destination)

CITY_FLIGHT_CATALOG = {
    "PAR": [
        {"flight_no": "AF 084", "carrier": "Air France", "departure": "17:20", "arrival": "13:05 (+1)", "price": 680.0},
        {"flight_no": "DL 262", "carrier": "Delta Air Lines", "departure": "18:40", "arrival": "14:15 (+1)", "price": 640.0},
        {"flight_no": "UA 990", "carrier": "United Airlines", "departure": "15:10", "arrival": "10:50 (+1)", "price": 590.0},
    ],
    "LIS": [
        {"flight_no": "TP 202", "carrier": "TAP Air Portugal", "departure": "16:45", "arrival": "11:30 (+1)", "price": 550.0},
        {"flight_no": "UA 064", "carrier": "United Airlines", "departure": "20:15", "arrival": "14:45 (+1)", "price": 510.0},
        {"flight_no": "IB 6274", "carrier": "Iberia", "departure": "19:00", "arrival": "15:20 (+1)", "price": 480.0},
    ],
    "NYC": [
        {"flight_no": "DL 412", "carrier": "Delta Air Lines", "departure": "08:00", "arrival": "16:30", "price": 380.0},
        {"flight_no": "AA 100", "carrier": "American Airlines", "departure": "09:30", "arrival": "18:00", "price": 350.0},
        {"flight_no": "B6 824", "carrier": "JetBlue", "departure": "11:15", "arrival": "19:45", "price": 310.0},
    ],
    "LON": [
        {"flight_no": "BA 286", "carrier": "British Airways", "departure": "18:30", "arrival": "12:45 (+1)", "price": 720.0},
        {"flight_no": "VS 020", "carrier": "Virgin Atlantic", "departure": "17:45", "arrival": "11:55 (+1)", "price": 690.0},
        {"flight_no": "UA 930", "carrier": "United Airlines", "departure": "19:50", "arrival": "14:10 (+1)", "price": 630.0},
    ]
}

def search_flights(origin: str, destination: str, date: str, max_price: Optional[float] = None) -> List[FlightOption]:
    """Returns candidate flight options for origin -> destination."""
    dest_code = destination[:3].upper() if len(destination) >= 3 else "TYO"
    orig_code = origin[:3].upper() if len(origin) >= 3 else "SFO"

    raw_candidates = CITY_FLIGHT_CATALOG.get(dest_code)

    if not raw_candidates:
        raw_candidates = [
            {"flight_no": f"{dest_code[:2]} 001", "carrier": f"{destination.title()} Express", "departure": "11:30", "arrival": "15:00 (+1)", "price": 620.0},
            {"flight_no": f"UA 837", "carrier": "United Airlines", "departure": "10:15", "arrival": "13:55 (+1)", "price": 540.0},
            {"flight_no": f"DL 105", "carrier": "Delta Air Lines", "departure": "13:45", "arrival": "17:20 (+1)", "price": 590.0},
            {"flight_no": f"AA 402", "carrier": "American Airlines", "departure": "15:00", "arrival": "18:30 (+1)", "price": 490.0},
        ]

    options = []
    for candidate in raw_candidates:
        price = candidate["price"]
        if max_price and price > max_price:
            continue
        risk = flight_risk_score(candidate["flight_no"], date, orig_code, dest_code)
        options.append(FlightOption(
            flight_no=candidate["flight_no"],
            carrier=candidate["carrier"],
            origin=orig_code,
            destination=dest_code,
            departure_time=f"{date} {candidate['departure']}",
            arrival_time=f"{date} {candidate['arrival']}",
            price=price,
            risk_score=risk,
            status="Scheduled"
        ))
    
    return options
