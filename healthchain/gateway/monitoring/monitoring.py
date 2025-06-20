import time
import structlog

from fastapi import FastAPI
from prometheus_client import Counter, Histogram
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "gateway_requests_total",
    "Total count of requests by endpoint and status",
    ["endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "gateway_request_latency_seconds", "Request latency in seconds", ["endpoint"]
)


def setup_monitoring(app: FastAPI):
    """Set up monitoring for FastAPI app"""
    # OpenTelemetry instrumentation
    FastAPIInstrumentor.instrument_app(app)

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request, call_next):
        start_time = time.time()
        path = request.url.path

        try:
            response = await call_next(request)
            status_code = response.status_code
            duration = time.time() - start_time

            # Update metrics
            REQUEST_COUNT.labels(endpoint=path, status=status_code).inc()
            REQUEST_LATENCY.labels(endpoint=path).observe(duration)

            # Structured logging
            logger.info(
                "request_processed",
                path=path,
                method=request.method,
                status_code=status_code,
                duration=duration,
            )

            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "request_failed",
                path=path,
                method=request.method,
                error=str(e),
                duration=duration,
            )
            raise
