import os
import uuid
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Mock Database / State Store
trips = {}

def generate_mock_state(destination, budget):
    """Helper to generate a state object matching the UI requirements."""
    return {
        "selected_flight": {
            "status": "Scheduled",
            "carrier": "Pulse Airways",
            "flight_no": "PA-202",
            "departure_time": "10:30 AM",
            "price": 450.00,
            "risk_score": 0.12
        },
        "selected_hotel": {
            "rating": 4.8,
            "name": f"The {destination} Grand",
            "location": "Downtown District",
            "total_price": 800.00
        },
        "budget_ledger": {
            "flight_spent": 450.00,
            "hotel_spent": 800.00,
            "activity_spent": 200.00,
            "total_budget": budget,
            "remaining_budget": budget - 1450.00
        },
        "activity_plan": [
            {"day": "1", "status": "Confirmed", "name": "City Discovery Tour", "time_slot": "09:00 AM", "location": "Central Square", "cost": 75.00},
            {"day": "2", "status": "Confirmed", "name": "Local Cuisine Workshop", "time_slot": "01:00 PM", "location": "Old Town", "cost": 125.00}
        ],
        "weather_forecast": [
            {"condition": "Sunny", "rain_probability": 0.05},
            {"condition": "Cloudy", "rain_probability": 0.20},
            {"condition": "Clear", "rain_probability": 0.00}
        ]
    }

@app.route('/')
def index():
    """Serve the main concierge dashboard."""
    return render_template('index.html')

@app.route('/api/plan', methods=['POST'])
def plan_trip():
    data = request.json
    dest = data.get('destination', 'Tokyo')
    budget = float(data.get('total_budget', 2000))
    
    trip_id = f"TRIP-{uuid.uuid4().hex[:6].upper()}"
    state = generate_mock_state(dest, budget)
    
    trips[trip_id] = state
    
    return jsonify({
        "trip_id": trip_id,
        "state": state,
        "summary": f"Successfully orchestrated your trip to **{dest}**. I've optimized the flight and hotel selection for your **${budget}** budget."
    })

@app.route('/api/replan', methods=['POST'])
def replan_trip():
    data = request.json
    trip_id = data.get('trip_id')
    disruption = data.get('disruption_type')
    details = data.get('details')

    if trip_id not in trips:
        return jsonify({"detail": "Trip not found"}), 404

    state = trips[trip_id]
    
    # Simulate re-planning logic based on disruption
    if disruption == 'weather_rain':
        state['activity_plan'][1]['status'] = 'Swapped'
        state['activity_plan'][1]['name'] = 'Indoor Museum Tour (Rain Contingency)'
        summary = "I've detected heavy rain for Day 2. I have swapped your outdoor workshop for an indoor Museum Tour."
    elif disruption == 'flight_delay':
        state['selected_flight']['status'] = 'Delayed'
        summary = "Flight delay detected. I am monitoring connection risks and notifying your hotel."
    else:
        summary = "Event handled and itinerary optimized."

    return jsonify({
        "state": state,
        "summary": summary
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').lower()
    
    if 'weather' in message:
        reply = "The forecast looks mostly clear, though there is a slight chance of rain later in the week. Should I prepare an indoor alternative?"
    elif 'budget' in message:
        reply = "You have about 30% of your budget remaining. Would you like me to find a high-end dining experience for your final night?"
    else:
        reply = "I'm your TripPulse assistant. I can help you manage disruptions, adjust your budget, or find new activities!"

    return jsonify({"reply": reply})

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    app.run(debug=True, port=5000)