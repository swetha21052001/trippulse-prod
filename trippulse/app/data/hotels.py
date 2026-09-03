import os
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.utils.logger import track_latency
from app.models.trip_state import HotelOption

HOTEL_CACHE: Dict[str, List[HotelOption]] = {}

def get_firestore_client():
    """Attempts to create a Firestore client."""
    if not (os.getenv("ENABLE_FIRESTORE", "false").lower() == "true" or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")):
        return None
    try:
        from google.cloud import firestore
        project_id = os.getenv("GCP_PROJECT", "trippulse-prod")
        return firestore.Client(project=project_id)
    except Exception:
        return None

def get_hotel_api_key() -> Optional[str]:
    """Retrieves the Google Places API key from the environment or Secret Manager."""
    api_key = os.getenv("HOTEL_API_KEY")
    if api_key:
        return api_key
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GCP_PROJECT", "trippulse-prod")
        name = f"projects/{project_id}/secrets/hotel-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as exc:
        raise RuntimeError("Unable to retrieve hotel API key") from exc

@track_latency("google_places_fetch_hotels")
def fetch_from_places_api(location: str, nights: int) -> List[HotelOption]:
    """Calls Google Places API to discover hotels in the target location."""
    api_key = get_hotel_api_key()
    if not api_key:
        raise RuntimeError("Hotel API key is not configured")

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": f"top rated hotels in {location}", "type": "lodging", "key": api_key}
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        
        results = resp.json().get("results", [])
        hotels = []
        for r in results[:5]:
            # Places API doesn't provide pricing; simulating based on rating
            price_night = 120.0 + (r.get("rating", 4.0) * 45.0)
            hotels.append(HotelOption(
                hotel_id=r["place_id"],
                name=r["name"],
                location=r.get("formatted_address", location),
                price_per_night=round(price_night, 2),
                total_price=round(price_night * nights, 2),
                rating=float(r.get("rating", 0.0)),
                amenities=r.get("types", ["lodging"]),
                is_indoor_friendly=True
            ))
        if not hotels:
            raise RuntimeError("Places API returned no hotel data")
        return hotels
    except requests.RequestException as exc:
        raise RuntimeError("Places hotel request failed") from exc

CITY_HOTEL_CATALOG = {
    "TOKYO": [
        {"hotel_id": "HTL-TYO-01", "name": "Park Hyatt Tokyo", "location": "Shinjuku, Tokyo", "price_per_night": 280.0, "total_price": 840.0, "rating": 4.8, "amenities": ["Spa", "Pool", "Indoor Dining", "City View"], "is_indoor_friendly": True},
        {"hotel_id": "HTL-TYO-02", "name": "Hotel Gracery Shinjuku", "location": "Shinjuku, Tokyo", "price_per_night": 160.0, "total_price": 480.0, "rating": 4.4, "amenities": ["Free WiFi", "Central Location", "Indoor Lounge"], "is_indoor_friendly": True},
        {"hotel_id": "HTL-TYO-03", "name": "Shibuya Stream Excel Hotel", "location": "Shibuya, Tokyo", "price_per_night": 190.0, "total_price": 570.0, "rating": 4.6, "amenities": ["Gym", "Direct Station Access", "Co-working Space"], "is_indoor_friendly": True}
    ],
    "PARIS": [
        {"hotel_id": "HTL-PAR-01", "name": "Le Meurice Paris", "location": "1st Arr., Paris", "price_per_night": 290.0, "total_price": 870.0, "rating": 4.9, "amenities": ["Michelin Dining", "Spa", "Louver View"], "is_indoor_friendly": True},
        {"hotel_id": "HTL-PAR-02", "name": "Hôtel Plaza Athénée", "location": "8th Arr., Paris", "price_per_night": 260.0, "total_price": 780.0, "rating": 4.7, "amenities": ["Balcony View", "Courtyard Restaurant", "Bar"], "is_indoor_friendly": True},
        {"hotel_id": "HTL-PAR-03", "name": "CitizenM Paris Gare de Lyon", "location": "12th Arr., Paris", "price_per_night": 150.0, "total_price": 450.0, "rating": 4.5, "amenities": ["Rooftop Bar", "Co-working Lounge", "Fast WiFi"], "is_indoor_friendly": True}
    ],
    "LISBON": [
        {"hotel_id": "HTL-LIS-01", "name": "Valverde Hotel Relais & Châteaux", "location": "Avenida da Liberdade, Lisbon", "price_per_night": 210.0, "total_price": 630.0, "rating": 4.8, "amenities": ["Patio Pool", "Live Fado", "Cocktail Lounge"], "is_indoor_friendly": True},
        {"hotel_id": "HTL-LIS-02", "name": "Corinthia Lisbon Hotel", "location": "Sete Rios, Lisbon", "price_per_night": 170.0, "total_price": 510.0, "rating": 4.6, "amenities": ["Luxury Spa", "Indoor Heated Pool", "Executive Club"], "is_indoor_friendly": True},
        {"hotel_id": "HTL-LIS-03", "name": "Memmo Alfama Hotel", "location": "Alfama, Lisbon", "price_per_night": 140.0, "total_price": 420.0, "rating": 4.5, "amenities": ["River View Terrace", "Wine Bar", "Central Old Town"], "is_indoor_friendly": True}
    ],
    "NEW YORK": [
        {"hotel_id": "HTL-NYC-01", "name": "The Plaza Hotel New York", "location": "Fifth Avenue, NYC", "price_per_night": 310.0, "total_price": 930.0, "rating": 4.9, "amenities": ["Champagne Bar", "Guerlain Spa", "Central Park Access"], "is_indoor_friendly": True},
        {"hotel_id": "HTL-NYC-02", "name": "Arlo Midtown NYC", "location": "Midtown West, NYC", "price_per_night": 180.0, "total_price": 540.0, "rating": 4.5, "amenities": ["Rooftop Lounge", "Co-working Spaces", "Gym"], "is_indoor_friendly": True},
        {"hotel_id": "HTL-NYC-03", "name": "Moxy NYC Times Square", "location": "Times Square, NYC", "price_per_night": 160.0, "total_price": 480.0, "rating": 4.4, "amenities": ["Magic Hour Rooftop", "Seafood Lounge", "Fitness Center"], "is_indoor_friendly": True}
    ],
    "LONDON": [
        {"hotel_id": "HTL-LON-01", "name": "The Savoy London", "location": "Strand, London", "price_per_night": 300.0, "total_price": 900.0, "rating": 4.9, "amenities": ["Gordon Ramsay Grill", "Thames View", "American Bar"], "is_indoor_friendly": True},
        {"hotel_id": "HTL-LON-02", "name": "CitizenM Tower of London", "location": "City of London", "price_per_night": 165.0, "total_price": 495.0, "rating": 4.6, "amenities": ["CloudM Skybar", "Direct Tube Access", "Express Check-in"], "is_indoor_friendly": True},
        {"hotel_id": "HTL-LON-03", "name": "The Hoxton Holborn", "location": "Holborn, London", "price_per_night": 185.0, "total_price": 555.0, "rating": 4.5, "amenities": ["Hubbub Coffee", "All-Day Restaurant", "Lobby Bar"], "is_indoor_friendly": True}
    ]
}

def _calculate_nights(check_in: str, check_out: str) -> int:
    try:
        d1 = datetime.strptime(check_in, "%Y-%m-%d")
        d2 = datetime.strptime(check_out, "%Y-%m-%d")
        return max(1, (d2 - d1).days)
    except Exception:
        return 1

def search_hotels(location: str, check_in: str, check_out: str, budget_limit: Optional[float] = None) -> List[HotelOption]:
    """Searches for hotel options in location within date range, checking cache first."""
    cache_key = f"{location.lower().strip()}_{check_in}_{check_out}"
    if cache_key in HOTEL_CACHE: return HOTEL_CACHE[cache_key]

    db = get_firestore_client()
    if db:
        try:
            doc_ref = db.collection("hotel-cache").document(cache_key)
            doc = doc_ref.get()
            if doc.exists:
                raw_data = doc.to_dict().get("hotels", [])
                hotels = [HotelOption(**h) for h in raw_data]
                HOTEL_CACHE[cache_key] = hotels
                return hotels
        except Exception:
            pass

    hotels = fetch_from_places_api(location, _calculate_nights(check_in, check_out))
    if not hotels:
        raise RuntimeError("Places API returned no hotel options")

    if budget_limit is not None:
        hotels = [hotel for hotel in hotels if hotel.total_price <= budget_limit]

    if not hotels:
        raise RuntimeError("Places API returned no hotels within the requested budget")

    HOTEL_CACHE[cache_key] = hotels

    # Attempt saving to Firestore
    if db:
        try:
            db.collection("hotel-cache").document(cache_key).set({"hotels": [h.dict() for h in hotels]})
        except Exception:
            pass

    return hotels
