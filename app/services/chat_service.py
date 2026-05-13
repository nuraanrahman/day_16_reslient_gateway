import logging
import time

from app.providers.base import LLMProvider
from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a direct, no-fluff coding tutor. "
    "Keep replies under 120 words. Use examples."
)


class ChatService:
    def __init__(self):
        self.sessions = {}

    def reply(self, session_id, user_message, provider, circuit_breaker):
        if session_id not in self.sessions:
            self.sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

        history = self.sessions[session_id]
        history.append({"role": "user", "content": user_message})

        model = getattr(provider, "_model", "unknown")
        logger.info("llm_call_start", extra={
            "event": "llm_call_start",
            "model": model,
            "session_id": session_id,
        })

        start = time.perf_counter()

        try:
            reply_text, tokens_used = circuit_breaker.call(
                lambda: provider.chat(history)
            )
        except CircuitBreakerOpen:
            logger.warning("circuit_blocked", extra={
                "event": "circuit_blocked",
                "session_id": session_id,
            })
            raise
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error("llm_call_failed", extra={
                "event": "llm_call_failed",
                "model": model,
                "error_type": type(exc).__name__,
                "latency_ms": latency_ms,
            })
            raise

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info("llm_call_complete", extra={
            "event": "llm_call_complete",
            "model": model,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
        })

        history.append({"role": "assistant", "content": reply_text})
        return reply_text, len(history), tokens_used

    def get_history(self, session_id):
        return self.sessions.get(session_id)

    def delete_session(self, session_id):
        if session_id not in self.sessions:
            return False
        del self.sessions[session_id]
        return True
