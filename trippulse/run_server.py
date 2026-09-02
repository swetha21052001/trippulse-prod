import os
import uuid
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.models.trip_state import UserPrefs
from app.orchestrator import global_orchestrator

app = FastAPI(title="TripPulse Multi-Agent Concierge")
templates = Jinja2Templates(directory="templates")

class ReplanRequest(BaseModel):
    trip_id: str
    disruption_type: str
    details: str = ""

class ChatRequest(BaseModel):
    trip_id: str
    message: str

def serialize_state(state):
    if hasattr(state, "model_dump"):
        return state.model_dump(mode="json")
    return state.dict()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main concierge dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "TripPulse Multi-Agent Concierge", "version": "1.0.0"}

@app.post("/api/plan")
async def plan_trip(prefs: UserPrefs):
    trip_id = f"TRIP-{uuid.uuid4().hex[:8].upper()}"
    state = global_orchestrator.get_or_create_session(trip_id, prefs)
    state = await global_orchestrator.run_pipeline(state)
    return {
        "trip_id": trip_id,
        "state": serialize_state(state),
        "summary": global_orchestrator.concierge.generate_trip_summary(state),
    }

@app.get("/api/trip/{trip_id}")
async def get_trip(trip_id: str):
    state = global_orchestrator.session_store.load(trip_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return serialize_state(state)

@app.post("/api/replan")
async def replan_trip(req: ReplanRequest):
    state = global_orchestrator.session_store.load(req.trip_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    state = await global_orchestrator.handle_disruption(state, req.disruption_type, req.details)
    return {
        "trip_id": req.trip_id,
        "state": serialize_state(state),
        "summary": global_orchestrator.concierge.generate_trip_summary(state),
    }

@app.post("/api/chat")
async def chat(req: ChatRequest):
    state = global_orchestrator.session_store.load(req.trip_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return { # type: ignore
        "reply": global_orchestrator.concierge.respond(req.message, state),
        "trip_id": req.trip_id,
    }

@app.post("/api/disruption/webhook")
async def pubsub_webhook(envelope: Dict[str, Any] = Body(...)):
    """Handles incoming Pub/Sub push notifications for trip disruptions."""
    try:
        state = await global_orchestrator.process_pubsub_event(envelope)
        
        if state:
            return {
                "status": "success",
                "trip_id": state.trip_id,
                "orchestration_status": state.status
            }

        return {"status": "no_action", "reason": "Trip not found or event ignored"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(exc)}")


if __name__ == '__main__':
    import uvicorn
    server_port = os.environ.get('PORT', '8080')
    uvicorn.run(app, host='0.0.0.0', port=int(server_port))