# TripPulse — Multi-Agent Travel Concierge

TripPulse is an event-driven multi-agent travel concierge system built with FastAPI, Google Cloud Platform (BigQuery, Secret Manager, Firestore, Vertex AI/Gemini), and an interactive web dashboard.

## System Architecture

```
[ User UI / API ] ──> [ Concierge Agent ]
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [ Flight/Hotel Agent ]             [ Weather Agent ]
   (BigQuery/SecretMgr)            (Open-Meteo Forecast)
            │                                 │
            └────────────────┬────────────────┘
                             ▼
                     [ Budget Agent ]
                  (Financial Ledger Audit)
```

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run tests:
   ```bash
   pytest tests/
   ```

3. Launch local dev server:
   ```bash
   uvicorn app.api.main:app --port 8080 --reload
   ```

4. Open `http://localhost:8080` in your web browser.

## Disruption Re-Planning
TripPulse automatically detects live disruptions (weather rain forecasts >60% or flight delay risk alerts) and re-allocates funds or swaps outdoor activities for top-rated indoor alternatives while maintaining strict budget limits.
