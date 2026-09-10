import os
import json
import requests
from typing import List, Dict, Any, Optional
from app.utils.logger import track_latency
from app.models.trip_state import FlightOption

def get_secret(secret_name: str) -> Optional[str]:
    """Retrieves a secret from the environment or GCP Secret Manager."""
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
    except Exception as exc:
        raise RuntimeError(f"Unable to retrieve secret '{secret_name}'") from exc

def query_bigquery_delay_risk(carrier: str, origin: str, destination: str, hour: Optional[int] = None) -> float:
    """Queries BigQuery BTS historical delay dataset by route, carrier, and hour."""
    raise NotImplementedError("BigQuery delay-risk queries are not implemented")

def flight_risk_score(flight_no: str, date: str, origin: str = "SFO", destination: str = "TYO", departure_time: str = "") -> float:
    """Computes risk score for a flight number."""
    carrier = flight_no.split()[0] if " " in flight_no else flight_no[:2]
    
    # Extract hour from departure_time (format assumed HH:MM)
    hour = None
    if ":" in departure_time:
        try:
            hour = int(departure_time.split(":")[0])
        except ValueError:
            pass
            
    try:
        return query_bigquery_delay_risk(carrier, origin, destination, hour)
    except (NotImplementedError, RuntimeError):
        # Keep planning available until the historical risk data source is configured.
        return 0.15

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

DESTINATION_IATA_CODES = {
    "TOKYO": "TYO",
    "PARIS": "PAR",
    "LISBON": "LIS",
    "NEW YORK": "NYC",
    "LONDON": "LON",
    "SINGAPORE": "SIN",
    "CHICAGO": "CHI",
}


def _resolve_iata_codes_with_gemini(origin: str, destination: str) -> tuple[str, str]:
    """Resolve origin and destination names to validated IATA airport codes."""
    from google import genai

    client = genai.Client(
        vertexai=True,
        project=os.getenv("GCP_PROJECT", "trippulse-prod"),
        location=os.getenv("GCP_LOCATION", "us-central1"),
    )
    response = client.models.generate_content(
        model=os.getenv("GCP_MODEL", "gemini-2.5-flash"),
        contents=(
            "Return only JSON with three-letter uppercase IATA airport codes for "
            f"the origin {origin!r} and destination {destination!r}. "
            'Use this schema: {"origin": "SFO", "destination": "TYO"}'
        ),
    )
    result = json.loads(getattr(response, "text", ""))
    origin_code = str(result["origin"]).strip().upper()
    destination_code = str(result["destination"]).strip().upper()
    if not all(len(code) == 3 and code.isalpha() for code in (origin_code, destination_code)):
        raise ValueError("Gemini returned invalid IATA airport codes")
    return origin_code, destination_code


def resolve_iata_codes(origin: str, destination: str) -> tuple[str, str]:
    """Resolve both route endpoints with Gemini, using local mappings as fallback."""
    try:
        return _resolve_iata_codes_with_gemini(origin, destination)
    except Exception:
        origin_code = origin.strip().upper()[:3]
        destination_code = DESTINATION_IATA_CODES.get(
            destination.upper().strip(),
            destination.strip().upper()[:3],
        )
        if len(origin_code) != 3 or len(destination_code) != 3:
            raise RuntimeError("Unable to resolve valid IATA codes for the requested route")
        return origin_code, destination_code

@track_latency("aviationstack_fetch_flights")
def fetch_flights_from_api(origin: str, destination: str, date: str) -> List[Dict[str, Any]]:
    """Calls external flight status API (AviationStack) to fetch schedules."""
    api_key = get_secret("FLIGHT_API_KEY")
    if not api_key:
        raise RuntimeError("Flight API key is not configured")

    url = "https://api.aviationstack.com/v1/flights"
    params = {
        "access_key": api_key,
        "dep_iata": origin,
        "arr_iata": destination,
        "flight_date": date,
        "limit": 5
    }
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("error"):
            error = payload["error"]
            message = error.get("message", "Unknown AviationStack error")
            code = error.get("code", "unknown_error")
            raise RuntimeError(f"AviationStack error ({code}): {message}")

        results = payload.get("data", [])
        if not results:
            raise RuntimeError("AviationStack returned no flights for the requested route and date")

        candidates = []
        for r in results:
            flight = r.get("flight", {})
            airline = r.get("airline", {})
            dep = r.get("departure", {})
            arr = r.get("arrival", {})
            
            candidates.append({
                "flight_no": f"{airline.get('iata', 'XX')} {flight.get('number', '000')}",
                "carrier": airline.get('name', 'Independent Carrier'),
                "departure": dep.get('scheduled', '12:00').split('T')[-1][:5],
                "arrival": arr.get('scheduled', '15:00').split('T')[-1][:5],
                # AviationStack supplies schedules/status, not booking fares.
                "price": float(r.get("price") or 0.0),
            })
        return candidates
    except requests.HTTPError as exc:
        detail = exc.response.text[:500] if exc.response is not None else str(exc)
        raise RuntimeError(f"Flight API returned HTTP {exc.response.status_code}: {detail}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Flight API request failed: {exc}") from exc

def search_flights(origin: str, destination: str, date: str, max_price: Optional[float] = None) -> List[FlightOption]:
    """Returns candidate flight options for origin -> destination."""
    orig_code, dest_code = resolve_iata_codes(origin, destination)

    try:
        raw_candidates = fetch_flights_from_api(orig_code, dest_code, date)
    except RuntimeError:
        raw_candidates = CITY_FLIGHT_CATALOG.get(dest_code, [])

    options = []
    for candidate in raw_candidates:
        price = candidate["price"]
        if max_price and price > max_price:
            continue
        risk = flight_risk_score(candidate["flight_no"], date, orig_code, dest_code, candidate["departure"])
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
