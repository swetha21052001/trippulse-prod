import logging
import time
import functools
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Basic configuration for TripPulse logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TripPulse")

def log_agent_decision(agent_name: str, trip_id: str, action: str, details: Optional[Dict[str, Any]] = None):
    """
    Logs structured information about decisions made by an agent.
    Useful for debugging multi-agent orchestration flows.
    """
    log_entry = {
        "severity": "INFO",
        "type": "AGENT_DECISION",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent_name,
        "trip_id": trip_id,
        "action": action,
        "details": details or {}
    }
    logger.info(json.dumps(log_entry))

def track_latency(operation_name: str):
    """
    Decorator to track the execution time of a function.
    Specifically targeted at external API calls (e.g., Places API, AviationStack).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            status = "success"
            try:
                return func(*args, **kwargs)
            except Exception as e:
                status = "error"
                raise e
            finally:
                latency_ms = (time.perf_counter() - start_time) * 1000
                logger.info(json.dumps({
                    "severity": "INFO",
                    "type": "API_LATENCY",
                    "operation": operation_name,
                    "latency_ms": round(latency_ms, 2),
                    "status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
        return wrapper
    return decorator