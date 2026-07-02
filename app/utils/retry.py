from collections.abc import Callable
from typing import TypeVar

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

T = TypeVar("T")


def retry_transient_errors(
    *exception_types: type[Exception],
    attempts: int = 3,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry an async callable on transient errors (network/rate-limit) with exponential backoff.

    Not intended for validation failures -- those need a different, bounded, content-aware retry
    (see GroqClient's structured-completion validation loop).
    """
    return retry(
        retry=retry_if_exception_type(exception_types),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
