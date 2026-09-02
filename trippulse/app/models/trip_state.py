from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class UserPrefs(BaseModel):
    destination: str = "Tokyo"
    start_date: str = "2026-09-10"
    end_date: str = "2026-09-13"
    total_budget: float = 2000.0
    travel_style: str = "balanced" # luxury, budget, balanced, adventurous
    interests: List[str] = Field(default_factory=lambda: ["culture", "food", "sightseeing"])
    max_flight_price: Optional[float] = 800.0

class FlightOption(BaseModel):
    flight_no: str
    carrier: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    price: float
    risk_score: float = 0.0 # 0.0 low delay risk to 1.0 high delay risk
    status: str = "Scheduled" # Scheduled, Delayed, Cancelled

class HotelOption(BaseModel):
    hotel_id: str
    name: str
    location: str
    price_per_night: float
    total_price: float
    rating: float = 4.5
    amenities: List[str] = Field(default_factory=list)
    is_indoor_friendly: bool = True

class WeatherForecast(BaseModel):
    date: str
    condition: str # Sunny, Rainy, Stormy, Cloudy
    temperature_c: float
    rain_probability: float # 0.0 to 1.0
    risk_level: str = "low" # low, medium, high
    indoor_recommended: bool = False

class ActivityPlan(BaseModel):
    activity_id: str
    day: int
    time_slot: str # Morning, Afternoon, Evening
    name: str
    category: str # Outdoor, Cultural, Dining, Relaxation
    cost: float
    location: str
    is_outdoor: bool = True
    rain_alternative: Optional[str] = None
    status: str = "Confirmed" # Confirmed, Swapped, Cancelled

class LedgerTransaction(BaseModel):
    timestamp: str
    category: str
    description: str
    amount: float
    type: str = "debit" # debit or credit

class BudgetLedger(BaseModel):
    total_budget: float = 2000.0
    flight_allocated: float = 600.0
    hotel_allocated: float = 700.0
    activity_allocated: float = 400.0
    contingency_allocated: float = 300.0
    flight_spent: float = 0.0
    hotel_spent: float = 0.0
    activity_spent: float = 0.0
    remaining_budget: float = 2000.0
    transactions: List[LedgerTransaction] = Field(default_factory=list)

class DisruptionEvent(BaseModel):
    event_id: str
    timestamp: str
    event_type: str # flight_delay, weather_rain, budget_exceeded
    description: str
    affected_day: Optional[int] = None
    severity: str = "medium" # low, medium, high

class TripState(BaseModel):
    trip_id: str
    user_prefs: UserPrefs
    flight_options: List[FlightOption] = Field(default_factory=list)
    selected_flight: Optional[FlightOption] = None
    hotel_options: List[HotelOption] = Field(default_factory=list)
    selected_hotel: Optional[HotelOption] = None
    weather_forecast: List[WeatherForecast] = Field(default_factory=list)
    activity_plan: List[ActivityPlan] = Field(default_factory=list)
    budget_ledger: BudgetLedger = Field(default_factory=BudgetLedger)
    disruptions: List[DisruptionEvent] = Field(default_factory=list)
    status: str = "Planning" # Planning, Confirmed, Re-planning, Complete
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
