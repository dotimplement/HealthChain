# Diabetes Risk Assessment Application
# Build from parent directory: docker build -f diabetes_risk_app/Dockerfile -t diabetes-risk-app .

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

# Install additional dependencies for the diabetes app
RUN pip install --no-cache-dir \
    "scikit-learn>=1.3.0" \
    "pytest>=8.0.0"

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy application files
COPY diabetes_risk_app/app.py .
COPY diabetes_risk_app/models/ ./models/
COPY diabetes_risk_app/config/ ./config/
COPY diabetes_risk_app/tests/ ./tests/

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/cds-services')" || exit 1

# Run the application
CMD ["python", "app.py"]
