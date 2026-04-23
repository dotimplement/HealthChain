import asyncio
import logging
import random
import time

from healthchain.gateway.fhir.errors import FHIRConnectionError, RateLimitError, RetryableError

logger = logging.getLogger(__name__)

RETRYABLE = (RateLimitError, RetryableError)


def get_delay(attempt, retry_after=None):
    if retry_after:
        return float(retry_after)
    return min(1.0 * (2 ** attempt), 60.0) * (0.5 + random.random() * 0.5)


def with_retry(func, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            return func()
        except RETRYABLE as e:
            if attempt >= max_retries:
                raise
            delay = get_delay(attempt, getattr(e, "retry_after", None))
            logger.warning(f"Attempt {attempt + 1} failed. Retrying in {delay:.1f}s")
            time.sleep(delay)
        except FHIRConnectionError:
            raise


async def with_retry_async(func, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except RETRYABLE as e:
            if attempt >= max_retries:
                raise
            delay = get_delay(attempt, getattr(e, "retry_after", None))
            logger.warning(f"Attempt {attempt + 1} failed. Retrying in {delay:.1f}s")
            await asyncio.sleep(delay)
        except FHIRConnectionError:
            raise