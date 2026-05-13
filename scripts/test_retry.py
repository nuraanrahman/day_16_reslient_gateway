"""
Retry logic demo — no server needed, runs directly.

What this tests
---------------
1. AuthenticationError  → should FAIL IMMEDIATELY (no retries, 401 is not in the retry list)
2. RateLimitError x3    → should RETRY 3 times then raise
3. RateLimitError x1    → should RETRY once, succeed on attempt 2  (2-attempt recovery)

Run with:
  cd C:\\ai_engineering\\day_16_retry_logic
  python scripts/test_retry.py
"""

import logging
import sys
import unittest.mock as mock

# ── set up logging so tenacity WARNING messages are visible ─────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("test_retry")

# ── import AFTER logging is configured so tenacity picks up the root logger ──
import openai
from app.core.retry import retry_llm


# ── helper: a fake generate() function we can decorate and test ──────────────

@retry_llm
def fake_generate(call_fn):
    """
    Stands in for a real provider's generate().
    call_fn() either raises an exception or returns a result.
    """
    return call_fn()


# ════════════════════════════════════════════════════════════════════════════
# TEST 1 — AuthenticationError must NOT be retried
# ════════════════════════════════════════════════════════════════════════════
def test_auth_error_no_retry():
    logger.info("=" * 60)
    logger.info("TEST 1: AuthenticationError — expect IMMEDIATE failure, no retries")
    logger.info("=" * 60)

    call_count = 0

    def raise_auth_error():
        nonlocal call_count
        call_count += 1
        logger.info(f"  -> call_count={call_count}")
        raise openai.AuthenticationError(
            message="401 Incorrect API key",
            response=mock.Mock(status_code=401),
            body={"error": {"message": "Incorrect API key"}},
        )

    try:
        fake_generate(raise_auth_error)
    except openai.AuthenticationError:
        logger.info(f"PASS: AuthenticationError raised after {call_count} call(s) — no retry")
    except Exception as e:
        logger.error(f"FAIL: Unexpected exception {type(e).__name__}: {e}")

    assert call_count == 1, f"Expected 1 call, got {call_count}"
    print()


# ════════════════════════════════════════════════════════════════════════════
# TEST 2 — RateLimitError retries all 3 attempts then gives up
# ════════════════════════════════════════════════════════════════════════════
def test_rate_limit_all_retries_fail():
    logger.info("=" * 60)
    logger.info("TEST 2: RateLimitError x3 — expect 3 attempts, then raise")
    logger.info("  (tenacity will log a WARNING before each sleep — watch for them)")
    logger.info("=" * 60)

    call_count = 0

    def always_rate_limit():
        nonlocal call_count
        call_count += 1
        logger.info(f"  -> call_count={call_count}")
        raise openai.RateLimitError(
            message="429 Rate limit exceeded",
            response=mock.Mock(status_code=429),
            body={"error": {"message": "Rate limit exceeded"}},
        )

    # Patch wait to zero so the test runs instantly
    with mock.patch("app.core.retry.wait_random_exponential", return_value=lambda retry_state: 0):
        # Re-import retry_llm with patched wait — easier to just patch tenacity's sleep
        pass

    # Simpler: patch time.sleep inside tenacity so we don't actually wait
    with mock.patch("tenacity.nap.time.sleep"):
        try:
            fake_generate(always_rate_limit)
        except openai.RateLimitError:
            logger.info(f"PASS: RateLimitError raised after {call_count} attempt(s)")
        except Exception as e:
            logger.error(f"FAIL: Unexpected exception {type(e).__name__}: {e}")

    assert call_count == 3, f"Expected 3 calls, got {call_count}"
    print()


# ════════════════════════════════════════════════════════════════════════════
# TEST 3 — 2-attempt recovery (fails once, succeeds on attempt 2)
# This is the scenario the user asked to see in the logs.
# ════════════════════════════════════════════════════════════════════════════
def test_two_attempt_recovery():
    logger.info("=" * 60)
    logger.info("TEST 3: 2-attempt recovery — fail on attempt 1, succeed on attempt 2")
    logger.info("  Watch for tenacity WARNING log after attempt 1, then success.")
    logger.info("=" * 60)

    call_count = 0

    def fail_once_then_succeed():
        nonlocal call_count
        call_count += 1
        logger.info(f"  -> call_count={call_count}")
        if call_count == 1:
            raise openai.RateLimitError(
                message="429 Rate limit exceeded",
                response=mock.Mock(status_code=429),
                body={"error": {"message": "Rate limit exceeded"}},
            )
        return "Hello from the LLM (attempt 2)"

    with mock.patch("tenacity.nap.time.sleep"):
        result = fake_generate(fail_once_then_succeed)

    logger.info(f"PASS: Got result on attempt {call_count}: '{result}'")
    assert call_count == 2, f"Expected 2 calls, got {call_count}"
    assert result == "Hello from the LLM (attempt 2)"
    print()


# ════════════════════════════════════════════════════════════════════════════
# Run all tests
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" Tenacity Retry Logic — Day 16 Demo")
    print("=" * 60 + "\n")

    test_auth_error_no_retry()
    test_rate_limit_all_retries_fail()
    test_two_attempt_recovery()

    print("=" * 60)
    print(" All 3 tests passed.")
    print("=" * 60)
