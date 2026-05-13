import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_EXTRA_FIELDS = (
    "event",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "session_id",
    "model",
    "latency_ms",
    "tokens_used",
    "environment",
    "error",
    "user_id",
    "email",
    # cache metrics
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "total_input_tokens",
    "cached_tokens",
    "total",
)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_line = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for field in _EXTRA_FIELDS:
            if hasattr(record, field):
                log_line[field] = getattr(record, field)
        return json.dumps(log_line)


def setup_logging(log_level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root.handlers = [handler]

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
