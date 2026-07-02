import pytest

from app.utils.retry import retry_transient_errors


async def test_retry_transient_errors_retries_matching_exception_then_succeeds():
    attempts = {"count": 0}

    @retry_transient_errors(ValueError, attempts=3)
    async def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise ValueError("transient")
        return "ok"

    result = await flaky()

    assert result == "ok"
    assert attempts["count"] == 2


async def test_retry_transient_errors_gives_up_after_max_attempts():
    attempts = {"count": 0}

    @retry_transient_errors(ValueError, attempts=2)
    async def always_fails():
        attempts["count"] += 1
        raise ValueError("still failing")

    with pytest.raises(ValueError):
        await always_fails()

    assert attempts["count"] == 2


async def test_retry_transient_errors_does_not_retry_unmatched_exceptions():
    attempts = {"count": 0}

    @retry_transient_errors(ValueError, attempts=3)
    async def raises_type_error():
        attempts["count"] += 1
        raise TypeError("not retried")

    with pytest.raises(TypeError):
        await raises_type_error()

    assert attempts["count"] == 1
