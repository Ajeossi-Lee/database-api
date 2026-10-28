import logging
import structlog
from app.settings.config import settings
import json
from datetime import datetime

# Configure structlog with security-aware processors
def configure_structlog():
    """Configure structlog with security-aware processors."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# Get logger
logger = structlog.get_logger()

def setup_logging():
    """Setup logging configuration."""
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configure structlog for the application
    configure_structlog()

def log_security_event(event_type: str, user_id: str = None, request_id: str = None,
                      ip_address: str = None, details: dict = None):
    """Log security-related events with structured logging."""
    extra_info = {
        "event_type": event_type,
        "user_id": user_id,
        "request_id": request_id,
        "ip_address": ip_address,
        "timestamp": datetime.utcnow().isoformat()
    }

    if details:
        extra_info.update(details)

    # Log as JSON for easy parsing by observability systems
    logger.info("Security event", **extra_info)

def log_authentication_event(event_type: str, user_id: str = None,
                           request_id: str = None, ip_address: str = None,
                           success: bool = True, details: dict = None):
    """Log authentication events."""
    extra_info = {
        "event_type": f"auth_{event_type}",
        "user_id": user_id,
        "request_id": request_id,
        "ip_address": ip_address,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }

    if details:
        extra_info.update(details)

    logger.info("Authentication event", **extra_info)

def log_authorization_event(event_type: str, user_id: str = None,
                          request_id: str = None, ip_address: str = None,
                          resource: str = None, action: str = None,
                          granted: bool = True, details: dict = None):
    """Log authorization events."""
    extra_info = {
        "event_type": f"authz_{event_type}",
        "user_id": user_id,
        "request_id": request_id,
        "ip_address": ip_address,
        "resource": resource,
        "action": action,
        "granted": granted,
        "timestamp": datetime.utcnow().isoformat()
    }

    if details:
        extra_info.update(details)

    logger.info("Authorization event", **extra_info)