from app.models.trip_state import DisruptionEvent
from app.models.trip_state import TripState
from app.utils.logger import log_agent_decision

class BudgetAgent:
    """Agent responsible for financial auditing, budget cap enforcement, and fund reallocation."""
    def __init__(self, name: str = "BudgetAgent"):
        self.name = name

    def process(self, state: TripState) -> TripState:
        log_agent_decision(self.name, state.trip_id, "Starting trip cost calculation")
        ledger = state.budget_ledger

        # Calculate actual totals
        flight_cost = state.selected_flight.price if state.selected_flight else 0.0
        hotel_cost = state.selected_hotel.total_price if state.selected_hotel else 0.0
        activity_cost = sum(act.cost for act in state.activity_plan if act.status != "Cancelled")

        ledger.flight_spent = flight_cost
        log_agent_decision(self.name, state.trip_id, "Flight cost calculated", {"flight_spent": flight_cost})
        ledger.hotel_spent = hotel_cost
        log_agent_decision(self.name, state.trip_id, "Hotel cost calculated", {"hotel_spent": hotel_cost})
        ledger.activity_spent = activity_cost
        log_agent_decision(self.name, state.trip_id, "Activity cost calculated", {"activity_spent": activity_cost})

        total_spent = flight_cost + hotel_cost + activity_cost
        ledger.total_budget = total_spent
        ledger.remaining_budget = 0.0
        log_agent_decision(self.name, state.trip_id, "Total trip cost calculated", {"total_cost": total_spent})

        return state
