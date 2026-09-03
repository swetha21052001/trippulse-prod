# TripPulse — Multi-Agent Travel Concierge
## Step-by-Step Build Guide (Google Cloud Console + Local Machine)

This guide walks through every phase, with concrete steps split into **Console** (things you click in the GCP web UI) and **Local** (things you run in your terminal).

---

## Phase 1 — Foundations

### 1.1 Create the GCP Project

**Console**
1. Go to [console.cloud.google.com](https://console.cloud.google.com).
2. Click the project dropdown (top left) → **New Project**.
3. Name it `trippulse-prod` (or similar) → **Create**.
4. Once created, select it from the project dropdown so it's active.
5. Go to **Billing** → link a billing account to the project (required for BigQuery/Vertex AI usage beyond free tier).

**Console — Enable APIs**
6. Go to **APIs & Services → Library**. Enable each of the following individually:
   - BigQuery API
   - Vertex AI API
   - Cloud Run API
   - Cloud Functions API
   - Cloud Scheduler API
   - Pub/Sub API
   - Secret Manager API
   - Firestore API

### 1.2 Create a Service Account

**Console**
1. Go to **IAM & Admin → Service Accounts → Create Service Account**.
2. Name: `trippulse-agent-sa`.
3. Grant roles:
   - `BigQuery Data Viewer`
   - `BigQuery Job User`
   - `Vertex AI User`
   - `Secret Manager Secret Accessor`
   - `Firestore User`
4. Click **Done**, then open the service account → **Keys → Add Key → JSON**. Download the key file.

**Local**
```bash
mkdir -p ~/trippulse && cd ~/trippulse
mv ~/Downloads/trippulse-agent-sa-*.json ./sa-key.json
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/trippulse/sa-key.json"
```

### 1.3 Local Environment Setup

**Local**
```bash
python3 --version   # confirm 3.11+
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install google-adk google-cloud-bigquery google-cloud-firestore google-cloud-secret-manager pydantic fastapi uvicorn
```

**Local — gcloud CLI setup**
```bash
# Install gcloud CLI if not already installed (macOS example)
brew install --cask google-cloud-sdk

gcloud init
gcloud auth login
gcloud auth application-default login
gcloud config set project trippulse-prod
```

### 1.4 Define the Shared Data Contract

**Local**
```bash
mkdir -p app/models
touch app/models/trip_state.py
```
Write the `TripState` Pydantic model here (trip_id, user_prefs, flight_options, hotel_options, weather_forecast, activity_plan, budget_ledger) — this is the object every agent reads/writes.

---

## Phase 2 — Data Layer

### 2.1 Flight Data

**Console**
1. Go to **BigQuery → SQL Workspace**.
2. Create a new dataset: click your project → **Create Dataset** → name it `trippulse_flights`, choose a region close to your users.
3. Under **Add Data → BigQuery public datasets**, search for FAA/BTS on-time performance data and confirm the actual table path (public dataset naming changes over time — verify in the marketplace listing rather than assuming a fixed name).
4. Test a query in the SQL editor against the public table to confirm access before wiring it into code.

**Console — API key for live flight status**
5. Sign up with a flight-status provider (FlightAware AeroAPI, AviationStack, or Amadeus for Developers).
6. Get an API key from their developer portal (outside GCP).
7. Go to **Security → Secret Manager → Create Secret**. Name: `flight-api-key`. Paste the key value → **Create**.

**Local**
```bash
mkdir -p app/data
touch app/data/flights.py
# Implement: search_flights(), flight_risk_score(flight_no, date)
# flight_risk_score queries your BigQuery historical dataset by route/carrier/hour
```
```bash
pip install requests
# add a client wrapper that fetches the secret at runtime:
python3 -c "
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
name = 'projects/trippulse-prod/secrets/flight-api-key/versions/latest'
print(client.access_secret_version(name=name).payload.data.decode())
"
```

### 2.2 Weather Data

**Console**
1. In BigQuery, **Add Data → BigQuery public datasets** → search `ghcn_d` (Global Historical Climatology Network daily). Add it — this gives historical baselines only.
2. For live forecasts (needed since GHCN-D isn't predictive), sign up for Open-Meteo (no key needed) or NOAA's API, or enable the Google Weather API under **APIs & Services → Library**.

**Local**
```bash
touch app/data/weather.py
# Implement: rain_probability(lat, lon, date) using the forecast API
# Implement: historical_baseline(lat, lon, date) using ghcn_d via BigQuery
```

### 2.3 Hotel / Activity Data

**Console**
1. Sign up for Amadeus for Developers or Google Places API (**APIs & Services → Library → Places API → Enable**).
2. If using Places, generate an API key: **APIs & Services → Credentials → Create Credentials → API Key**. Restrict it to Places API only.
3. Store the key in Secret Manager the same way as the flight key (`hotel-api-key`).

**Console — Firestore for caching**
4. Go to **Firestore → Create Database** → choose **Native mode** → pick a region.
5. Create collections `hotel_cache` and `activity_cache` (can be done programmatically instead of manually).
5. Create collections `hotel-cache` and `activity-cache` (can be done programmatically instead of manually).

**Console — Google Weather API**
1. Enable the **Weather API** in Google Cloud APIs & Services.
2. Create a restricted Google Maps Platform API key with access to the Weather API.
3. Store it in Secret Manager as `WEATHER_API_KEY`.

**Local**
```bash
touch app/data/hotels.py app/data/activities.py
# Implement: search_hotels(), get_indoor_alternatives()
# Both should check Firestore cache before calling the external API
```

---

## Phase 3 — Build the Agents (ADK)

### 3.1 Vertex AI / Gemini Access

**Console**
1. Go to **Vertex AI → Dashboard** → confirm the API is enabled (done in 1.1).
2. Go to **Vertex AI → Model Garden**, search "Gemini 2.0 Flash", confirm availability in your region.
3. No manual key needed — ADK will use your service account credentials via `GOOGLE_APPLICATION_CREDENTIALS`.

**Local**
```bash
mkdir -p app/agents
touch app/agents/flight_hotel_agent.py app/agents/weather_agent.py app/agents/budget_agent.py app/agents/concierge.py
```
Write each `Agent(...)` definition (as in the architecture doc) in its respective file, wiring in the `FunctionTool`s built in Phase 2.

### 3.2 Orchestrator

**Local**
```bash
touch app/orchestrator.py
```
Compose `ParallelAgent` (flight/hotel + weather) → `SequentialAgent` (into budget agent) → root `concierge` agent with `sub_agents=[trip_pipeline]`.

**Local — smoke test**
```bash
adk run app/orchestrator.py
# or, if using the Python API directly:
python3 -m app.orchestrator
```

---

## Phase 4 — Event-Driven Re-Planning

### 4.1 Pub/Sub Topic

**Console**
1. Go to **Pub/Sub → Topics → Create Topic**. Name: `trip-disruption-events`.
2. Create a **Subscription** on that topic (push or pull) pointing at your Cloud Run/Cloud Function handler (set up in 4.3).

### 4.2 Cloud Scheduler Polling Job

**Console**
1. Go to **Cloud Scheduler → Create Job**.
2. Name: `poll-flight-weather`.
3. Frequency: `*/30 * * * *` (every 30 min) using cron syntax.
4. Target type: HTTP. URL: the endpoint of your polling Cloud Function (set up next).
5. **Create**.

### 4.3 Cloud Function / Cloud Run handler

**Local**
```bash
mkdir -p functions/poll_disruptions
touch functions/poll_disruptions/main.py functions/poll_disruptions/requirements.txt
# main.py: checks flight status + weather forecast for active trips,
# publishes to trip-disruption-events topic if a change is detected
```

**Local — deploy**
```bash
gcloud functions deploy poll_disruptions \
  --runtime python311 \
  --trigger-http \
  --entry-point poll_disruptions \
  --region us-central1 \
  --service-account trippulse-agent-sa@trippulse-prod.iam.gserviceaccount.com \
  --allow-unauthenticated
```

**Console — verify**
6. Go to **Cloud Functions**, confirm `poll_disruptions` shows status "Active".
7. Go to **Cloud Scheduler**, click **Run Now** on `poll-flight-weather` to test end-to-end, then check **Logs Explorer** for output.

### 4.4 Budget Reconciliation Hook

**Local**
```bash
touch app/data/ledger.py
# Implement: update_ledger(), reallocate_funds(), validate(ledger)
# Every agent write must call validate() before committing
```

---

## Phase 5 — Interface

### 5.1 Backend API

**Local**
```bash
mkdir -p app/api
touch app/api/main.py
# FastAPI app exposing POST /chat, wired to the ADK Runner + concierge agent
```
```bash
uvicorn app.api.main:app --reload --port 8080
# test locally: curl -X POST localhost:8080/chat -d '{"message":"plan my trip to Lisbon"}'
```

### 5.2 Frontend

**Local**
```bash
npx create-react-app trippulse-ui
cd trippulse-ui
npm install axios
# Build a day-by-day itinerary card view + chat panel calling POST /chat
npm start   # runs on localhost:3000
```
*(Alternative for a fast prototype: `pip install streamlit` and build a single-file Streamlit app instead of React.)*

### 5.3 Session Persistence

**Console**
1. Confirm Firestore database from step 2.3 is active.
2. Go to **Firestore → Data**, create a `sessions` collection (or let ADK's session service create it automatically on first write).

**Local**
```python
# In orchestrator.py, configure ADK's FirestoreSessionService
# pointing at project=trippulse-prod, collection=sessions
```

---

## Phase 6 — Testing & Hardening

### 6.1 Automated Agent Tests

**Local**
```bash
mkdir -p tests
touch tests/test_flight_delay.py tests/test_weather_swap.py tests/test_budget_cap.py
adk eval app/orchestrator.py tests/
```

### 6.2 Guardrails

**Local**
```bash
touch app/utils/rate_limiter.py
# Simple token-bucket or sliding-window limiter around external API calls
```

**Console**
1. Go to **APIs & Services → Quotas** for BigQuery, Vertex AI, and any third-party API dashboards — set alert thresholds so you're notified before hitting spend caps.
2. Go to **Billing → Budgets & Alerts → Create Budget** — set a monthly cap (e.g., $50) with email alerts at 50/90/100%.

### 6.3 Deploy to Production

**Local**
```bash
# containerize
touch Dockerfile
docker build -t gcr.io/trippulse-prod/trippulse .
docker push gcr.io/trippulse-prod/trippulse
```

**Console**
1. Go to **Cloud Run → Create Service**.
2. Select the container image just pushed.
3. Set **Minimum instances = 0** (cost efficiency), **Maximum instances** per expected load.
4. Under **Variables & Secrets**, mount `flight-api-key` and `hotel-api-key` from Secret Manager as environment variables.
5. Attach the `trippulse-agent-sa` service account under **Security**.
6. **Deploy** → note the generated URL.
7. Point your frontend's API base URL at this Cloud Run URL, redeploy the frontend.

---

## Quick Reference: Console vs. Local Split

| Task | Where |
|---|---|
| Create project, enable APIs, billing | Console |
| Service account + keys | Console (create) → Local (use) |
| BigQuery datasets/tables | Console (create/browse) → Local (query via code) |
| Secret Manager | Console (store) → Local (read at runtime) |
| Writing agent code, orchestrator, API, frontend | Local |
| Pub/Sub topic, Cloud Scheduler job | Console (create) |
| Cloud Function/Run deploy | Local (build/push) → Console (verify/monitor) |
| Firestore database | Console (create) → Local (read/write via SDK) |
| Billing alerts, quotas | Console |

---

### Notes on the Original Spec
- `bigquery-public-data.bts_realtime` is not a standard public dataset name — verify the actual BTS/FAA table in the BigQuery public dataset marketplace before coding against it; you'll likely need a live status API alongside it since BTS data is historical, not real-time.
- `ghcn_d` (GHCN-Daily) is real and useful for historical weather baselines, but it is **not** a forecast — pair it with a forecast API (Open-Meteo, NOAA, Google Weather API) for future trip dates.