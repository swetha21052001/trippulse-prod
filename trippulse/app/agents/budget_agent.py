from app.models.trip_state import DisruptionEvent
from app.models.trip_state import TripState
from app.data.ledger import validate, reallocate_funds, update_ledger

from app.utils.logger import log_agent_decision

class BudgetAgent:
    """Agent responsible for financial auditing, budget cap enforcement, and fund reallocation."""
    def __init__(self, name: str = "BudgetAgent"):
        self.name = name

    def process(self, state: TripState) -> TripState:
        log_agent_decision(self.name, state.trip_id, "Starting budget audit process", {"total_budget": state.user_prefs.total_budget})
        ledger = state.budget_ledger
        ledger.total_budget = state.user_prefs.total_budget

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
        ledger.remaining_budget = ledger.total_budget - total_spent
        log_agent_decision(self.name, state.trip_id, "Total spent and remaining budget calculated", {"total_spent": total_spent, "remaining_budget": ledger.remaining_budget})

        # Fund Reallocation Audit if a category overruns its allocation
        if flight_cost > ledger.flight_allocated:
            overage = flight_cost - ledger.flight_allocated
            if ledger.contingency_allocated >= overage:
                reallocate_funds(state, "contingency", "flight", overage)
                log_agent_decision(self.name, state.trip_id, "Reallocated funds for flight overage", {"amount": overage})

        if hotel_cost > ledger.hotel_allocated:
            overage = hotel_cost - ledger.hotel_allocated
            if ledger.contingency_allocated >= overage:
                reallocate_funds(state, "contingency", "hotel", overage)
                log_agent_decision(self.name, state.trip_id, "Reallocated funds for hotel overage", {"amount": overage})

        # Strict validation check
        is_valid, msg = validate(ledger)
        if not is_valid:
            # Add disruption alert for budget overrun
            state.disruptions.append(
                DisruptionEvent(
                    event_id=f"DIS-BUD-OVER",
                    timestamp="",
                    event_type="budget_exceeded",
                    description=msg,
                    severity="high"
                )
            )
            state.status = "Budget Alert"
            log_agent_decision(self.name, state.trip_id, "Budget alert triggered", {"reason": msg})
        else:
            log_agent_decision(self.name, state.trip_id, "Budget validated successfully", {"status": state.status})

        return state
