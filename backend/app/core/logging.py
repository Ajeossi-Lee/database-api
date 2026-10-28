import logging
import sys
from datetime import datetime
from pathlib import Path

import structlog

from app.settings.config import settings

# backend/app/core/logging.py -> backend/logs
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"

_LEVEL_FILES = (
    # appender 名、文件名中的级别、只接收的级别、是否包含更高级别
    ("FILEERROR", "error", logging.ERROR, True),
    ("FILEWARN", "warn", logging.WARNING, False),
    ("FILEINFO", "info", logging.INFO, False),
    ("FILEDEBUG", "debug", logging.DEBUG, False),
)


class _ExactLevelFilter(logging.Filter):
    """每个文件只收自己的级别。error 文件同时收下 critical。"""

    def __init__(self, level: int, include_higher: bool = False):
        super().__init__()
        self.level = level
        self.include_higher = include_higher

    def filter(self, record: logging.LogRecord) -> bool:
        if self.include_higher:
            return record.levelno >= self.level
        return record.levelno == self.level


class _DailyLevelFileHandler(logging.Handler):
    """按日期写入 log-{级别}-{YYYY-MM-DD}.log，跨天时换新文件，旧文件留作归档。"""

    def __init__(self, log_dir: Path, level_name: str):
        super().__init__()
        self.log_dir = log_dir
        self.level_name = level_name
        self._current_day = ""
        self._stream = None
        self._app_log_handler = True

    def _path_for(self, day: str) -> Path:
        return self.log_dir / f"log-{self.level_name}-{day}.log"

    def _ensure_stream(self) -> None:
        day = datetime.now().strftime("%Y-%m-%d")
        if self._stream is not None and day == self._current_day:
            return
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        self._current_day = day
        path = self._path_for(day)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = path.open("a", encoding="utf-8")

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._ensure_stream()
            self._stream.write(self.format(record) + "\n")
            self.flush()
        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        if self._stream is not None:
            self._stream.flush()

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        super().close()


def _console_level() -> int:
    """控制台级别跟随 LOG_LEVEL，方便开发测试。"""
    name = settings.LOG_LEVEL.upper()
    if name == "WARN":
        name = "WARNING"
    return getattr(logging, name, logging.INFO)


def configure_structlog():
    """把 structlog 交到标准库，级别文件和控制台才能收到这些日志。"""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )


logger = structlog.get_logger()


def setup_logging():
    """按级别把日志写入 backend/logs，并在控制台输出。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in list(root.handlers):
        if getattr(handler, "_app_log_handler", False):
            root.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for _appender, level_name, level, include_higher in _LEVEL_FILES:
        handler = _DailyLevelFileHandler(LOG_DIR, level_name)
        handler.addFilter(_ExactLevelFilter(level, include_higher))
        handler.setFormatter(formatter)
        root.addHandler(handler)

    # stdout：开发测试时在控制台查看，级别由 LOG_LEVEL 决定
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(_console_level())
    console.setFormatter(formatter)
    console._app_log_handler = True
    root.addHandler(console)

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
