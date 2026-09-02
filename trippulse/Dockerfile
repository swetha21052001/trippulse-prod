# Use a slim version for better compatibility with GCP libraries (grpcio, secret-manager, etc.)
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Environment variables for application configuration
ENV PORT=8080
ENV GCP_PROJECT=trippulse-prod
ENV GCP_LOCATION=us-central1
ENV ENABLE_FIRESTORE=true
ENV ENABLE_BIGQUERY=true

# Secret placeholders (values should be injected by Cloud Run from Secret Manager at runtime)
ENV HOTEL_API_KEY=""
ENV FLIGHT_API_KEY=""

EXPOSE 8080

CMD ["uvicorn", "run_server:app", "--host", "0.0.0.0", "--port", "8080"]
