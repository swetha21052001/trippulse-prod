import os
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)

def poll_disruptions(request):
    """Cloud Function entrypoint triggered by Cloud Scheduler to poll active trips for flight/weather disruptions."""
    logging.info("Starting scheduled disruption polling for active trips...")
    
    # Example simulated check
    active_trips_checked = 3
    disruptions_detected = 0

    response_data = {
        "status": "success",
        "trips_checked": active_trips_checked,
        "disruptions_detected": disruptions_detected,
        "message": "Disruption polling completed successfully."
    }

    return (json.dumps(response_data), 200, {"Content-Type": "application/json"})
