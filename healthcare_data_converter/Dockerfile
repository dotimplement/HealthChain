# Healthcare Data Converter Application
# Build from parent directory: docker build -f healthcare_data_converter/Dockerfile -t healthcare-data-converter .

FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
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

# Install additional dependencies for XML processing and testing
RUN pip install --no-cache-dir \
    "pytest>=8.0.0" \
    "pytest-asyncio>=0.24.0"

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime XML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy application files
COPY healthcare_data_converter/__init__.py ./__init__.py
COPY healthcare_data_converter/converter.py ./converter.py
COPY healthcare_data_converter/service.py ./service.py
COPY healthcare_data_converter/cli.py ./cli.py
COPY healthcare_data_converter/models.py ./models.py
COPY healthcare_data_converter/configs/ ./configs/
COPY healthcare_data_converter/examples/ ./examples/

# Create package structure for imports
RUN mkdir -p /app/healthcare_data_converter && \
    cp *.py /app/healthcare_data_converter/ && \
    cp -r configs /app/healthcare_data_converter/

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command - run the API server
CMD ["python", "-m", "uvicorn", "healthcare_data_converter.service:app", "--host", "0.0.0.0", "--port", "8000"]
