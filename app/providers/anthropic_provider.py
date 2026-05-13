import logging

import anthropic
from fastapi import HTTPException

from app.core.retry import retry_llm
from app.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def chat(self, messages: list[dict]) -> tuple[str, int]:
        """Standard chat for ChatService compatibility — no cache_control."""
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                messages=[m for m in messages if m["role"] != "system"],
                system=next((m["content"] for m in messages if m["role"] == "system"), ""),
            )
        except anthropic.APIError as e:
            raise HTTPException(status_code=502, detail=f"Anthropic error: {e}")

        reply = response.content[0].text if response.content else ""
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        return reply, tokens_used

    @retry_llm
    def generate(self, system_prompt: str, user_message: str) -> tuple[str, int, int, int]:
        """
        Single-turn call with cache_control + retry logic on RateLimitError / APIError.
        Returns (reply, cache_creation_tokens, cache_read_tokens, total_tokens).

        Exceptions are NOT caught here — they bubble up to tenacity so it can retry.
        After 3 failed attempts the original exception is re-raised to the caller.
        """
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": user_message},
            ],
        }]

        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=messages,
        )

        usage = response.usage
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        total = usage.input_tokens + usage.output_tokens

        logger.info("cache_metrics", extra={
            "cache_creation_input_tokens": cache_creation,
            "cache_read_input_tokens": cache_read,
            "total_input_tokens": total,
        })

        reply = response.content[0].text if response.content else ""
        return reply, cache_creation, cache_read, total
