# Multi-EHR Data Aggregation Application
# Build from parent directory: docker build -f multi_ehr_aggregation/Dockerfile -t multi-ehr-aggregation .

FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy healthchain package source
COPY healthchain/ /build/healthchain/
COPY pyproject.toml /build/

# Install healthchain from source
RUN pip install --no-cache-dir /build

# Install additional dependencies for async operations
RUN pip install --no-cache-dir \
    "pytest>=8.0.0" \
    "pytest-asyncio>=0.24.0"

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Create data directory
RUN mkdir -p /app/data && chown appuser:appuser /app/data

# Copy application files
COPY multi_ehr_aggregation/app.py .
COPY multi_ehr_aggregation/models/ ./models/
COPY multi_ehr_aggregation/config/ ./config/
COPY multi_ehr_aggregation/examples/ ./examples/

# Copy tests if they exist
COPY multi_ehr_aggregation/tests/ ./tests/

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command - run the aggregation demo
CMD ["python", "app.py"]
