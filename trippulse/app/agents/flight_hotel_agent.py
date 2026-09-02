from app.models.trip_state import TripState
from app.data.flights import search_flights
from app.data.hotels import search_hotels

class FlightHotelAgent:
    """Agent responsible for sourcing, evaluating, and selecting flight and hotel options."""
    def __init__(self, name: str = "FlightHotelAgent"):
        self.name = name

    def process(self, state: TripState) -> TripState:
        prefs = state.user_prefs
        
        # 1. Search Flights
        flights = search_flights(
            origin="SFO",
            destination=prefs.destination,
            date=prefs.start_date,
            max_price=prefs.max_flight_price
        )
        state.flight_options = flights

        # Pick best flight considering price and delay risk score
        if flights:
            # Sort by balance of price and risk score (lower is better)
            best_flight = min(flights, key=lambda f: f.price * (1.0 + f.risk_score))
            state.selected_flight = best_flight
            state.budget_ledger.flight_spent = best_flight.price

        # 2. Search Hotels
        num_nights = 3
        max_hotel_budget = (prefs.total_budget * 0.4) # allocate ~40% max to hotel
        hotels = search_hotels(
            location=prefs.destination,
            check_in=prefs.start_date,
            check_out=prefs.end_date,
            budget_limit=max_hotel_budget
        )
        state.hotel_options = hotels

        # Pick best hotel (highest rating within budget)
        if hotels:
            best_hotel = max(hotels, key=lambda h: (h.rating, -h.total_price))
            state.selected_hotel = best_hotel
            state.budget_ledger.hotel_spent = best_hotel.total_price

        return state
