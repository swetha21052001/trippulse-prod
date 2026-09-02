import unittest
from app.models.trip_state import TripState, UserPrefs, BudgetLedger
from app.data.ledger import validate, reallocate_funds

class TestBudgetCap(unittest.TestCase):
    def test_ledger_validation(self):
        ledger = BudgetLedger(total_budget=1000.0, flight_spent=500.0, hotel_spent=400.0, activity_spent=50.0)
        is_valid, msg = validate(ledger)
        self.assertTrue(is_valid)

        # Test over-spending violation
        ledger_over = BudgetLedger(total_budget=1000.0, flight_spent=700.0, hotel_spent=400.0, activity_spent=50.0)
        is_valid, msg = validate(ledger_over)
        self.assertFalse(is_valid)
        self.assertIn("exceeds", msg.lower())

    def test_fund_reallocation(self):
        state = TripState(trip_id="TEST-BUDGET-01", user_prefs=UserPrefs(total_budget=2000.0))
        ledger = state.budget_ledger
        ledger.flight_allocated = 600.0
        ledger.contingency_allocated = 300.0

        state = reallocate_funds(state, "contingency", "flight", 100.0)
        self.assertEqual(state.budget_ledger.flight_allocated, 700.0)
        self.assertEqual(state.budget_ledger.contingency_allocated, 200.0)

if __name__ == "__main__":
    unittest.main()
