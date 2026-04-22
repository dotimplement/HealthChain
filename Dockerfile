# HealthChain application Dockerfile
#
# Usage:
#   Build:  docker build -t my-healthcare-app .
#   Run:    docker run -p 8000:8000 --env-file .env my-healthcare-app
#
# Required environment variables (set in .env or pass via -e):
#   APP_MODULE   Python module path to your app, e.g. "myapp:app" (default: "app:app")
#
# FHIR source credentials (if connecting to Epic/Cerner):
#   FHIR_BASE_URL, CLIENT_ID, CLIENT_SECRET or CLIENT_SECRET_PATH
#
# See docs: https://healthchainai.github.io/HealthChain/reference/gateway/gateway/

FROM python:3.11-slim

# Keeps Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_MODULE=app:app \
    PORT=8000

WORKDIR /app

# Install system dependencies needed by lxml and spaCy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install healthchain from PyPI
RUN pip install --no-cache-dir healthchain

# Install any additional dependencies your application needs
# (copy requirements first to leverage Docker layer caching)
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY . .

# Run as non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE $PORT

CMD uvicorn $APP_MODULE --host 0.0.0.0 --port $PORT
