import logging

from fastapi import HTTPException
from openai import OpenAI, OpenAIError

from app.core.retry import retry_llm
from app.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def chat(self, messages: list[dict]) -> tuple[str, int]:
        """Standard chat for ChatService compatibility."""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
            )
        except OpenAIError as e:
            raise HTTPException(status_code=502, detail=f"OpenAI error: {e}")

        reply = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else len(reply.split())
        return reply, tokens_used

    @retry_llm
    def generate(self, system_prompt: str, user_message: str) -> tuple[str, int, int, int]:
        """
        Single-turn call with retry logic on RateLimitError / APIError / APITimeoutError.
        Returns (reply, cache_creation_tokens, cache_read_tokens, total_tokens).

        Exceptions are NOT caught here — they bubble up to tenacity so it can retry.
        After 3 failed attempts the original exception is re-raised to the caller.
        """
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        cached = 0
        if response.usage and hasattr(response.usage, "prompt_tokens_details"):
            cached = response.usage.prompt_tokens_details.cached_tokens if response.usage.prompt_tokens_details else 0

        total = response.usage.total_tokens if response.usage else 0

        logger.info("cache_metrics", extra={
            "cached_tokens": cached,
            "total": total,
        })

        reply = response.choices[0].message.content or ""
        return reply, 0, cached, total
