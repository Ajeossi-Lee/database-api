from fastapi import APIRouter
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from app.core.config import settings
import time

router = APIRouter()

# Metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Latency',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'http_active_requests',
    'Active HTTP Requests'
)

# Database connection pool metrics
DATABASE_CONNECTIONS = Gauge(
    'database_connections',
    'Database connections in use',
    ['pool_type']
)

@router.get("/metrics")
async def get_metrics():
    """Expose Prometheus metrics."""
    # In a real implementation, you would collect actual metrics from the application
    # For now, we'll return the basic metrics that are collected

    # Collect metrics
    metrics = generate_latest()

    return {
        "metrics": metrics.decode('utf-8'),
        "status": "success"
    }

# Helper function to record metrics
def record_metrics(method: str, endpoint: str, status_code: int, duration: float):
    """Record request metrics."""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)