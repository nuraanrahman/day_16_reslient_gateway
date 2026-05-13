import logging
import time

logger = logging.getLogger(__name__)

CLOSED    = "closed"
OPEN      = "open"
HALF_OPEN = "half_open"


class CircuitBreakerOpen(Exception):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CLOSED
        self.failure_count = 0
        self.opened_at = None

    def call(self, func):
        if self.state == OPEN:
            seconds_waiting = time.time() - self.opened_at
            if seconds_waiting < self.recovery_timeout:
                raise CircuitBreakerOpen("Service is down. Try again in 60 seconds.")
            self.state = HALF_OPEN
            logger.info("circuit_half_open", extra={"event": "circuit_half_open"})

        try:
            result = func()
        except Exception:
            self.failure_count += 1
            logger.warning("circuit_failure", extra={
                "event": "circuit_failure",
                "failure_count": self.failure_count,
                "threshold": self.failure_threshold,
            })
            if self.failure_count >= self.failure_threshold:
                self.state = OPEN
                self.opened_at = time.time()
                logger.error("circuit_opened", extra={
                    "event": "circuit_opened",
                    "failure_count": self.failure_count,
                })
            raise

        if self.state != CLOSED:
            logger.info("circuit_closed", extra={"event": "circuit_closed"})
        self.state = CLOSED
        self.failure_count = 0
        return result
