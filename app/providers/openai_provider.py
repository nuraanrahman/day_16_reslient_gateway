import logging

from openai import OpenAI

from app.core.retry import retry_llm
from app.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

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
