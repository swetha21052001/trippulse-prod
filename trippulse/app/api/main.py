import os
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.models.trip_state import UserPrefs, TripState
from app.orchestrator import global_orchestrator

security = HTTPBearer(auto_error=False)


def require_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    api_key = os.getenv("TRIPPULSE_API_KEY")
    if not api_key:
        return

    if credentials is None or credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )


app = FastAPI(
    title="TripPulse — Multi-Agent Travel Concierge API",
    description="Backend API powering multi-agent travel planning, disruption detection, and financial budget auditing.",
    version="1.0.0"
)

# Request Models
class PlanRequest(BaseModel):
    destination: str = "Tokyo"
    total_budget: float = 2000.0
    start_date: str = "2026-09-10"
    end_date: str = "2026-09-13"
    travel_style: str = "balanced"

class ChatRequest(BaseModel):
    trip_id: str
    message: str

class ReplanRequest(BaseModel):
    trip_id: str
    disruption_type: str # flight_delay, weather_rain, budget_exceeded
    details: str = ""

@app.get("/api/health")
def health_check(_=Depends(require_api_key)):
    return {"status": "ok", "service": "TripPulse Multi-Agent Concierge", "version": "1.0.0"}

@app.post("/api/plan")
def create_trip_plan(req: PlanRequest, _=Depends(require_api_key)):
    trip_id = f"TRIP-{uuid.uuid4().hex[:8].upper()}"
    prefs = UserPrefs(
        destination=req.destination,
        total_budget=req.total_budget,
        start_date=req.start_date,
        end_date=req.end_date,
        travel_style=req.travel_style
    )

    state = global_orchestrator.get_or_create_session(trip_id, prefs)
    updated_state = global_orchestrator.run_pipeline(state)

    summary = global_orchestrator.concierge.generate_trip_summary(updated_state)
    return {"trip_id": trip_id, "state": updated_state, "summary": summary}

@app.get("/api/trip/{trip_id}")
def get_trip(trip_id: str, _=Depends(require_api_key)):
    state = global_orchestrator.get_or_create_session(trip_id)
    return state

@app.post("/api/chat")
def chat_with_concierge(req: ChatRequest, _=Depends(require_api_key)):
    state = global_orchestrator.get_or_create_session(req.trip_id)
    reply = global_orchestrator.concierge.respond(req.message, state)
    return {"reply": reply, "trip_id": req.trip_id}

@app.post("/api/replan")
def trigger_replan(req: ReplanRequest, _=Depends(require_api_key)):
    state = global_orchestrator.get_or_create_session(req.trip_id)
    updated_state = global_orchestrator.handle_disruption(state, req.disruption_type, req.details)
    summary = global_orchestrator.concierge.generate_trip_summary(updated_state)
    return {"trip_id": req.trip_id, "state": updated_state, "summary": summary}

# Mount static web interface
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Welcome to TripPulse API. Visit /docs for Swagger UI."}
