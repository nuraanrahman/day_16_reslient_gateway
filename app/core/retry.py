import logging

import anthropic
import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

# Retry up to 3 times on TRANSIENT errors only (rate limits, timeouts, network, server errors).
# Waits 1-30 seconds between attempts with random exponential back-off.
#
# Why NOT openai.APIError / anthropic.APIError (the broad base class)?
#   AuthenticationError (401), BadRequestError (400), etc. are subclasses of APIError.
#   Those are permanent errors — retrying them is pointless and wastes quota.
#   So we name only the transient subclasses we actually want to retry.
retry_llm = retry(
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type((
        openai.RateLimitError,        # 429 - too many requests
        openai.APITimeoutError,       # request timed out
        openai.APIConnectionError,    # network issue
        openai.InternalServerError,   # 500 - OpenAI server error
        anthropic.RateLimitError,     # 429 - too many requests
        anthropic.InternalServerError,  # 500 - Anthropic server error
        anthropic.APIConnectionError,   # network issue
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,  # after 3 failures, re-raise the original exception (not RetryError)
)
