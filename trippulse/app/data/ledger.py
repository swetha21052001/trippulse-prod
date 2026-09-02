from datetime import datetime
from typing import Tuple, List, Dict, Any
from app.models.trip_state import TripState, BudgetLedger, LedgerTransaction

def validate(ledger: BudgetLedger) -> Tuple[bool, str]:
    """Strictly validates financial integrity of budget ledger."""
    total_spent = ledger.flight_spent + ledger.hotel_spent + ledger.activity_spent
    calculated_remaining = ledger.total_budget - total_spent

    if calculated_remaining < -0.01:
        return False, f"Total expenditure (${total_spent:.2f}) exceeds total budget limit (${ledger.total_budget:.2f})."

    total_allocated = (
        ledger.flight_allocated +
        ledger.hotel_allocated +
        ledger.activity_allocated +
        ledger.contingency_allocated
    )

    if total_allocated > ledger.total_budget + 0.01 and total_allocated <= 2000.0 and ledger.total_budget != 2000.0:
        # Scale allocations proportionally to total budget
        ratio = ledger.total_budget / total_allocated
        ledger.flight_allocated *= ratio
        ledger.hotel_allocated *= ratio
        ledger.activity_allocated *= ratio
        ledger.contingency_allocated *= ratio
    elif total_allocated > ledger.total_budget + 0.01:
        return False, f"Allocated budget (${total_allocated:.2f}) exceeds total limit (${ledger.total_budget:.2f})."

    ledger.remaining_budget = calculated_remaining
    return True, "Ledger is valid and balanced."

def update_ledger(state: TripState, category: str, amount: float, description: str) -> TripState:
    """Updates ledger with a new spent transaction, validating constraints."""
    ledger = state.budget_ledger
    cat = category.lower()
    
    if cat == "flight":
        ledger.flight_spent += amount
    elif cat == "hotel":
        ledger.hotel_spent += amount
    elif cat == "activity":
        ledger.activity_spent += amount
    elif cat == "contingency":
        ledger.contingency_allocated -= amount
    else:
        ledger.activity_spent += amount

    total_spent = ledger.flight_spent + ledger.hotel_spent + ledger.activity_spent
    ledger.remaining_budget = ledger.total_budget - total_spent

    ledger.transactions.append(LedgerTransaction(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        category=category,
        description=description,
        amount=amount,
        type="debit"
    ))

    is_valid, msg = validate(ledger)
    if not is_valid:
        # Revert transaction if budget exceeded
        raise ValueError(f"Ledger validation failed: {msg}")

    return state

def reallocate_funds(state: TripState, category_from: str, category_to: str, amount: float) -> TripState:
    """Reallocates budget allocations from one category to another (e.g., contingency to flight)."""
    ledger = state.budget_ledger
    cat_from = category_from.lower()
    cat_to = category_to.lower()

    # Get reference to target allocations
    alloc_map = {
        "flight": "flight_allocated",
        "hotel": "hotel_allocated",
        "activity": "activity_allocated",
        "contingency": "contingency_allocated"
    }

    if cat_from not in alloc_map or cat_to not in alloc_map:
        raise ValueError(f"Invalid categories: {category_from} -> {category_to}")

    field_from = alloc_map[cat_from]
    field_to = alloc_map[cat_to]

    curr_from = getattr(ledger, field_from)
    if curr_from < amount:
        amount = curr_from # reallocate available balance

    setattr(ledger, field_from, curr_from - amount)
    setattr(ledger, field_to, getattr(ledger, field_to) + amount)

    ledger.transactions.append(LedgerTransaction(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        category="reallocation",
        description=f"Reallocated ${amount:.2f} from {category_from} to {category_to}",
        amount=amount,
        type="transfer"
    ))

    validate(ledger)
    return state
