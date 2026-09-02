import os
import uuid
from flask import Flask, jsonify, render_template, request
from pydantic import ValidationError

# Keep the Flask deployment entrypoint named app.py while allowing imports from
# the application package in the sibling app/ directory.
if __name__ == "app":
    __path__ = [os.path.join(os.path.dirname(__file__), "app")]

from app.models.trip_state import UserPrefs
from app.orchestrator import global_orchestrator

app = Flask(__name__)

def serialize_state(state):
    if hasattr(state, "model_dump"):
        return state.model_dump(mode="json")
    return state.dict()


def request_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")
    return data


def error_response(message, status_code):
    return jsonify({"detail": message}), status_code

@app.route('/')
def index():
    """Serve the main concierge dashboard."""
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "TripPulse Multi-Agent Concierge", "version": "1.0.0"})

@app.route('/api/plan', methods=['POST'])
def plan_trip():
    try:
        data = request_data()
        prefs = UserPrefs(
            destination=data.get('destination', 'Tokyo'),
            total_budget=data.get('total_budget', 2000.0),
            start_date=data.get('start_date', '2026-09-10'),
            end_date=data.get('end_date', '2026-09-13'),
            travel_style=data.get('travel_style', 'balanced'),
            interests=data.get('interests', ['culture', 'food', 'sightseeing']),
            max_flight_price=data.get('max_flight_price', 800.0),
        )
    except (ValueError, TypeError, ValidationError) as exc:
        return error_response(str(exc), 400)

    trip_id = f"TRIP-{uuid.uuid4().hex[:8].upper()}"
    state = global_orchestrator.get_or_create_session(trip_id, prefs)
    state = global_orchestrator.run_pipeline(state)
    return jsonify({
        "trip_id": trip_id,
        "state": serialize_state(state),
        "summary": global_orchestrator.concierge.generate_trip_summary(state),
    })

@app.route('/api/trip/<trip_id>', methods=['GET'])
def get_trip(trip_id):
    state = global_orchestrator.session_store.load(trip_id)
    if state is None:
        return error_response("Trip not found", 404)
    return jsonify(serialize_state(state))

@app.route('/api/replan', methods=['POST'])
def replan_trip():
    try:
        data = request_data()
        trip_id = data['trip_id']
        disruption = data['disruption_type']
    except (ValueError, KeyError) as exc:
        return error_response(str(exc), 400)

    state = global_orchestrator.session_store.load(trip_id)
    if state is None:
        return error_response("Trip not found", 404)
    state = global_orchestrator.handle_disruption(state, disruption, data.get('details', ''))
    return jsonify({
        "trip_id": trip_id,
        "state": serialize_state(state),
        "summary": global_orchestrator.concierge.generate_trip_summary(state),
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request_data()
        trip_id = data['trip_id']
        message = data['message']
    except (ValueError, KeyError) as exc:
        return error_response(str(exc), 400)

    state = global_orchestrator.session_store.load(trip_id)
    if state is None:
        return error_response("Trip not found", 404)
    return jsonify({
        "reply": global_orchestrator.concierge.respond(message, state),
        "trip_id": trip_id,
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    app.run(debug=True, port=5000)